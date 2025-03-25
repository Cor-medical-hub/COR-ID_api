
from sqlalchemy.orm import Session


from cor_pass.database.models import (

    Doctor,
    DoctorStatus,
    Diploma,
    Certificate,
    ClinicAffiliation

)
from cor_pass.schemas import (
    UserModel,
    PasswordStorageSettings,
    MedicalStorageSettings,
    UserSessionDBModel,
    UserSessionModel,
)



async def get_doctors(skip: int, limit: int, db: Session) -> list[Doctor]:
    """
    The get_doctors function returns a list of all doctors from the database.

    :param skip: int: Skip the first n records in the database
    :param limit: int: Limit the number of results returned
    :param db: Session: Pass the database session to the function
    :return: A list of all doctors
    """
    query = db.query(Doctor).offset(skip).limit(limit).all()
    return query


async def get_doctor(doctor_id: str, db: Session) -> Doctor | None:

    query = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
    return query



async def get_all_doctor_info(doctor_id: str, db: Session) -> Doctor | None:

    query = (
        db.query(Doctor)
        .filter(Doctor.doctor_id == doctor_id)
        .outerjoin(Diploma)  
        .outerjoin(Certificate)  
        .outerjoin(ClinicAffiliation)  
        .first()  
    )
    return query


async def approve_doctor(doctor: Doctor, db: Session, status: DoctorStatus):

    doctor.status = status
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise e


