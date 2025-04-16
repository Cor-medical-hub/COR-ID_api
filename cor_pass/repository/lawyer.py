from typing import List
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload


from cor_pass.database.models import (
    Doctor,
    DoctorStatus,
    Diploma,
    Certificate,
    ClinicAffiliation,
)
from cor_pass.schemas import (
    UserModel,
    PasswordStorageSettings,
    MedicalStorageSettings,
    UserSessionDBModel,
    UserSessionModel,
)
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession


async def get_doctors(skip: int, limit: int, db: AsyncSession) -> List[Doctor]:
    """
    Асинхронно повертає список всіх лікарів з бази даних.

    :param skip: int: Пропустити перші n записів у базі даних
    :param limit: int: Обмежити кількість повернутих результатів
    :param db: AsyncSession: Асинхронна сесія бази даних
    :return: Список всіх лікарів
    """
    stmt = select(Doctor).offset(skip).limit(limit)
    result = await db.execute(stmt)
    doctors = result.scalars().all()
    return list(doctors)


async def get_doctor(doctor_id: str, db: AsyncSession) -> Doctor | None:
    """
    Асинхронно отримує лікаря за його ID.
    """
    stmt = select(Doctor).where(Doctor.doctor_id == doctor_id)
    result = await db.execute(stmt)
    doctor = result.scalar_one_or_none()
    return doctor


async def get_all_doctor_info(doctor_id: str, db: AsyncSession) -> Doctor | None:
    """
    Асинхронно отримує всю інформацію про лікаря, включаючи дипломи, сертифікати та прив'язки до клінік.
    """
    stmt = (
        select(Doctor)
        .where(Doctor.doctor_id == doctor_id)
        .outerjoin(Diploma)
        .outerjoin(Certificate)
        .outerjoin(ClinicAffiliation)
        # Для завантаження пов'язаних об'єктів (замість lazy loading)
        .options(selectinload(Doctor.diplomas))
        .options(selectinload(Doctor.certificates))
        .options(selectinload(Doctor.clinic_affiliations))
    )
    result = await db.execute(stmt)
    doctor = result.scalar_one_or_none()
    return doctor


async def approve_doctor(doctor: Doctor, db: AsyncSession, status: DoctorStatus):
    """
    Асинхронно оновлює статус лікаря.
    """
    doctor.status = status
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise e


async def delete_doctor_by_doctor_id(db: AsyncSession, doctor_id: str):
    """
    Асинхронно видаляє лікаря за його doctor_id.
    """
    try:
        stmt = select(Doctor).where(Doctor.doctor_id == doctor_id)
        result = await db.execute(stmt)
        doctor = result.scalar_one()

        await db.delete(doctor)
        await db.commit()
    except NoResultFound:
        print("Доктор не знайдений.")
    except Exception as e:
        await db.rollback()
        print(f"Произошла ошибка при удалении врача: {e}")
