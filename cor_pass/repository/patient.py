import base64
from typing import Optional
import uuid
from fastapi import HTTPException, status
from sqlalchemy import select
from cor_pass.database.models import (
    Patient,
    DoctorPatientStatus,
    PatientClinicStatus,
    PatientStatus,
    Doctor
)
from cor_pass.database.models import PatientClinicStatusModel as db_PatientClinicStatus
from cor_pass.schemas import (
    ExistingPatientRegistration,
    NewPatientRegistration,
    PasswordGeneratorSettings,
    PatientCreationResponse,
    UserModel,
)
from cor_pass.repository import person as repository_person
from cor_pass.repository.password_generator import generate_password
from cor_pass.repository import cor_id as repository_cor_id
from cor_pass.services.cipher import encrypt_data
from cor_pass.services.email import (
    send_email_code_with_temp_pass,
)
from cor_pass.config.config import settings
from cor_pass.services.auth import auth_service
from cor_pass.services.logger import logger
from sqlalchemy.ext.asyncio import AsyncSession


async def register_new_patient(
    db: AsyncSession, body: NewPatientRegistration, doctor: Doctor
):
    """
    Асинхронно регистрирует нового пользователя как пациента и связывает его с врачом.
    """
    # Генерируем временный пароль
    password_settings = PasswordGeneratorSettings()
    temp_password = generate_password(password_settings)
    hashed_password = auth_service.get_password_hash(temp_password)

    user_signup_data = UserModel(
        email=body.email,
        password=temp_password,
        birth=body.birth_date.year,
        user_sex=body.sex,
    )
    hashed_password = auth_service.get_password_hash(temp_password)
    user_signup_data.password = hashed_password

    new_user = await repository_person.create_user(user_signup_data, db)

    await db.flush()

    await repository_cor_id.create_new_corid(new_user, db)
    decoded_key = base64.b64decode(settings.aes_key)

    new_patient = Patient(
        patient_cor_id=new_user.cor_id,
        encrypted_surname=await encrypt_data(body.surname.encode("utf-8"), decoded_key),
        encrypted_first_name=await encrypt_data(
            body.first_name.encode("utf-8"), decoded_key
        ),
        encrypted_middle_name=(
            await encrypt_data(body.middle_name.encode("utf-8"), decoded_key)
            if body.middle_name
            else None
        ),
        birth_date=body.birth_date,
        sex=body.sex,
        email=body.email,
        phone_number=body.phone_number,
        address=body.address,
    )
    db.add(new_patient)
    await db.commit()

    doctor_patient_status = DoctorPatientStatus(
        patient_id=new_patient.id,
        doctor_id=doctor.id,
        status=PatientStatus.registered,
    )
    db.add(doctor_patient_status)

    await db.commit()

    clinic_patient_status = db_PatientClinicStatus(
        patient_id=new_patient.id,
        patient_status_for_clinic=PatientClinicStatus.registered,
    )
    db.add(clinic_patient_status)

    await db.commit()

    await send_email_code_with_temp_pass(
        email=new_patient.email, temp_pass=temp_password
    )
    return new_patient


async def add_existing_patient(
    db: AsyncSession, cor_id: str, doctor: Doctor, status: str = "registered"
):
    """
    Асинхронно добавляет существующего пользователя как пациента к врачу.
    """

    existing_user = await repository_person.get_user_by_corid(cor_id, db)
    if not existing_user:
        raise HTTPException(
            status_code=404, detail=f"Пользователь с Cor ID {cor_id} не найден."
        )

    stmt_patient = select(Patient).where(Patient.patient_cor_id == cor_id)
    result_patient = await db.execute(stmt_patient)
    existing_patient = result_patient.scalar_one_or_none()
    if existing_patient:
        raise HTTPException(
            status_code=400,
            detail=f"Пользователь с Cor ID {cor_id} уже является пациентом.",
        )

    new_patient = Patient(
        patient_cor_id=existing_user.cor_id,
        sex=existing_user.user_sex,
        email=existing_user.email,
    )
    db.add(new_patient)
    await db.flush()
    doctor_id_str = doctor.id

    doctor_patient_status = DoctorPatientStatus(
        patient_id=new_patient.id, doctor_id=doctor_id_str, status=PatientStatus(status)
    )
    db.add(doctor_patient_status)

    clinic_patient_status = db_PatientClinicStatus(
    patient_id=new_patient.id,
    patient_status_for_clinic=PatientClinicStatus.registered,
    )
    db.add(clinic_patient_status)

    await db.commit()

    return new_patient


