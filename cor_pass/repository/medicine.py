from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from cor_pass.database.models import Medicine, MedicineSchedule, User
from cor_pass.schemas import (
    MedicineCreate,
    MedicineUpdate,
    MedicineScheduleCreate,
    MedicineScheduleUpdate,
)


async def create_medicine(
    db: AsyncSession, body: MedicineCreate, user: User
) -> Medicine:
    """
    Создает новый медикамент для текущего пользователя.
    В зависимости от способа введения сохраняет соответствующие параметры.
    """
    method = body.method_data

    new_medicine = Medicine(
        name=body.name,
        active_substance=body.active_substance,
        intake_method=method.intake_method,
        dosage=getattr(method, "dosage", None),
        unit=getattr(method, "unit", None),
        concentration=getattr(method, "concentration", None),
        volume=getattr(method, "volume", None),
        created_by=user.cor_id,
    )

    db.add(new_medicine)
    await db.commit()
    await db.refresh(new_medicine)
    return new_medicine


async def get_user_medicines(db: AsyncSession, user: User) -> List[Medicine]:
    """
    Возвращает все медикаменты текущего пользователя.
    """
    result = await db.execute(
        select(Medicine).where(Medicine.created_by == user.cor_id)
    )
    return result.scalars().all()


async def get_medicine_by_id(db: AsyncSession, medicine_id: str) -> Optional[Medicine]:
    """
    Возвращает медикамент по его ID.
    """
    result = await db.execute(
        select(Medicine).where(Medicine.id == medicine_id)
    )
    return result.scalar_one_or_none()


async def update_medicine(
    db: AsyncSession, medicine: Medicine, body: MedicineUpdate
) -> Medicine:
    """
    Обновляет данные медикамента, включая параметры способа введения.
    """
    if body.name is not None:
        medicine.name = body.name
    if body.active_substance is not None:
        medicine.active_substance = body.active_substance

    if body.method_data:
        method = body.method_data
        medicine.intake_method = method.intake_method
        medicine.dosage = getattr(method, "dosage", None)
        medicine.unit = getattr(method, "unit", None)
        medicine.concentration = getattr(method, "concentration", None)
        medicine.volume = getattr(method, "volume", None)

    db.add(medicine)
    await db.commit()
    await db.refresh(medicine)
    return medicine


async def delete_medicine(db: AsyncSession, medicine: Medicine) -> None:
    """
    Удаляет медикамент.
    """
    await db.delete(medicine)
    await db.commit()




async def create_medicine_schedule(
    db: AsyncSession, body: MedicineScheduleCreate, user: User
) -> MedicineSchedule:
    """
    Создает новое расписание приёма для медикамента.
    """
    new_schedule = MedicineSchedule(
        medicine_id=body.medicine_id,
        user_cor_id=user.cor_id,
        start_date=body.start_date,
        duration_days=body.duration_days,
        times_per_day=body.times_per_day,
        intake_times=body.intake_times,
        interval_minutes=body.interval_minutes,
        notes=body.notes,
    )
    db.add(new_schedule)
    await db.commit()
    await db.refresh(new_schedule)
    return new_schedule


async def get_user_schedules(db: AsyncSession, user: User) -> List[MedicineSchedule]:
    """
    Возвращает все расписания медикаментов пользователя.
    """
    result = await db.execute(
        select(MedicineSchedule).where(MedicineSchedule.user_cor_id == user.cor_id)
    )
    return result.scalars().all()


async def delete_medicine_schedule(db: AsyncSession, schedule: MedicineSchedule):
    """
    Удаляет расписание приёма медикамента.
    """
    await db.delete(schedule)
    await db.commit()