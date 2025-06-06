from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Query,
    UploadFile,
    status,
)

from sqlalchemy.exc import IntegrityError
from typing import List, Optional

from cor_pass.database.db import get_db
from cor_pass.database.models import PatientStatus, User
from cor_pass.repository.doctor import (
    create_doctor,
    create_doctor_service,
    get_doctor_patients_with_status,
    get_doctor_single_patient_with_status,
    upload_certificate_service,
    upload_diploma_service,
    upload_doctor_photo_service,
    upload_reserv_data_service,
)
from cor_pass.repository.lawyer import get_doctor
from cor_pass.repository.patient import add_existing_patient, register_new_patient
from cor_pass.schemas import (
    DoctorCreate,
    DoctorCreateResponse,
    ExistingPatientAdd,
    MicrodescriptionResponse,
    NewPatientRegistration,
    PathohistologicalConclusionResponse,
    PatientCasesWithReferralsResponse,
    PatientDecryptedResponce,
    PatientGlassPageResponse,
    ReferralAttachmentResponse,
    ReferralResponse,
    ReferralResponseForDoctor,
    SingleCaseGlassPageResponse,
    UpdateMicrodescription,
    UpdatePathohistologicalConclusion
)
from cor_pass.routes.cases import router as cases_router
from cor_pass.repository import case as case_service
from cor_pass.repository import person as repository_person
from cor_pass.services.auth import auth_service
from cor_pass.services.access import user_access, doctor_access
from cor_pass.services.auth import auth_service
from cor_pass.services.document_validation import validate_document_file
from cor_pass.services.image_validation import validate_image_file
import logging
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/doctor", tags=["Doctor"])