async def get_patient_by_corid(db: AsyncSession, cor_id: str):

    existing_user = await repository_person.get_user_by_corid(cor_id, db)
    if not existing_user:
        raise HTTPException(
            status_code=404, detail=f"Пользователь с Cor ID {cor_id} не найден."
        )

    stmt_patient = select(Patient).where(Patient.patient_cor_id == cor_id)
    result_patient = await db.execute(stmt_patient)
    existing_patient = result_patient.scalar_one_or_none()
    if not existing_patient:
        raise HTTPException(
            status_code=404, detail=f"Пациент с Cor ID {cor_id} не найден."
        )
    return existing_patient




# новые функции создания пациента

async def _create_patient_internal(
    db: AsyncSession, 
    patient_data: NewPatientRegistration, 
    doctor: Doctor, 
    user_id: Optional[str] = None, 
    patient_cor_id_value: Optional[str] = None,
    send_email: bool = False, 
    temp_password: Optional[str] = None 
) -> PatientCreationResponse:
    """
    Внутренняя вспомогательная функция для создания пациента.
    user_id: ID пользователя, если пациент привязывается к существующему пользователю.
    patient_cor_id_value: Значение patient_cor_id, если оно определено заранее (например, от user.cor_id).
    send_email: Флаг для отправки email, если был создан новый пользователь.
    temp_password: Временный пароль, если создан новый пользователь, для отправки по email.
    """
    
    decoded_key = base64.b64decode(settings.aes_key)

    # Определяем patient_cor_id
    if patient_cor_id_value:
        final_patient_cor_id = patient_cor_id_value
    else:
        # Если patient_cor_id не передан, генерируем новый уникальный
        final_patient_cor_id = await repository_cor_id.create_only_corid(birth=patient_data.birth_date.year, user_sex=patient_data.sex, db=db)

    # Проверяем уникальность patient_cor_id (если он не от пользователя)
    # Если patient_cor_id_value был передан, предполагаем, что его уникальность уже проверена (например, user.cor_id)
    if not patient_cor_id_value: # Проверяем только если мы сами его сгенерировали
        existing_patient_with_corid = await db.execute(
            select(Patient).where(Patient.patient_cor_id == final_patient_cor_id)
        )
        if existing_patient_with_corid.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, # Conflict, так как ID уже есть
                detail=f"Сгенерированный patient_cor_id '{final_patient_cor_id}' уже существует. Повторите попытку."
            )

    new_patient = Patient(
        id=str(uuid.uuid4()), # Генерируем новый UUID для ID пациента
        patient_cor_id=final_patient_cor_id,
        user_id=user_id, # Может быть None
        encrypted_surname=await encrypt_data(patient_data.surname.encode("utf-8"), decoded_key),
        encrypted_first_name=await encrypt_data(
            patient_data.first_name.encode("utf-8"), decoded_key
        ),
        encrypted_middle_name=(
            await encrypt_data(patient_data.middle_name.encode("utf-8"), decoded_key)
            if patient_data.middle_name
            else None
        ),
        birth_date=patient_data.birth_date,
        sex=patient_data.sex,
        email=patient_data.email, 
        phone_number=patient_data.phone_number,
        address=patient_data.address,
    )
    db.add(new_patient)
    await db.flush() # Flush, чтобы new_patient.id был доступен

    # Связываем с врачом
    doctor_patient_status = DoctorPatientStatus(
        patient_id=new_patient.id,
        doctor_id=doctor.id,
        status=PatientStatus.registered,
    )
    db.add(doctor_patient_status)

    # Связываем с клиникой (если это общий статус для всех пациентов)
    clinic_patient_status = db_PatientClinicStatus(
        patient_id=new_patient.id,
        patient_status_for_clinic=PatientClinicStatus.registered,
    )
    db.add(clinic_patient_status)

    await db.commit()
    await db.refresh(new_patient) # Обновляем объект, чтобы получить актуальные данные из БД

    # Отправляем email, если это сценарий с новым пользователем
    if send_email and new_patient.email and temp_password:
        await send_email_code_with_temp_pass(
            email=new_patient.email, temp_pass=temp_password
        )

    return PatientCreationResponse.model_validate(new_patient)

