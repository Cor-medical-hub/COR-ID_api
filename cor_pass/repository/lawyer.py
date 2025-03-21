
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
    The get_users function returns a list of all users from the database.

    :param skip: int: Skip the first n records in the database
    :param limit: int: Limit the number of results returned
    :param db: Session: Pass the database session to the function
    :return: A list of all users
    """
    query = db.query(Doctor).offset(skip).limit(limit).all()
    return query


async def approve_doctor(doctor_id: str, db: Session):
    # Находим врача по ID
    doctor = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
    if not doctor:
        raise ValueError("Врач не найден")

    # Меняем статус на "подтвержден"
    doctor.status = DoctorStatus.APPROVED
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise e