@router.post(
    "/signup",
    response_model=DoctorCreateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(user_access)],
)
async def signup_doctor(
    doctor_data: DoctorCreate = Body(...),
    current_user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    **Создание врача со всеми связанными данными**\n
    Этот маршрут позволяет создать врача вместе с дипломами, сертификатами и привязками к клиникам.
    Уровень доступа:
    - Текущий авторизованный пользователь
    :param doctor_data: str: Данные для создания врача в формате JSON.
    :param db: AsyncSession: Сессия базы данных.
    :return: Созданный врач.
    :rtype: DoctorResponse
    """

    exist_doctor = await get_doctor(db=db, doctor_id=current_user.cor_id)
    if exist_doctor:
        logger.debug(f"{current_user.cor_id} doctor already exist")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Doctor account already exists"
        )

    try:
        doctor = await create_doctor(
            doctor_data=doctor_data,
            db=db,
            user=current_user,
        )
        cer, dip, clin = await create_doctor_service(
            doctor_data=doctor_data, db=db, doctor=doctor
        )
    except IntegrityError as e:
        logger.error(f"Database integrity error: {e}")
        await db.rollback()
        detail = "Database error occurred. Please check the data for duplicates or invalid entries."
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during doctor creation.",
        )
    # Сериализуем ответ
    doctor_response = DoctorCreateResponse(
        id=doctor.id,
        doctor_cor_id=doctor.doctor_id,
        work_email=doctor.work_email,
        phone_number=doctor.phone_number,
        first_name=doctor.first_name,
        surname=doctor.surname,
        last_name=doctor.last_name,
        scientific_degree=doctor.scientific_degree,
        date_of_last_attestation=doctor.date_of_last_attestation,
        status=doctor.status,
        diploma_id=dip,
        certificates_id=cer,
        clinic_affiliations_id=clin,
        place_of_registration=doctor.place_of_registration,
        passport_code=doctor.passport_code,
        taxpayer_identification_number=doctor.taxpayer_identification_number,
    )

    return doctor_response


@router.post("/doctors/{doctor_cor_id}/photo", dependencies=[Depends(user_access)])
async def upload_doctor_photo(
    doctor_cor_id: str,
    file: UploadFile = Depends(validate_image_file),
    db: AsyncSession = Depends(get_db),
):
    return await upload_doctor_photo_service(doctor_cor_id, file, db)


@router.post("/doctors/{doctor_cor_id}/reserv", dependencies=[Depends(user_access)])
async def upload_doctor_reserv_data(
    doctor_cor_id: str,
    file: UploadFile = Depends(validate_document_file),
    db: AsyncSession = Depends(get_db),
):
    return await upload_reserv_data_service(doctor_cor_id, file, db)


@router.post("/diploma/{diploma_id}", dependencies=[Depends(user_access)])
async def upload_diploma(
    document_id: str,
    file: UploadFile = Depends(validate_document_file),
    db: AsyncSession = Depends(get_db),
):
    return await upload_diploma_service(document_id, file, db)


@router.post("/certificate/{certificate_id}", dependencies=[Depends(user_access)])
async def upload_certificate(
    document_id: str,
    file: UploadFile = Depends(validate_document_file),
    db: AsyncSession = Depends(get_db),
):
    return await upload_certificate_service(document_id, file, db)


@router.get(
    "/patients",
    dependencies=[Depends(doctor_access)],
    # response_model=PatientResponce
)
async def get_doctor_patients(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user),
    patient_status: Optional[str] = Query(None),  # Принимаем статус как строку
    sex: Optional[List[str]] = Query(None),
    sort_by: Optional[str] = Query("change_date"),
    sort_order: Optional[str] = Query("desc"),
    skip: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
):
    doctor = await get_doctor(db=db, doctor_id=current_user.cor_id)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found"
        )

    status_filters = None
    if patient_status:
        try:
            status_filters = [PatientStatus(patient_status)]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status value: {status}. Allowed values are: {[e.value for e in PatientStatus]}",
            )

    patients_with_status, total_count = await get_doctor_patients_with_status(
        db=db,
        doctor=doctor,
        status_filters=status_filters,
        sex_filters=sex,
        sort_by=sort_by,
        sort_order=sort_order,
        skip=skip,
        limit=limit,
    )
    return {"items": patients_with_status, "total": total_count}


@router.get(
    "/patients/{patient_cor_id}",
    dependencies=[Depends(doctor_access)],
    response_model=PatientDecryptedResponce
)
async def get_single_patient(
    patient_cor_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user),
):
    doctor = await get_doctor(db=db, doctor_id=current_user.cor_id)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found"
        )
    
    patient = await get_doctor_single_patient_with_status(db=db, patient_cor_id=patient_cor_id, doctor=doctor)

    return patient


@router.post(
    "/patients/register-new",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(doctor_access)],
)
async def add_new_patient_to_doctor(
    body: NewPatientRegistration,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user),
):
    """
    Добавить нового пациента к врачу.
    """
    doctor = await get_doctor(current_user.cor_id, db)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found"
        )

    if current_user.cor_id != doctor.doctor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to add patients to this doctor",
        )

    if body:
        new_patient_info = body
        exist_user = await repository_person.get_user_by_email(
            new_patient_info.email, db
        )
        if exist_user:
            logger.debug(f"{new_patient_info.email} user already exists")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Account already exists"
            )
        new_patient = await register_new_patient(db, new_patient_info, doctor)
        return {
            "message": f"Новый пациент {new_patient_info.first_name} {new_patient_info.surname} успешно зарегистрирован и добавлен к врачу."
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректные данные для добавления пациента.",
        )


@router.post("/patients/add-existing", dependencies=[Depends(doctor_access)])
async def add_existing_patient_to_doctor(
    patient_data: ExistingPatientAdd,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user),
):
    """
    Добавить существующего пациента к врачу.
    """
    doctor = await get_doctor(doctor_id=current_user.cor_id, db=db)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found"
        )

    existing_patient = await add_existing_patient(
        db=db, doctor=doctor, cor_id=patient_data.cor_id
    )
    if not existing_patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found"
        )

    return existing_patient



@router.get(
    "/patients/{patient_id}/glass-details",
    response_model=PatientGlassPageResponse,
    dependencies=[Depends(doctor_access)],
    status_code=status.HTTP_200_OK,
    summary="Получение кейсов и стёкол для страницы 'Стёкла'",
    tags=["DoctorPage"]
)
async def get_patient_glass_page_data(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    
) -> PatientGlassPageResponse:
    """
    Возвращает список всех кейсов пациента и все стёкла первого кейса
    """
    
    glass_page_data = await case_service.get_patient_case_details_for_glass_page(db=db, patient_id=patient_id)
        
    return glass_page_data


@router.get(
    "/cases/{case_id}/glass-details",
    response_model=SingleCaseGlassPageResponse,
    dependencies=[Depends(doctor_access)],
    status_code=status.HTTP_200_OK,
    summary="Cтёкла конкретного кейса для страницы 'Стёкла'",
    tags=["DoctorPage"]
)
async def get_single_case_details_for_glass_page(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    
) -> SingleCaseGlassPageResponse:
    """
    Возвращает стёкла конкретного кейса
    """
    
    glass_page_data = await case_service.get_single_case_details_for_glass_page(db=db, case_id=case_id)
        
    return glass_page_data




@router.get(
    "/patients/{patient_cor_id}/referral_page",
    response_model=PatientCasesWithReferralsResponse,
    dependencies=[Depends(doctor_access)],
    status_code=status.HTTP_200_OK,
    summary="Получение кейсов и вывод файлов направления по первому кейсу",
    tags=["DoctorPage"]
)
async def get_patient_cases_for_doctor(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
) -> PatientCasesWithReferralsResponse:
    """
    Возвращает список всех кейсов конкретного пациента, а также детали первого кейса, включая ссылку на файлы его направлений
    """
    patient_cases_data = await case_service.get_patient_cases_with_directions(db=db, patient_id=patient_id)
    if not patient_cases_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Кейси пацієнта або направлення не знайдено."
        )
        
    return patient_cases_data


@router.get("/patients/referrals/{case_id}", response_model=ReferralResponseForDoctor, 
            dependencies=[Depends(doctor_access)],
            status_code=status.HTTP_200_OK,
            summary="Вывод файлов направления по id кейса для доктора",
            tags=["DoctorPage"])
async def get_single_referral(
    case_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Возвращает ссылки на прикрепленные файлы направлений конкретного кейса.
    """
    referral = await case_service.get_referral_by_case(db=db, case_id=case_id)
    if not referral:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Referral not found")

    # Генерируем URL для каждого прикрепленного файла
    attachments_response = [
        ReferralAttachmentResponse(
            id=att.id,
            filename=att.filename,
            content_type=att.content_type,
            file_url=cases_router.url_path_for("get_referral_attachment", attachment_id=att.id)
        ) for att in referral.attachments
    ]

    referral_response_obj = ReferralResponseForDoctor.model_validate(referral)

    referral_response_obj.attachments = attachments_response

    return referral_response_obj



@router.put(
    "/pathohistological_conclusion/{case_id}",
    response_model=PathohistologicalConclusionResponse,
    dependencies=[Depends(doctor_access)],
    status_code=status.HTTP_200_OK,
    summary="Обновляет патогистологическое заключение кейса",
    tags=["DoctorPage"]
)
async def update_pathohistological_conclusion(
    case_id: str,
    body: UpdatePathohistologicalConclusion,
    db: AsyncSession = Depends(get_db),
):
    """
    Обновляет патогистологическое заключение кейса

    """
    db_case = await case_service.update_case_pathohistological_conclusion(
        db=db, case_id=case_id, body=body
    )
    if db_case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Case not found"
        )
    return db_case


@router.put(
    "/microdescription/{case_id}",
    response_model=MicrodescriptionResponse,
    dependencies=[Depends(doctor_access)],
    status_code=status.HTTP_200_OK,
    summary="Обновляет микроописание кейса",
    tags=["DoctorPage"]
)
async def update_microdescription(
    case_id: str,
    body: UpdateMicrodescription,
    db: AsyncSession = Depends(get_db),
):
    """
    Обновляет микроописание кейса

    """
    db_case = await case_service.update_case_microdescription(
        db=db, case_id=case_id, body=body
    )
    if db_case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Case not found"
        )
    return db_case