# Если пользователь существует 
async def create_patient_linked_to_user(
    db: AsyncSession, patient_data: ExistingPatientRegistration, doctor: Doctor, user_cor_id: str
) -> PatientCreationResponse:
    """
    Создает пациента, связанного с существующим пользователем по его COR ID.
    Если пользователь не найден или уже имеет пациента, выбрасывается HTTPException.
    """
    existing_user = await repository_person.get_user_by_corid(user_cor_id, db)
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Пользователь с Cor ID '{user_cor_id}' не найден."
        )

    existing_patient_for_user = await db.execute(
        select(Patient).where(Patient.user_id == existing_user.id)
    )
    if existing_patient_for_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail=f"Пользователь с Cor ID '{user_cor_id}' уже связан с пациентом."
        )

    if not existing_user.cor_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"У пользователя с ID '{existing_user.id}' отсутствует COR ID."
        )

    new_patient = Patient(
            id=str(uuid.uuid4()), 
            patient_cor_id=user_cor_id,
            user_id=existing_user.id,
            encrypted_surname=None,
            encrypted_first_name=None,
            encrypted_middle_name=None,
            birth_date=None,
            sex=patient_data.sex,
            email=patient_data.email, 
            phone_number=None,
            address=None,
        )
    db.add(new_patient)
    await db.flush() 
    doctor_patient_status = DoctorPatientStatus(
        patient_id=new_patient.id,
        doctor_id=doctor.id,
        status=PatientStatus.registered,
    )
    db.add(doctor_patient_status)

    clinic_patient_status = db_PatientClinicStatus(
        patient_id=new_patient.id,
        patient_status_for_clinic=PatientClinicStatus.registered,
    )
    db.add(clinic_patient_status)

    await db.commit()
    await db.refresh(new_patient)
    return PatientCreationResponse.model_validate(new_patient)


async def create_patient_and_user_by_email(
    db: AsyncSession, patient_data: NewPatientRegistration, doctor: Doctor
) -> PatientCreationResponse:
    """
    Создает нового пользователя и связанного с ним пациента.
    Если пользователь с таким email уже существует, выбрасывается HTTPException.
    """
    # Проверяем, существует ли уже пользователь с таким email
    existing_user_by_email = await repository_person.get_user_by_email(patient_data.email, db)
    if existing_user_by_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Пользователь с email '{patient_data.email}' уже зарегистрирован."
        )

    # 1. Создаем нового пользователя
    password_settings = PasswordGeneratorSettings()
    temp_password = generate_password(password_settings)
    hashed_password = auth_service.get_password_hash(temp_password)

    user_signup_data = UserModel(
        email=patient_data.email,
        password=temp_password, # Пароль будет перехэширован внутри create_user
        birth=patient_data.birth_date.year,
        user_sex=patient_data.sex,
    )
    user_signup_data.password = hashed_password # Присваиваем хэшированный пароль

    new_user = await repository_person.create_user(user_signup_data, db)
    await db.flush() # Flush, чтобы получить new_user.id и cor_id, если он генерируется

    # Если cor_id генерируется асинхронно или после flush, убедитесь, что он есть
    # Это важно, если create_user не гарантирует наличие cor_id сразу
    if not new_user.cor_id:
        await repository_cor_id.create_new_corid(new_user, db) # Убедимся, что у пользователя есть cor_id
        await db.refresh(new_user) # Обновим, чтобы получить cor_id

    # 2. Создаем пациента, связанного с новым пользователем
    # Используем данные пациента из NewPatientData, а user_id и patient_cor_id от нового пользователя
    return await _create_patient_internal(
        db=db,
        patient_data=patient_data, # Данные пациента
        doctor=doctor,
        user_id=new_user.id, # Связываем с только что созданным пользователем
        patient_cor_id_value=new_user.cor_id, # Используем COR ID нового пользователя
        send_email=True, # Отправляем email с временным паролем
        temp_password=temp_password
    )


async def create_standalone_patient(
    db: AsyncSession, patient_data: NewPatientRegistration, doctor: Doctor
) -> PatientCreationResponse:
    """
    Создает пациента без привязки к существующему или новому пользователю.
    Patient_cor_id будет сгенерирован автоматически.
    """
    # user_id будет None, patient_cor_id_value будет сгенерирован внутри _create_patient_internal
    return await _create_patient_internal(
        db=db,
        patient_data=patient_data,
        doctor=doctor,
        user_id=None,
        patient_cor_id_value=None, # Будет сгенерирован внутри _create_patient_internal
        send_email=False # Нет пользователя, нет email для отправки
    )