import uuid
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from cor_pass.database.models import (
    User,
    Patient,
    DoctorPatientStatus,
    PatientStatus,
    Doctor,
)

from cor_pass.schemas import (
    NewPatientRegistration,
    PasswordGeneratorSettings,
    UserModel,
)
from cor_pass.repository import person as repository_person

from cor_pass.repository.password_generator import generate_password
from cor_pass.repository import cor_id as repository_cor_id
from cor_pass.services.cipher import encrypt_data
from cor_pass.services.email import (
    send_email_code,
    send_email_code_forgot_password,
    send_email_code_with_temp_pass,
)
from cor_pass.config.config import settings
from cor_pass.services.access import user_access
from cor_pass.services.auth import auth_service
from cor_pass.services.logger import logger
from sqlalchemy.ext.asyncio import AsyncSession


async def register_new_patient(
    db: AsyncSession, body: NewPatientRegistration, doctor: Doctor
):
    """
    Асинхронно регистрирует нового пользователя как пациента и связывает его с врачом.
    """
    # 1. Генерируем временный пароль
    password_settings = PasswordGeneratorSettings()
    temp_password = generate_password(password_settings)
    hashed_password = auth_service.get_password_hash(temp_password)

    user_signup_data = UserModel(
        email=body.email,
        password=hashed_password,
        birth=body.birth_date.year,
        user_sex=body.sex,
    )
    new_user = await repository_person.create_user(user_signup_data, db)

    await db.flush()

    await repository_cor_id.create_new_corid(new_user, db)

    # 4. Создаем запись пациента
    new_patient = Patient(
        patient_cor_id=new_user.cor_id,
        encrypted_surname=await encrypt_data(
            body.surname.encode("utf-8"), settings.aes_key.encode()
        ),
        encrypted_first_name=await encrypt_data(
            body.first_name.encode("utf-8"), settings.aes_key.encode()
        ),
        encrypted_middle_name=(
            await encrypt_data(
                body.middle_name.encode("utf-8"), settings.aes_key.encode()
            )
            if body.middle_name
            else None
        ),
        birth_date=body.birth_date,
        sex=body.sex,
        email=body.email,
        phone_number=body.phone_number,
        address=body.address,
        # photo=body.photo.encode('utf-8') if body.photo else None, # Пример шифрования
    )
    db.add(new_patient)

    # 5. Связываем пациента с врачом через DoctorPatientStatus
    doctor_patient_status = DoctorPatientStatus(
        patient_id=new_patient.id,
        doctor_id=doctor.id,
        status=PatientStatus(body.status),
    )
    db.add(doctor_patient_status)

    await db.commit()

    # 6. Отправляем письмо с временным паролем
    await send_email_code_with_temp_pass(new_patient.email, temp_password)


async def add_existing_patient(
    db: AsyncSession, cor_id: str, doctor: Doctor, status: str = "registered"
):
    """
    Асинхронно добавляет существующего пользователя как пациента к врачу.
    """
    # 1. Находим пользователя по cor_id
    existing_user = await repository_person.get_user_by_corid(cor_id, db)
    if not existing_user:
        raise HTTPException(
            status_code=404, detail=f"Користувача з Cor ID {cor_id} не знайдено."
        )

    # 2. Проверяем, не является ли пользователь уже пациентом
    stmt_patient = select(Patient).where(Patient.patient_cor_id == cor_id)
    result_patient = await db.execute(stmt_patient)
    existing_patient = result_patient.scalar_one_or_none()
    if existing_patient:
        raise HTTPException(
            status_code=400, detail=f"Користувач з Cor ID {cor_id} вже є пацієнтом."
        )

    # 3. Создаем запись пациента
    new_patient = Patient(
        patient_cor_id=existing_user.cor_id,
        # Другие поля пациента (возможно, вам потребуется запросить эти данные)
    )
    db.add(new_patient)
    await db.flush()
    doctor_id_str = doctor.id

    # 4. Связываем пациента с врачом через DoctorPatientStatus
    doctor_patient_status = DoctorPatientStatus(
        patient_id=new_patient.id, doctor_id=doctor_id_str, status=PatientStatus(status)
    )
    db.add(doctor_patient_status)

    await db.commit()
