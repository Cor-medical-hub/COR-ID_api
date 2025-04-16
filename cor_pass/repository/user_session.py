from datetime import datetime, timedelta
from typing import List
import uuid
from sqlalchemy.orm import Session

from sqlalchemy import func, and_, select

from cor_pass.database.models import (
    AuthSessionStatus,
    CorIdAuthSession,
    User,
    Status,
    Verification,
    UserSettings,
    UserSession,
)
from cor_pass.schemas import (
    InitiateLoginRequest,
    UserModel,
    PasswordStorageSettings,
    MedicalStorageSettings,
    UserSessionDBModel,
    UserSessionModel,
)
from cor_pass.services.auth import auth_service
from cor_pass.services.logger import logger
from cor_pass.services.cipher import (
    generate_aes_key,
    encrypt_user_key,
    generate_recovery_code,
    encrypt_data,
    decrypt_user_key,
)
from sqlalchemy.ext.asyncio import AsyncSession


async def create_user_session(
    body: UserSessionModel, user: User, db: AsyncSession
) -> UserSession:
    """
    Асинхронно створює нову сесію користувача або оновлює існуючу.
    """
    # Шукаємо існуючу сесію для даного користувача та пристрою
    stmt = select(UserSession).where(
        UserSession.user_id == user.cor_id,
        UserSession.device_info == body.device_info,
    )
    result = await db.execute(stmt)
    existing_session = result.scalar_one_or_none()

    encrypted_refresh_token = await encrypt_data(
        data=body.refresh_token, key=await decrypt_user_key(user.unique_cipher_key)
    )

    if existing_session:
        # Якщо сесія існує, оновлюємо refresh_token та updated_at
        existing_session.refresh_token = encrypted_refresh_token
        existing_session.updated_at = func.now()
        try:
            db.add(existing_session)
            await db.commit()
            await db.refresh(existing_session)
            return existing_session
        except Exception as e:
            await db.rollback()
            raise e
    else:
        new_session = UserSession(
            user_id=user.cor_id,
            device_type=body.device_type,
            device_info=body.device_info,
            ip_address=body.ip_address,
            device_os=body.device_os,
            refresh_token=encrypted_refresh_token,
        )
        try:
            db.add(new_session)
            await db.commit()
            await db.refresh(new_session)
            return new_session
        except Exception as e:
            await db.rollback()
            raise e


async def get_user_sessions_by_device_info(
    user_id: str, device_info: str, db: AsyncSession
) -> List[UserSession]:
    """
    Асинхронно отримує всі сесії користувача на вказаному пристрої.
    """
    stmt = select(UserSession).where(
        UserSession.user_id == user_id,
        UserSession.device_info == device_info,
    )
    result = await db.execute(stmt)
    sessions = result.scalars().all()
    return list(sessions)


async def update_session_token(
    user: User, token: str | None, device_info: str, db: AsyncSession
) -> UserSession | None:
    """
    Асинхронно оновлює refresh token для сесії користувача на вказаному пристрої.

    :param user: User: Користувач, для якого оновлюється токен
    :param token: str | None: Новий токен сесії
    :param device_info: str: Інформація про пристрій користувача
    :param db: AsyncSession: Асинхронна сесія бази даних для збереження змін
    :return: Оновлену UserSession або None, якщо сесію не знайдено
    """
    try:
        stmt = select(UserSession).where(
            UserSession.user_id == user.cor_id,
            UserSession.device_info == device_info,
        )
        result = await db.execute(stmt)
        existing_session = result.scalar_one_or_none()

        if existing_session and token is not None:
            encrypted_refresh_token = await encrypt_data(
                data=token, key=await decrypt_user_key(user.unique_cipher_key)
            )
            # Якщо сесія існує, оновлюємо refresh_token
            existing_session.refresh_token = encrypted_refresh_token
            existing_session.updated_at = func.now()
            try:
                db.add(existing_session)
                await db.commit()
                await db.refresh(existing_session)
                print("session token has updated")
                return existing_session
            except Exception as e:
                await db.rollback()
                raise e
        elif existing_session and token is None:
            # Якщо токен None, нічого не оновлюємо, але повертаємо існуючу сесію
            return existing_session
        else:
            return None  # Повертаємо None, якщо сесію не знайдено
    except Exception as e:
        raise Exception("Помилка при пошуку або оновленні сесії")


async def get_session_by_id(user: User, db: AsyncSession, session_id: str):
    """
    Асинхронно отримує сесію користувача за її ID, перевіряючи приналежність користувачу.
    """
    stmt = (
        select(UserSession)
        .join(User, UserSession.user_id == User.cor_id)
        .where(and_(UserSession.id == session_id, User.cor_id == user.cor_id))
    )
    result = await db.execute(stmt)
    user_session = result.scalar_one_or_none()
    return user_session


async def get_all_user_sessions(
    db: AsyncSession, user_id: str, skip: int, limit: int
) -> List[UserSession]:
    """
    Асинхронно отримує всі сесії конкретного користувача з бази даних з урахуванням пагінації.
    """
    stmt = (
        select(UserSession)
        .where(UserSession.user_id == user_id)
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    sessions = result.scalars().all()
    return list(sessions)


async def delete_session(user: User, db: AsyncSession, session_id: str):
    """
    Асинхронно видаляє сесію користувача за її ID, перевіряючи приналежність користувачу.
    """
    stmt = (
        select(UserSession)
        .join(User, UserSession.user_id == User.cor_id)
        .where(and_(UserSession.id == session_id, User.cor_id == user.cor_id))
    )
    result = await db.execute(stmt)
    user_session = result.scalar_one_or_none()

    if not user_session:
        return None

    await db.delete(user_session)
    await db.commit()
    print("Session deleted")
    return user_session


async def create_auth_session(request: InitiateLoginRequest, db: AsyncSession) -> str:
    """
    Асинхронно створює запис сесії для авторизації за Cor ID.
    """
    email = request.email
    cor_id = request.cor_id
    session_token = uuid.uuid4().hex
    expires_at = datetime.now() + timedelta(minutes=10)  # 10 хвилин на підтвердження

    db_session = CorIdAuthSession(
        email=email, cor_id=cor_id, session_token=session_token, expires_at=expires_at
    )
    try:
        db.add(db_session)
        await db.commit()
        await db.refresh(db_session)
        return session_token
    except Exception as e:
        await db.rollback()
        raise e


async def get_auth_session(
    session_token: str, db: AsyncSession
) -> CorIdAuthSession | None:
    """
    Асинхронно отримує активну сесію авторизації за її токеном.
    """
    stmt = select(CorIdAuthSession).where(
        CorIdAuthSession.session_token == session_token,
        CorIdAuthSession.status == AuthSessionStatus.PENDING,
        CorIdAuthSession.expires_at > datetime.utcnow(),
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_auth_session_by_token(
    session_token: str, db: AsyncSession
) -> CorIdAuthSession | None:
    """
    Асинхронно отримує сесію авторизації за її токеном.
    """
    stmt = select(CorIdAuthSession).where(
        CorIdAuthSession.session_token == session_token
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_session_status(
    db_session: CorIdAuthSession,
    confirmation_status: AuthSessionStatus,
    db: AsyncSession,
):
    """
    Асинхронно оновлює статус сесії авторизації.
    """
    if confirmation_status == "approved":
        db_session.status = AuthSessionStatus.APPROVED
    elif confirmation_status == "rejected":
        db_session.status = AuthSessionStatus.REJECTED
    try:
        db.add(db_session)  # Ensure the session is added to the current transaction
        await db.commit()
        await db.refresh(db_session)
    except Exception as e:
        await db.rollback()
        raise e
