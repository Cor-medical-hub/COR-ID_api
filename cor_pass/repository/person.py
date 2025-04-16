from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.future import select
from sqlalchemy import func
import uuid
from datetime import datetime
from cor_pass.database.models import (
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
from cor_pass.services.email import send_email_code_with_qr
from sqlalchemy.exc import NoResultFound

from sqlalchemy.ext.asyncio import AsyncSession


async def get_user_by_email(email: str, db: AsyncSession) -> User | None:
    """
    Асинхронно отримує користувача за його email.

    :param email: str: Email користувача, якого потрібно отримати
    :param db: AsyncSession: Асинхронна сесія бази даних
    :return: Першого користувача, знайденого за вказаним email
    """
    email_lower = email.lower()
    stmt = select(User).where(User.email.ilike(email_lower))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    return user


async def get_user_by_uuid(uuid: str, db: AsyncSession) -> User | None:
    """
    Асинхронно отримує користувача за його UUID.

    :param uuid: str: UUID користувача, якого потрібно отримати
    :param db: AsyncSession: Асинхронна сесія бази даних
    :return: Першого користувача, знайденого за вказаним UUID
    """
    stmt = select(User).where(User.id == uuid)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    return user


async def get_user_by_corid(cor_id: str, db: AsyncSession) -> User | None:
    """
    Асинхронно отримує користувача за його Cor ID.

    :param cor_id: str: Cor ID користувача, якого потрібно отримати
    :param db: AsyncSession: Асинхронна сесія бази даних
    :return: Першого користувача, знайденого за вказаним Cor ID
    """
    stmt = select(User).where(User.cor_id == cor_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    return user


async def get_max_user_index(db: AsyncSession) -> int | None:
    """Асинхронно отримує максимальний user_index з бази даних."""
    result = await db.execute(select(func.max(User.user_index)))
    return result.scalar_one_or_none()


async def create_user(body: UserModel, db: AsyncSession) -> User:
    """
    Асинхронно створює нового користувача в базі даних.

        Args:
            body (UserModel): Об'єкт UserModel, що містить інформацію для додавання до бази даних.
            db (AsyncSession): Асинхронна сесія SQLAlchemy для запитів та оновлень даних.
        Returns:
            User: Об'єкт User, що представляє новоствореного користувача.

    :param body: UserModel: Передає дані з тіла запиту до функції create_user
    :param db: AsyncSession: Створює асинхронну сесію бази даних
    :return: Об'єкт користувача
    """

    new_user = User(**body.model_dump())
    new_user.id = str(uuid.uuid4())

    user_settings = UserSettings(user_id=new_user.id)
    max_index = await get_max_user_index(db)
    new_user.user_index = (max_index + 1) if max_index is not None else 1
    new_user.account_status = Status.basic
    new_user.unique_cipher_key = await generate_aes_key()  # ->bytes
    new_user.recovery_code = await generate_recovery_code()
    await send_email_code_with_qr(
        new_user.email, host=None, recovery_code=new_user.recovery_code
    )
    encrypted_recovery_code = await encrypt_data(
        data=new_user.recovery_code, key=new_user.unique_cipher_key
    )

    new_user.unique_cipher_key = await encrypt_user_key(new_user.unique_cipher_key)
    new_user.recovery_code = encrypted_recovery_code

    try:
        db.add(new_user)
        db.add(user_settings)
        await db.commit()
        await db.refresh(new_user)
        await db.refresh(user_settings)
        return new_user
    except Exception as e:
        await db.rollback()
        raise e


async def update_token(user: User, token: str | None, db: AsyncSession) -> None:
    """
    Асинхронно оновлює refresh token для користувача.

    :param user: User: Користувач, якого потрібно оновити
    :param token: str | None: Новий refresh token
    :param db: AsyncSession: Асинхронна сесія бази даних для збереження змін
    :return: None
    """
    user.refresh_token = token
    await db.commit()
    await db.refresh(user)


async def get_users(skip: int, limit: int, db: AsyncSession) -> list[User]:
    """
    Асинхронно повертає список всіх користувачів з бази даних.

    :param skip: int: Пропустити перші n записів у базі даних
    :param limit: int: Обмежити кількість повернутих результатів
    :param db: AsyncSession: Асинхронна сесія бази даних
    :return: Список всіх користувачів
    """
    stmt = select(User).offset(skip).limit(limit)
    result = await db.execute(stmt)
    users = result.scalars().all()
    return list(users)


# переписать
async def make_user_status(
    email: str, account_status: Status, db: AsyncSession
) -> None:
    """
    Асинхронно оновлює статус користувача на вказаний.

    Args:
        email (str): Email користувача.
        status (Status): Новий статус для користувача.
        db (AsyncSession): Асинхронна сесія бази даних.

    :param email: str: Отримати користувача за email
    :param status: Status: Встановити статус користувача
    :param db: AsyncSession: Передати асинхронну сесію бази даних до функції
    :return: None
    """

    user = await get_user_by_email(email, db)
    if user:
        user.account_status = account_status
        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise e


async def get_user_status(email: str, db: AsyncSession) -> Status | None:
    """
    Асинхронно отримує статус користувача за його email.
    """
    user = await get_user_by_email(email, db)
    if user:
        return user.account_status
    return None


async def write_verification_code(
    email: str, db: AsyncSession, verification_code: int
) -> None:
    """
    Асинхронно записує або оновлює код верифікації для вказаного email.

    :param email: str: Email адреса користувача для підтвердження
    :param db: AsyncSession: Асинхронна сесія бази даних
    :param verification_code: int: Код верифікації для запису
    :return: None
    """
    stmt = select(Verification).where(Verification.email == email)
    result = await db.execute(stmt)
    verification_record = result.scalar_one_or_none()

    if verification_record:
        verification_record.verification_code = verification_code
        try:
            await db.commit()
            logger.debug("Оновлено код верифікації в існуючому записі")
        except Exception as e:
            await db.rollback()
            raise e
    else:
        verification_record = Verification(
            email=email, verification_code=verification_code
        )
        try:
            db.add(verification_record)
            await db.commit()
            await db.refresh(verification_record)
            logger.debug("Створено новий запис верифікації")
        except Exception as e:
            await db.rollback()
            raise e


async def verify_verification_code(
    email: str, db: AsyncSession, verification_code: int
) -> bool:
    """
    Асинхронно перевіряє код верифікації для вказаного email.

    :param email: str: Email адреса користувача для підтвердження
    :param db: AsyncSession: Асинхронна сесія бази даних
    :param verification_code: int: Код верифікації для перевірки
    :return: True, якщо код вірний та знайдено запис, False в іншому випадку.
    """
    try:
        stmt = select(Verification).where(Verification.email == email)
        result = await db.execute(stmt)
        verification_record = result.scalar_one_or_none()

        if (
            verification_record
            and verification_record.verification_code == verification_code
        ):
            verification_record.email_confirmation = True
            await db.commit()
            return True
        else:
            return False
    except Exception as e:
        raise e


async def change_user_password(email: str, password: str, db: AsyncSession) -> None:
    """
    Асинхронно змінює пароль користувача.
    """
    user = await get_user_by_email(email, db)
    if user:
        hashed_password = auth_service.get_password_hash(password)
        user.password = hashed_password
        user.last_password_change = datetime.now()
        try:
            await db.commit()
            logger.debug("Password has changed")
        except Exception as e:
            await db.rollback()
            raise e
    else:
        logger.warning(f"User with email {email} not found during password change.")
        # Вирішіть, чи потрібно тут викидати виняток або просто логувати


async def change_user_email(email: str, current_user, db: AsyncSession) -> None:
    """
    Асинхронно змінює email користувача.
    """
    current_user.email = email
    try:
        await db.commit()
        logger.debug("Email has changed")
    except Exception as e:
        await db.rollback()
        raise e


async def add_user_backup_email(
    email: str, current_user: User, db: AsyncSession
) -> None:
    """
    Асинхронно додає резервний email користувачу.
    """
    current_user.backup_email = email
    try:
        await db.commit()
        logger.debug("Backup email has added")
    except Exception as e:
        await db.rollback()
        raise e


async def delete_user_by_email(db: AsyncSession, email: str):
    """
    Асинхронно видаляє користувача за його email.
    """
    try:
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        user = result.scalar_one()

        await db.delete(user)
        await db.commit()
    except NoResultFound:
        print("Користувача не знайдено.")
    except Exception as e:
        await db.rollback()
        print(f"Произошла ошибка при удалении користувача: {e}")


async def get_settings(user: User, db: AsyncSession):
    """
    Асинхронно отримує налаштування користувача. Якщо налаштування відсутні, створює нові.
    """
    stmt = (
        select(UserSettings)
        .join(User, UserSettings.user_id == User.id)
        .where(UserSettings.user_id == user.id)
    )
    result = await db.execute(stmt)
    user_settings = result.scalar_one_or_none()

    if user_settings:
        return user_settings
    else:
        user_settings = UserSettings(user_id=user.id)
        try:
            db.add(user_settings)
            await db.commit()
            await db.refresh(user_settings)
            logger.debug("Created new user_settings")
        except Exception as e:
            await db.rollback()
            raise e
        return user_settings


async def get_max_user_index(db: AsyncSession):
    """
    Асинхронно отримує максимальне значення user_index з таблиці User.
    """
    try:
        result = await db.execute(select(func.max(User.user_index)))
        max_index = result.scalar_one_or_none()
        if max_index is None:
            logger.debug("No users found in the database.")
            return None
        return max_index
    except Exception as e:
        logger.error(f"Failed to get max user_index: {e}")
        await db.rollback()
        raise e


async def change_password_storage_settings(
    current_user: User, settings: PasswordStorageSettings, db: AsyncSession
) -> UserSettings:
    """
    Асинхронно змінює налаштування зберігання паролів користувача.
    Якщо налаштування відсутні, створює нові.
    """
    stmt = (
        select(UserSettings)
        .join(User, UserSettings.user_id == User.id)
        .where(UserSettings.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    user_settings = result.scalar_one_or_none()

    if user_settings:
        user_settings.local_password_storage = settings.local_password_storage
        user_settings.cloud_password_storage = settings.cloud_password_storage
        await db.commit()
        await db.refresh(user_settings)
    else:
        user_settings = UserSettings(
            user_id=current_user.id,
            local_password_storage=settings.local_password_storage,
            cloud_password_storage=settings.cloud_password_storage,
        )
        try:
            db.add(user_settings)
            await db.commit()
            await db.refresh(user_settings)
            logger.debug("Created new user_settings")
        except Exception as e:
            await db.rollback()
            raise e
    return user_settings


async def change_medical_storage_settings(
    current_user: User, settings: MedicalStorageSettings, db: AsyncSession
) -> UserSettings:
    """
    Асинхронно змінює налаштування зберігання медичних даних користувача.
    Якщо налаштування відсутні, створює нові.
    """
    stmt = (
        select(UserSettings)
        .join(User, UserSettings.user_id == User.id)
        .where(UserSettings.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    user_settings = result.scalar_one_or_none()

    if user_settings:
        user_settings.local_medical_storage = settings.local_medical_storage
        user_settings.cloud_medical_storage = settings.cloud_medical_storage
        await db.commit()
        await db.refresh(user_settings)
    else:
        user_settings = UserSettings(
            user_id=current_user.id,
            local_medical_storage=settings.local_medical_storage,
            cloud_medical_storage=settings.cloud_medical_storage,
        )
        try:
            db.add(user_settings)
            await db.commit()
            await db.refresh(user_settings)
            logger.debug("Created new user_settings")
        except Exception as e:
            await db.rollback()
            raise e
    return user_settings


async def deactivate_user(email: str, db: AsyncSession) -> None:
    """
    Асинхронно деактивує обліковий запис користувача за вказаною email-адресою.

    :param email: str: Email адреса користувача для деактивації
    :param db: AsyncSession: Асинхронна сесія бази даних
    :return: None
    """
    user = await get_user_by_email(email, db)
    if user:
        user.is_active = False
        try:
            await db.commit()
            await db.refresh(user)
        except Exception as e:
            await db.rollback()
            raise e


async def activate_user(email: str, db: AsyncSession) -> None:
    """
    Асинхронно активує обліковий запис користувача за вказаною email-адресою.

    :param email: str: Email адреса користувача для активації
    :param db: AsyncSession: Асинхронна сесія бази даних
    :return: None
    """
    user = await get_user_by_email(email, db)
    if user:
        user.is_active = True
        try:
            await db.commit()
            await db.refresh(user)
        except Exception as e:
            await db.rollback()
            raise e


async def get_last_password_change(email: str, db: AsyncSession) -> Optional[datetime]:
    """
    Асинхронно отримує дату останньої зміни пароля користувача за його email.
    Повертає None, якщо користувача не знайдено.
    """
    user = await get_user_by_email(email, db)
    if user:
        return user.last_password_change
    return None
