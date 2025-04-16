from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from cor_pass.database.models import Tag
from cor_pass.schemas import TagModel, TagResponse
from sqlalchemy.ext.asyncio import AsyncSession


async def get_tags(skip: int, limit: int, db: AsyncSession) -> List[Dict[str, Any]]:
    """
    Асинхронно отримує список тегів з бази даних.

    :param skip: Кількість тегів, які потрібно пропустити.
    :param limit: Максимальна кількість тегів для отримання.
    :param db: Асинхронна сесія бази даних для взаємодії з базою даних.
    :return: Список словників, що представляють теги.
    """
    stmt = select(Tag).offset(skip).limit(limit)
    result = await db.execute(stmt)
    tags = result.scalars().all()
    tag_dicts = [{"name": tag.name, "id": str(tag.id)} for tag in tags]
    return tag_dicts


async def get_tag(tag_id: int, db: AsyncSession) -> Tag | None:
    """
    Асинхронно отримує тег з бази даних за його ID.

    :param tag_id: ID тега, який потрібно отримати.
    :param db: Асинхронна сесія бази даних для взаємодії з базою даних.
    :return: Отриманий об'єкт тега або None, якщо тег не знайдено.
    """
    stmt = select(Tag).where(Tag.id == tag_id)
    result = await db.execute(stmt)
    tag = result.scalar_one_or_none()
    return tag


async def create_tag(body: TagModel, db: AsyncSession) -> TagResponse:
    """
    Асинхронно створює новий тег в базі даних.

    :param body: Дані тега, які використовуються для створення тега.
    :param db: Асинхронна сесія бази даних для взаємодії з базою даних.
    :return: Об'єкт відповіді створеного тега.
    """
    tag = Tag(name=body.name)
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return TagResponse(id=tag.id, name=tag.name)


async def update_tag(tag_id: int, body: TagModel, db: AsyncSession) -> Tag | None:
    """
    Асинхронно оновлює існуючий тег в базі даних.

    :param tag_id: ID тега, який потрібно оновити.
    :param body: Оновлені дані тега.
    :param db: Асинхронна сесія бази даних для взаємодії з базою даних.
    :return: Оновлений об'єкт тега, якщо знайдено, інакше None.
    """
    stmt = select(Tag).where(Tag.id == tag_id)
    result = await db.execute(stmt)
    tag = result.scalar_one_or_none()
    if tag:
        tag.name = body.name
        await db.commit()
        await db.refresh(tag)  # Оновлюємо об'єкт для відображення змін
        return tag
    return None


async def remove_tag(tag_id: int, db: AsyncSession) -> Tag | None:
    """
    Асинхронно видаляє тег з бази даних.

    :param tag_id: ID тега, який потрібно видалити.
    :param db: Асинхронна сесія бази даних для взаємодії з базою даних.
    :return: Видалений об'єкт тега, якщо знайдено, інакше None.
    """
    stmt = select(Tag).where(Tag.id == tag_id)
    result = await db.execute(stmt)
    tag = result.scalar_one_or_none()
    if tag:
        await db.delete(tag)
        await db.commit()
        return tag
    return None
