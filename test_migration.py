from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from cryptography.fernet import Fernet
import uuid
import base64
from datetime import datetime
from cor_pass.services.cipher import (
    generate_aes_key,
    encrypt_user_key,
    generate_recovery_code,
    encrypt_data,
)
import asyncio
from cor_pass.repository import person
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
import asyncio
from asyncio import WindowsSelectorEventLoopPolicy

# Set the event loop policy
asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())
# Настройки подключения к первой и второй базам
FIRST_DB_URL = "postgresql+psycopg://postgres:INPaOeOZjNekQlgv@localhost:5432/auth_db"
SECOND_DB_URL = "postgresql+psycopg://postgres:cormedpassword@localhost:54322/corpass_development"

first_engine = create_async_engine(FIRST_DB_URL, future=True, echo=True)
second_engine = create_async_engine(SECOND_DB_URL, future=True, echo=True)

FirstSession = sessionmaker(first_engine, class_=AsyncSession, expire_on_commit=False)
SecondSession = sessionmaker(second_engine, class_=AsyncSession, expire_on_commit=False)

# Генерация ключа для шифрования unique_cipher_key (рекомендуется хранить его в переменной окружения)
# AES_KEY = Fernet.generate_key()
# cipher = Fernet(AES_KEY)

# Импорт моделей
from cor_pass.database.models import User as SecondUser
from cor_pass.database.old_models import User as FirstUser

# Миграция данных
async def migrate_users():
    print("Connecting to first database...")
    async with FirstSession() as first_session, SecondSession() as second_session:
        print("Connected to both databases")
        user_index = 1
        try:
            # Выбираем пользователей из первой базы
            result = await first_session.execute(select(FirstUser))
            users = result.scalars().all()

            for user in users:
                # создаем ключ шифрования
                unique_cipher_key = await generate_aes_key()

                # создаем код восстановления
                recovery_code = await generate_recovery_code()
                encrypted_recovery_code = await encrypt_data(data=recovery_code, key=unique_cipher_key)

                unique_cipher_key = await encrypt_user_key(unique_cipher_key)

                # max_index = await person.get_max_user_index(second_session)
                # user_index = (max_index + 1) if max_index is not None else 1

                # Создаём запись для второй базы
                new_user = SecondUser(
                    id=user.id,
                    email=user.email,
                    password=user.password,
                    unique_cipher_key=unique_cipher_key,
                    recovery_code=encrypted_recovery_code,
                    user_sex=None,  # Значение по умолчанию
                    birth=None,  # Значение по умолчанию
                    user_index=user_index,
                    is_active=True,
                    created_at=datetime.now(),
                )

                # Добавляем запись во вторую базу
                second_session.add(new_user)
                user_index += 1 
            # Фиксируем изменения
            await second_session.commit()
            print(f"{len(users)} пользователей успешно перенесено.")

        except Exception as e:
            print("Ошибка при миграции:", e)
            await second_session.rollback()

if __name__ == "__main__":
    asyncio.run(migrate_users())