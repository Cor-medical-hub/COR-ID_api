from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from cor_pass.database.db import get_db
from cor_pass.database.models import User
from cor_pass.schemas import (
    FirstAidKitCreate,
    FirstAidKitUpdate,
    FirstAidKitRead,
    FirstAidKitItemCreate,
    FirstAidKitItemRead,
)
from cor_pass.repository.first_aid_kit import (
    create_first_aid_kit,
    get_user_first_aid_kits,
    get_first_aid_kit_by_id,
    update_first_aid_kit,
    delete_first_aid_kit,
    add_item_to_first_aid_kit,
    get_items_by_kit,
)
from cor_pass.services.auth import auth_service
from cor_pass.services.access import user_access

router = APIRouter(prefix="/first_aid_kits", tags=["First Aid Kits"])


@router.post(
    "/",
    response_model=FirstAidKitRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(user_access)],
    summary="Создать новую аптечку",
)
async def create_new_first_aid_kit(
    body: FirstAidKitCreate,
    current_user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Создает новую аптечку для текущего пользователя.
    """
    new_kit = await create_first_aid_kit(db=db, body=body, user=current_user)
    return new_kit


@router.get(
    "/my",
    response_model=List[FirstAidKitRead],
    dependencies=[Depends(user_access)],
    summary="Получить все аптечки текущего пользователя",
)
async def get_my_first_aid_kits(
    current_user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Возвращает список всех аптечек пользователя.
    """
    kits = await get_user_first_aid_kits(db=db, user=current_user)
    return kits


@router.put(
    "/{kit_id}",
    response_model=FirstAidKitRead,
    dependencies=[Depends(user_access)],
    summary="Обновить аптечку",
)
async def update_kit(
    kit_id: str,
    body: FirstAidKitUpdate,
    current_user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Обновляет данные аптечки пользователя.
    """
    kit = await get_first_aid_kit_by_id(db=db, kit_id=kit_id, user=current_user)
    if not kit:
        raise HTTPException(status_code=404, detail="Аптечка не найдена")

    updated = await update_first_aid_kit(db=db, kit=kit, body=body)
    return updated


@router.delete(
    "/{kit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(user_access)],
    summary="Удалить аптечку",
)
async def delete_kit(
    kit_id: str,
    current_user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Удаляет аптечку вместе с её содержимым.
    """
    kit = await get_first_aid_kit_by_id(db=db, kit_id=kit_id, user=current_user)
    if not kit:
        raise HTTPException(status_code=404, detail="Аптечка не найдена")

    await delete_first_aid_kit(db=db, kit=kit)
    return None




@router.post(
    "/{kit_id}/items",
    response_model=FirstAidKitItemRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(user_access)],
    summary="Добавить медикамент в аптечку",
)
async def add_item(
    kit_id: str,
    body: FirstAidKitItemCreate,
    current_user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Добавляет медикамент в аптечку пользователя.
    """
    kit = await get_first_aid_kit_by_id(db=db, kit_id=kit_id, user=current_user)
    if not kit:
        raise HTTPException(status_code=404, detail="Аптечка не найдена")

    new_item = await add_item_to_first_aid_kit(db=db, body=body)
    return new_item


@router.get(
    "/{kit_id}/items",
    response_model=List[FirstAidKitItemRead],
    dependencies=[Depends(user_access)],
    summary="Получить содержимое аптечки",
)
async def get_kit_items(
    kit_id: str,
    current_user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Возвращает список медикаментов, добавленных в аптечку пользователя.
    """
    kit = await get_first_aid_kit_by_id(db=db, kit_id=kit_id, user=current_user)
    if not kit:
        raise HTTPException(status_code=404, detail="Аптечка не найдена")

    items = await get_items_by_kit(db=db, kit_id=kit_id)
    return items