from datetime import datetime, timedelta
from typing import List
import uuid
from sqlalchemy import func, and_, select
from cor_pass.database.models import (
    AuthSessionStatus,
    CorIdAuthSession,
    User,
    UserSession,
)
from cor_pass.schemas import (
    InitiateLoginRequest,
    UserSessionModel,
)
from loguru import logger
from cor_pass.services.cipher import (
    encrypt_data,
    decrypt_user_key,
)
from sqlalchemy.ext.asyncio import AsyncSession


async def create_user_session(
    body: UserSessionModel, user: User, db: AsyncSession
) -> UserSession:
    """
    Асинхронно создает новую сессию пользователя или обновляет существующую.
    Для мобильных устройств используется связка (user_id, app_id, device_id).
    Для десктопа — (user_id, device_info).
    """

    if body.app_id and body.device_id:
        # Для мобильных
        stmt = select(UserSession).where(
            UserSession.user_id == user.cor_id,
            UserSession.app_id == body.app_id,
            UserSession.device_id == body.device_id,
        )
    else:
        # Для десктопа
        stmt = select(UserSession).where(
            UserSession.user_id == user.cor_id,
            UserSession.device_info == body.device_info,
        )

    result = await db.execute(stmt)
    existing_session = result.scalar_one_or_none()

    encrypted_refresh_token = await encrypt_data(
        data=body.refresh_token, key=await decrypt_user_key(user.unique_cipher_key)
    )
    encrypted_access_token = await encrypt_data(
        data=body.access_token, key=await decrypt_user_key(user.unique_cipher_key)
    )

    if existing_session:
        existing_session.refresh_token = encrypted_refresh_token
        existing_session.jti = body.jti
        existing_session.updated_at = func.now()
        existing_session.access_token = encrypted_access_token
        existing_session.device_os = body.device_os
        existing_session.device_info = body.device_info
        existing_session.app_id = body.app_id
        existing_session.device_id = body.device_id
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
            app_id=body.app_id,          
            device_id=body.device_id,    
            refresh_token=encrypted_refresh_token,
            jti=body.jti,
            access_token=encrypted_access_token,
        )
        try:
            db.add(new_session)
            await db.commit()
            await db.refresh(new_session)
            return new_session
        except Exception as e:
            await db.rollback()
            raise e


async def get_user_sessions_by_device(
    user_id: str, db: AsyncSession, app_id: str = None, device_id: str = None, device_info: str = None
) -> List[UserSession]:
    """
    Асинхронно получает все сессии пользователя на указанном устройстве.
    Для мобильных устройств используется (user_id, app_id, device_id).
    Для десктопа — (user_id, device_info).
    """

    if app_id and device_id:
        stmt = select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.app_id == app_id,
            UserSession.device_id == device_id,
        )
    elif device_info:
        stmt = select(UserSession).where(
            UserSession.user_id == user_id,
            UserSession.device_info == device_info,
        )
    else:
        return []

    result = await db.execute(stmt)
    sessions = result.scalars().all()
    return list(sessions)

async def get_user_sessions_by_device_info(
    user_id: str, device_info: str, db: AsyncSession
) -> List[UserSession]:
    """
    Асинхронно получает все сессии пользователя на указанном устройстве.
    """
    stmt = select(UserSession).where(
        UserSession.user_id == user_id,
        UserSession.device_info == device_info,
    )
    result = await db.execute(stmt)
    sessions = result.scalars().all()
    return list(sessions)


async def update_user_session_jti(db: AsyncSession, session_id: str, new_jti: str):
    """Обновляет JTI для существующей сессии."""
    result = await db.execute(select(UserSession).where(UserSession.id == session_id))
    session = result.scalar_one_or_none()
    if session:
        session.jti = new_jti
        await db.commit()
        await db.refresh(session)
    return session


