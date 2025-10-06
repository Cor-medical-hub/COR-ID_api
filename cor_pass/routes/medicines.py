from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from cor_pass.database.db import get_db
from cor_pass.database.models import User
from cor_pass.schemas import (
    MedicineCreate,
    MedicineUpdate,
    MedicineRead,
    MedicineScheduleCreate,
    MedicineScheduleRead,
    OintmentMedicine,
    OralMedicine,
    SolutionMedicine,
)
from cor_pass.repository.medicine import (
    create_medicine,
    get_user_medicines,
    get_medicine_by_id,
    update_medicine,
    delete_medicine,
    create_medicine_schedule,
    get_user_schedules,
)
from cor_pass.services.auth import auth_service
from cor_pass.services.access import user_access

router = APIRouter(prefix="/medicines", tags=["Medicines"])


@router.post(
    "/",
    response_model=MedicineRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(user_access)],
    summary="Создать новый медикамент",
)
async def create_new_medicine(
    body: MedicineCreate,
    current_user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Создает новый медикамент для текущего пользователя.
    В зависимости от способа введения сохраняет соответствующие поля.
    """
    new_medicine = await create_medicine(db=db, body=body, user=current_user)

    # Собираем method_data обратно в нужный подтип для ответа
    method_map = {
        "Перорально": OralMedicine,
        "Мазі/свічі": OintmentMedicine,
        "Внутрішньовенно": SolutionMedicine,
        "Внутрішньом’язово": SolutionMedicine,
        "Розчини": SolutionMedicine,
    }

    method_cls = method_map.get(new_medicine.intake_method)
    method_data = (
        method_cls(
            intake_method=new_medicine.intake_method,
            dosage=new_medicine.dosage,
            unit=new_medicine.unit,
            concentration=new_medicine.concentration,
            volume=new_medicine.volume,
        )
        if method_cls
        else None
    )

    response = MedicineRead(
        id=new_medicine.id,
        name=new_medicine.name,
        active_substance=new_medicine.active_substance,
        method_data=method_data,
        created_by=new_medicine.created_by,
        created_at=new_medicine.created_at,
        updated_at=new_medicine.updated_at,
    )
    return response


@router.get(
    "/my",
    response_model=List[MedicineRead],
    dependencies=[Depends(user_access)],
    summary="Получить все медикаменты текущего пользователя",
)
async def get_my_medicines(
    current_user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Возвращает список всех медикаментов текущего пользователя.
    """
    medicines = await get_user_medicines(db=db, user=current_user)
    result = []

    for med in medicines:
        method_map = {
            "Перорально": OralMedicine,
            "Мазі/свічі": OintmentMedicine,
            "Внутрішньовенно": SolutionMedicine,
            "Внутрішньом’язово": SolutionMedicine,
            "Розчини": SolutionMedicine,
        }

        method_cls = method_map.get(med.intake_method)
        method_data = (
            method_cls(
                intake_method=med.intake_method,
                dosage=med.dosage,
                unit=med.unit,
                concentration=med.concentration,
                volume=med.volume,
            )
            if method_cls
            else None
        )

        result.append(
            MedicineRead(
                id=med.id,
                name=med.name,
                active_substance=med.active_substance,
                method_data=method_data,
                created_by=med.created_by,
                created_at=med.created_at,
                updated_at=med.updated_at,
            )
        )

    return result


@router.put(
    "/{medicine_id}",
    response_model=MedicineRead,
    dependencies=[Depends(user_access)],
    summary="Обновить информацию о медикаменте",
)
async def update_medicine_info(
    medicine_id: str,
    body: MedicineUpdate,
    current_user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Обновляет данные конкретного медикамента.
    """
    medicine = await get_medicine_by_id(db=db, medicine_id=medicine_id)
    if not medicine:
        raise HTTPException(status_code=404, detail="Медикамент не найден")

    updated = await update_medicine(db=db, medicine=medicine, body=body)

    method_map = {
        "Перорально": OralMedicine,
        "Мазі/свічі": OintmentMedicine,
        "Внутрішньовенно": SolutionMedicine,
        "Внутрішньом’язово": SolutionMedicine,
        "Розчини": SolutionMedicine,
    }
    method_cls = method_map.get(updated.intake_method)
    method_data = (
        method_cls(
            intake_method=updated.intake_method,
            dosage=updated.dosage,
            unit=updated.unit,
            concentration=updated.concentration,
            volume=updated.volume,
        )
        if method_cls
        else None
    )

    response = MedicineRead(
        id=updated.id,
        name=updated.name,
        active_substance=updated.active_substance,
        method_data=method_data,
        created_by=updated.created_by,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )
    return response


@router.delete(
    "/{medicine_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(user_access)],
    summary="Удалить медикамент",
)
async def delete_medicine_by_id(
    medicine_id: str,
    current_user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Удаляет медикамент пользователя.
    """
    medicine = await get_medicine_by_id(db=db, medicine_id=medicine_id)
    if not medicine:
        raise HTTPException(status_code=404, detail="Медикамент не найден")

    await delete_medicine(db=db, medicine=medicine)
    return None




@router.post(
    "/schedules",
    response_model=MedicineScheduleRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(user_access)],
    summary="Создать расписание приёма медикамента",
)
async def create_schedule(
    body: MedicineScheduleCreate,
    current_user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Создает новое расписание приёма медикамента для пользователя.
    """
    new_schedule = await create_medicine_schedule(db=db, body=body, user=current_user)
    return new_schedule


@router.get(
    "/schedules/my",
    response_model=List[MedicineScheduleRead],
    dependencies=[Depends(user_access)],
    summary="Получить все расписания медикаментов текущего пользователя",
)
async def get_my_schedules(
    current_user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Возвращает список всех расписаний медикаментов текущего пользователя.
    """
    schedules = await get_user_schedules(db=db, user=current_user)
    return schedules