from datetime import datetime, timedelta
from typing import List
import uuid
from sqlalchemy.orm import Session

from sqlalchemy import func, and_

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


async def create_user_session(
    body: UserSessionModel, user: User, db: Session
) -> UserSessionModel:
    # Ищем существующую сессию для данного пользователя и устройства
    existing_session = (
        db.query(UserSession)
        .filter(
            UserSession.user_id == user.cor_id,
            UserSession.device_info == body.device_info,
        )
        .first()
    )

    if existing_session:
        encrypded_refresh_token = await encrypt_data(
            data=body.refresh_token, key=await decrypt_user_key(user.unique_cipher_key)
        )
        # Если сессия существует, обновляем refresh_token
        existing_session.refresh_token = encrypded_refresh_token
        existing_session.updated_at = func.now()
        try:
            db.add(existing_session)
            db.commit()
            db.refresh(existing_session)
            return existing_session
        except Exception as e:
            db.rollback()
            raise e
    else:
        encrypded_refresh_token = await encrypt_data(
            data=body.refresh_token, key=await decrypt_user_key(user.unique_cipher_key)
        )
        new_session = UserSession(
            user_id=user.cor_id,
            device_type=body.device_type,
            device_info=body.device_info,
            ip_address=body.ip_address,
            device_os=body.device_os,
            refresh_token=encrypded_refresh_token,
        )
        try:
            db.add(new_session)
            db.commit()
            db.refresh(new_session)
            return new_session
        except Exception as e:
            db.rollback()
            raise e


async def get_user_sessions_by_device_info(
    user_id: str, device_info: str, db: Session
) -> List[UserSession]:
    """
    Получает все сессии пользователя на указанном устройстве.
    """
    return (
        db.query(UserSession)
        .filter(
            UserSession.user_id == user_id,
            UserSession.device_info == device_info,
        )
        .all()
    )


async def update_session_token(
    user: User, token: str | None, device_info, db: Session
) -> None:
    """
    The update_token function updates the refresh token for a user.

    :param user: User: Identify the user that is being updated
    :param token: str | None: Pass the token to the function
    :param db: Session: Commit the changes to the database
    :return: None, so the return type should be none
    """
    try:
        existing_session = (
            db.query(UserSession)
            .filter(
                UserSession.user_id == user.cor_id,
                UserSession.device_info == device_info,
            )
            .first()
        )
        if existing_session:
            encrypded_refresh_token = await encrypt_data(
                data=token, key=await decrypt_user_key(user.unique_cipher_key)
            )
            # Если сессия существует, обновляем refresh_token
            existing_session.refresh_token = encrypded_refresh_token
            existing_session.updated_at = func.now()
            try:
                db.add(existing_session)
                db.commit()
                db.refresh(existing_session)
                print("session token has updated")
                return existing_session
            except Exception as e:
                db.rollback()
                raise e
    except Exception as e:
        raise "Sessions not found"


async def get_session_by_id(user: User, db: Session, session_id: str):
    print(session_id)
    user_session = (
        db.query(UserSession)
        .join(User, UserSession.user_id == User.cor_id)
        .filter(and_(UserSession.id == session_id, User.cor_id == user.cor_id))
        .first()
    )
    return user_session


async def get_all_user_sessions(db: Session, user_id: str, skip: int, limit: int):
    sessions = (
        db.query(UserSession).filter_by(user_id=user_id).offset(skip).limit(limit).all()
    )
    return sessions


async def delete_session(user: User, db: Session, session_id: str):
    user_session = (
        db.query(UserSession)
        .join(User, UserSession.user_id == User.cor_id)
        .filter(and_(UserSession.id == session_id, User.cor_id == user.cor_id))
        .first()
    )
    if not user_session:
        return None
    if user_session:
        db.delete(user_session)
        db.commit()
        print("Session deleted")
    return user_session




async def create_auth_session(request: User, db: Session):
    email = request.email
    session_token = uuid.uuid4().hex
    expires_at = datetime.now() + timedelta(minutes=10)  # 10 минут на подтверждение

    db_session = CorIdAuthSession(email=email, session_token=session_token, expires_at=expires_at)
    try:
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
        return session_token
    except Exception as e:
        db.rollback()
        raise e
    
async def get_auth_session(session_token: str, db: Session) -> CorIdAuthSession | None:
    return db.query(CorIdAuthSession).filter(
        CorIdAuthSession.session_token == session_token,
        CorIdAuthSession.status == AuthSessionStatus.PENDING,
        CorIdAuthSession.expires_at > datetime.utcnow()
    ).first()


async def update_session_status(db_session: CorIdAuthSession, confirmation_status: AuthSessionStatus, db: Session):
    if confirmation_status == "approved":
        db_session.status = AuthSessionStatus.APPROVED

    elif confirmation_status == "rejected":
        db_session.status = AuthSessionStatus.REJECTED
    try:
        db.commit()
        db.refresh(db_session)
    except Exception as e:
        db.rollback()
        raise e