async def update_session_token(
    user: User,
    token: str | None,
    device_info: str,
    jti: str,
    access_token: str,
    device_id: str| None,
    app_id: str| None,
    db: AsyncSession,
) -> UserSession | None:
    """
    Асинхронно обновляет refresh token для сессии пользователя на указанном устройстве.
    """
    try:
        if app_id and device_id:
            stmt = select(UserSession).where(
                UserSession.user_id == user.cor_id,
                UserSession.app_id == app_id,
                UserSession.device_id == device_id,
            )
        elif device_info:
            stmt = select(UserSession).where(
                UserSession.user_id == user.cor_id,
                UserSession.device_info == device_info,
            )
        result = await db.execute(stmt)
        existing_session = result.scalar_one_or_none()
        logger.debug(existing_session)
        key = await decrypt_user_key(user.unique_cipher_key)
        
        if token:
            if existing_session:
                if app_id and device_id == None:
                    encrypted_refresh_token = await encrypt_data(data=token, key=key)
                    encrypted_access_token = await encrypt_data(data=access_token, key=key)

                    existing_session.refresh_token = encrypted_refresh_token
                    existing_session.jti = jti
                    existing_session.updated_at = func.now()
                    existing_session.access_token = encrypted_access_token
                    existing_session.app_id = app_id
                    existing_session.device_id = str(uuid.uuid4())
                    try:
                        db.add(existing_session)
                        await db.commit()
                        await db.refresh(existing_session)
                        logger.debug("session token has updated")
                        return existing_session
                    except Exception as e:
                        await db.rollback()
                        raise e
                else:
                    encrypted_refresh_token = await encrypt_data(data=token, key=key)
                    encrypted_access_token = await encrypt_data(data=access_token, key=key)

                    existing_session.refresh_token = encrypted_refresh_token
                    existing_session.jti = jti
                    existing_session.updated_at = func.now()
                    existing_session.access_token = encrypted_access_token
                    try:
                        db.add(existing_session)
                        await db.commit()
                        await db.refresh(existing_session)
                        logger.debug("session token has updated")
                        return existing_session
                    except Exception as e:
                        await db.rollback()
                        raise e
        elif existing_session and token is None:
            return existing_session
        else:
            return None
    except Exception as e:
        raise Exception("Ошибка при поиске или обновлении сессии")


async def get_session_by_id(
    user: User, db: AsyncSession, session_id: str
) -> UserSession | None:
    """
    Асинхронно получает сессию пользователя по ее ID, проверяя принадлежность пользователя.
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
    Асинхронно получает все сессии конкретного юзера из базы данных с учетом пагинации.
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
    Асинхронно удаляет сессию пользователя по ее ID, проверяя принадлежность пользователя.
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
    Асинхронно создает запись сессии для авторизации по Cor ID.
    """
    email = request.email
    email = email.lower()
    cor_id = request.cor_id
    app_id = request.app_id
    device_id = str(uuid.uuid4())
    session_token = uuid.uuid4().hex
    expires_at = datetime.now() + timedelta(minutes=10)  # 10 минут на подтверждение

    db_session = CorIdAuthSession(
        email=email, cor_id=cor_id, session_token=session_token, expires_at=expires_at, app_id=app_id, device_id=device_id
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
    Асинхронно получает активную сессию авторизации по ее токену.
    """
    stmt = select(CorIdAuthSession).where(
        CorIdAuthSession.session_token == session_token,
        CorIdAuthSession.status == AuthSessionStatus.PENDING,
        CorIdAuthSession.expires_at > datetime.utcnow(),
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_auth_approved_session(
    session_token: str, db: AsyncSession
) -> CorIdAuthSession | None:
    """
    Асинхронно получает активную сессию авторизации по ее токену.
    """
    stmt = select(CorIdAuthSession).where(
        CorIdAuthSession.session_token == session_token,
        CorIdAuthSession.status == AuthSessionStatus.APPROVED,
        CorIdAuthSession.expires_at > datetime.utcnow(),
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_auth_session_by_token(
    session_token: str, db: AsyncSession
) -> CorIdAuthSession | None:
    """
    Асинхронно получает сессию авторизации по ее токену.
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
    Асинхронно обновляет статус сессии авторизации.
    """
    if confirmation_status == "approved":
        db_session.status = AuthSessionStatus.APPROVED
    elif confirmation_status == "rejected":
        db_session.status = AuthSessionStatus.REJECTED
    try:
        db.add(db_session)
        await db.commit()
        await db.refresh(db_session)
    except Exception as e:
        await db.rollback()
        raise e
