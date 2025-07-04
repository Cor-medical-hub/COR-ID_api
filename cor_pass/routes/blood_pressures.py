from datetime import datetime
import uuid
from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional

from cor_pass.repository import records as repository_record
from cor_pass.database.db import get_db
from cor_pass.repository.blood_pressure import create_measurement, get_measurements
from cor_pass.schemas import (
    BloodPressureMeasurementCreate,
    BloodPressureMeasurementResponse,
    BloodPressureMeasures,
    CreateRecordModel,
    NewBloodPressureMeasurementResponse,
    RecordResponse,
    TonometrIncomingData,
    UpdateRecordModel,
    MainscreenRecordResponse,
)
from cor_pass.database.models import User
from cor_pass.config.config import settings
from cor_pass.services.auth import auth_service
from cor_pass.services.logger import logger
from cor_pass.services.access import user_access

from cor_pass.services.cipher import decrypt_data, decrypt_user_key
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/measurements/blood_pressure", tags=["Blood Pressure Measurements"])

@router.post(
    "/",
    response_model=BloodPressureMeasurementResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(user_access)],
    summary="Добавить новое измерение артериального давления"
)
async def create_bp_measurement(
    body: BloodPressureMeasurementCreate,
    current_user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Добавляет новое измерение артериального давления и пульса для текущего пользователя.
    """
    new_measurement = await create_measurement(db=db, body=body, user=current_user)
    response = BloodPressureMeasurementResponse(
        systolic_pressure=new_measurement.systolic_pressure,
        diastolic_pressure=new_measurement.diastolic_pressure,
        pulse=new_measurement.pulse,
        measured_at=new_measurement.measured_at,
        id=new_measurement.id,
        user_id= new_measurement.user_id,
        created_at= new_measurement.created_at
    )
    return response




@router.get(
    "/",
    response_model=List[BloodPressureMeasurementResponse],
    dependencies=[Depends(user_access)],
    summary="Получить все измерения артериального давления текущего пользователя"
)
async def get_pb_measurements(
    current_user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Возвращает список всех измерений артериального давления и пульса для текущего пользователя.
    """
    measurements = await get_measurements(db=db, user=current_user)
    return measurements



@router.post(
    "/record",
    response_model=NewBloodPressureMeasurementResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(auth_service.get_current_user)],
    summary="Принять данные измерения давления от тонометра в старом формате"
)
async def receive_tonometer_data(
    incoming_data: TonometrIncomingData,
    current_user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Принимает и обрабатывает данные артериального давления и пульса от тонометра
    в специфическом формате устройства, объединяя их в одну запись.
    """
    systolic_pressure_val: Optional[int] = None
    diastolic_pressure_val: Optional[int] = None
    pulse_val: Optional[int] = None

    # Перебираем results, а не result (исправлено в TonometrIncomingData)
    for result_item in incoming_data.results:
        # Проверяем, что measures является объектом BloodPressureMeasures
        if isinstance(result_item.measures, BloodPressureMeasures):
            if result_item.measures.systolic and result_item.measures.systolic.value is not None:
                systolic_pressure_val = result_item.measures.systolic.value
            if result_item.measures.diastolic and result_item.measures.diastolic.value is not None:
                diastolic_pressure_val = result_item.measures.diastolic.value
            if result_item.measures.pulse and result_item.measures.pulse.value is not None:
                pulse_val = result_item.measures.pulse.value
        elif isinstance(result_item.measures, str):
            try:
                # Если measures может быть строкой для пульса
                pulse_val = int(result_item.measures)
            except ValueError:
                logger.debug(f"Не удалось преобразовать пульс '{result_item.measures}' в число")
        else:
            logger.debug(f"Неизвестный или неподдерживаемый формат measures: {type(result_item.measures)}")


    if systolic_pressure_val is None and diastolic_pressure_val is None and pulse_val is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Входящие данные не содержат валидных измерений давления или пульса."
        )

    try:
        measurement_data = BloodPressureMeasurementCreate(
            systolic_pressure=systolic_pressure_val,
            diastolic_pressure=diastolic_pressure_val,
            pulse=pulse_val,
            measured_at=incoming_data.createdDateTime # Используем createdDateTime из TonometrIncomingData
        )

        new_measurement = await create_measurement(db=db, body=measurement_data, user=current_user)
        return NewBloodPressureMeasurementResponse(
            id=new_measurement.id,
            systolic_pressure=new_measurement.systolic_pressure,
            diastolic_pressure=new_measurement.diastolic_pressure,
            pulse=new_measurement.pulse,
            measured_at=new_measurement.measured_at,
            user_id=new_measurement.user_id,
            created_at=new_measurement.created_at
        )

    except Exception as e:
        import traceback
        logger.error(f"Ошибка при сохранении объединенного измерения: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Не удалось сохранить объединенное измерение: {e}")