from typing import List
from fastapi import APIRouter, File, HTTPException, Depends, UploadFile, status
from sqlalchemy.orm import Session
from cor_pass.database.db import get_db
from cor_pass.services.auth import auth_service
from cor_pass.database.models import Certificate, ClinicAffiliation, Diploma, User, Status, Doctor
from cor_pass.services.access import admin_access, lawyer_access
from cor_pass.schemas import CertificateResponse, ClinicAffiliationResponse, DiplomaResponse, DoctorCreate, DoctorResponse, DoctorWithRelationsResponse, UserDb
from cor_pass.repository import person
from cor_pass.repository import lawyer
from pydantic import EmailStr
from cor_pass.database.redis_db import redis_client


from cor_pass.services.logger import logger

router = APIRouter(prefix="/lawyer", tags=["Lawyer"])


@router.get(
    "/get_all",
    response_model=List[DoctorResponse],  
    dependencies=[Depends(lawyer_access)],
)
async def get_all_doctors(
    skip: int = 0,  
    limit: int = 10,  
    db: Session = Depends(get_db),  
):

    list_doctors = db.query(Doctor).offset(skip).limit(limit).all()

    if not list_doctors:
        return []

    doctors_response = [
        DoctorResponse(
            id=doctor.id,
            doctor_id=doctor.doctor_id,
            work_email=doctor.work_email,
            first_name=doctor.first_name,
            surname=doctor.surname,
            last_name=doctor.last_name,
            scientific_degree=doctor.scientific_degree,
            date_of_last_attestation=doctor.date_of_last_attestation,
            status=doctor.status,  
        )
        for doctor in list_doctors
    ]
    return doctors_response


@router.get(
    "/{doctor_id}",
    response_model=DoctorWithRelationsResponse,
    dependencies=[Depends(lawyer_access)],
)
async def get_doctor_with_relations(
    doctor_id: str,  
    db: Session = Depends(get_db),  
):
    doctor = (
        db.query(Doctor)
        .filter(Doctor.id == doctor_id)
        .outerjoin(Diploma)  
        .outerjoin(Certificate)  
        .outerjoin(ClinicAffiliation)  
        .first()  
    )

    if not doctor:
        raise HTTPException(status_code=404, detail="Лікаря не знайдено")

    # Серіалізуємо дані у відповідну схему
    doctor_response = DoctorWithRelationsResponse(
        id=doctor.id,
        doctor_id=doctor.doctor_id,
        work_email=doctor.work_email,
        first_name=doctor.first_name,
        surname=doctor.surname,
        last_name=doctor.last_name,
        scientific_degree=doctor.scientific_degree,
        date_of_last_attestation=doctor.date_of_last_attestation,
        status=doctor.status,
        diplomas=[
            DiplomaResponse(
                id=diploma.id,
                date=diploma.date,
                series=diploma.series,
                number=diploma.number,
                university=diploma.university,
            )
            for diploma in doctor.diplomas
        ],
        certificates=[
            CertificateResponse(
                id=certificate.id,
                date=certificate.date,
                series=certificate.series,
                number=certificate.number,
                university=certificate.university,
            )
            for certificate in doctor.certificates
        ],
        clinic_affiliations=[
            ClinicAffiliationResponse(
                id=affiliation.id,
                clinic_name=affiliation.clinic_name,
                department=affiliation.department,
                position=affiliation.position,
                specialty=affiliation.specialty,
            )
            for affiliation in doctor.clinic_affiliations
        ],
    )

    return doctor_response



@router.patch("/asign_status/{account_status}", dependencies=[Depends(admin_access)])
async def assign_status(
    email: EmailStr, account_status: Status, db: Session = Depends(get_db)
):
    """
    **Assign a account_status to a user by email. / Применение нового статуса аккаунта пользователя**\n

    This route allows to assign the selected account_status to a user by their email.

    :param email: EmailStr: Email of the user to whom you want to assign the status.

    :param account_status: Status: The selected account_status for the assignment (Premium, Basic).

    :param db: Session: Database Session.

    :return: Message about successful status change.

    :rtype: dict
    """
    user = await person.get_user_by_email(email, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if account_status == user.account_status:
        return {"message": "The acount status has already been assigned"}
    else:
        await person.make_user_status(email, account_status, db)
        return {"message": f"{email} - {account_status.value}"}



@router.patch("/activate/{email}", dependencies=[Depends(admin_access)])
async def activate_user(email: EmailStr, db: Session = Depends(get_db)):
    """
    **Activate user by email. / Активация аккаунта пользователя**\n

    This route allows to assign the selected account_status to a user by their email.

    :param email: EmailStr: Email of the user to whom you want to assign the status.

    :param account_status: Status: The selected account_status for the assignment (Premium, Basic).

    :param db: Session: Database Session.

    :return: Message about successful status change.

    :rtype: dict
    """
    user = await person.get_user_by_email(email, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if user.is_active:
        return {"message": f"The {user.email} account is already active"}
    else:
        await person.activate_user(email, db)
        return {"message": f"{user.email} - account is activated"}


