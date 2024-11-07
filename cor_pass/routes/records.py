from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List

from cor_pass.repository import records as repository_record
from cor_pass.database.db import get_db
from cor_pass.schemas import CreateRecordModel, RecordResponse, UpdateRecordModel, MainscreenRecordResponse
from cor_pass.database.models import User
from cor_pass.config.config import settings
from cor_pass.services.auth import auth_service
from cor_pass.services.logger import logger
from cor_pass.services.access import user_access

from cor_pass.services.cipher import encrypt_data, decrypt_data, decrypt_user_key
import datetime
router = APIRouter(prefix="/records", tags=["Records"])
encryption_key = settings.encryption_key


@router.get(
    "/all", response_model=List[MainscreenRecordResponse], dependencies=[Depends(user_access)]
)
async def read_records(
    skip: int = 0,
    limit: int = 150,
    user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
):
    """
    **Get a list of records. / Получение всех записей пользователя** \n

    :param skip: The number of records to skip (for pagination). Default is 0.
    :type skip: int
    :param limit: The maximum number of records to retrieve. Default is 50.
    :type limit: int
    :param db: The database session. Dependency on get_db.
    :type db: Session, optional
    :return: A list of RecordModel objects representing the records.
    :rtype: List[RecordModel]
    """
    try:
        records = await repository_record.get_all_user_records(db, user.id, skip, limit)
    except Exception as e:
        logger.error(f"Database query failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    decrypted_records = []
    for record in records:
        decrypted_username = await decrypt_data(
            encrypted_data=record.username,
            key=await decrypt_user_key(user.unique_cipher_key),
        )
        # decrypted_password = await decrypt_data(
        #     encrypted_data=record.password,
        #     key=await decrypt_user_key(user.unique_cipher_key),
        # )
        record_response = MainscreenRecordResponse(
            record_id=record.record_id,
            record_name=record.record_name,
            website=record.website,
            username=decrypted_username,
            password=record.password,
            is_favorite=record.is_favorite
        )
        decrypted_records.append(record_response)
    return decrypted_records


@router.get(
    "/{record_id}", response_model=RecordResponse, dependencies=[Depends(user_access)]
)
async def read_record(
    record_id: int,
    user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
):
    """
    **Get a specific record by ID. / Получение данных одной конкретной записи пользователя** \n

    :param record_id: The ID of the record.
    :type record_id: int
    :param db: The database session. Dependency on get_db.
    :type db: Session, optional
    :return: The RecordModel object representing the record.
    :rtype: RecordModel
    :raises HTTPException 404: If the record with the specified ID does not exist.
    """
    record = await repository_record.get_record_by_id(user, db, record_id)
    if record is None:
        logger.exception("Record not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Record not found"
        )
    return record


@router.post(
    "/create",
    response_model=RecordResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(user_access)],
)
async def create_record(
    body: CreateRecordModel,
    user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
):
    """
    **Create a new record. / Создание записи** \n

    :param body: The request body containing the record data.
    :type body: CreateRecordModel
    :param db: The database session. Dependency on get_db.
    :type db: Session, optional
    :return: The created ResponseRecord object representing the new record.
    :rtype: ResponseRecord
    """
    if user.account_status.value == "basic":
        records = await repository_record.get_all_user_records(db, user.id, 0, 50)
        if len(records) < settings.basic_account_records:
            record = await repository_record.create_record(body, db, user)
            return record
        else:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="User is not premium",
            )

    else:
        record = await repository_record.create_record(body, db, user)
        return record


"""
Маршрут обновления записи
"""


@router.put(
    "/{record_id}", response_model=RecordResponse, dependencies=[Depends(user_access)]
)
async def update_record(
    record_id: int,
    body: UpdateRecordModel,
    db: Session = Depends(get_db),
    user: User = Depends(auth_service.get_current_user),
):
    """
    **Update an existing record. / Обновление данных записи** \n

    :param record_id: The ID of the record to update.
    :type record_id: int
    :param body: The request body containing the updated record data.
    :type body: CreateRecordModel
    :param db: The database session. Dependency on get_db.
    :type db: Session, optional
    :return: The updated ResponseRecord object representing the updated record.
    :rtype: ResponseRecord
    :raises HTTPException 404: If the record with the specified ID does not exist.
    """
    record = await repository_record.update_record(record_id, body, user, db)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Record not found"
        )
    return record

@router.put(
    "/make_favorite/{record_id}", response_model=RecordResponse, dependencies=[Depends(user_access)]
)
async def make_favorite(
    record_id: int,
    is_favorite: bool,
    db: Session = Depends(get_db),
    user: User = Depends(auth_service.get_current_user),
):
    """
    **Make favorite an existing record. / Отметить запись как избранную** \n

    :param record_id: The ID of the record to update.
    :type record_id: int
    :param is_favorite: bool value.
    :type is_favorite: bool
    :param db: The database session. Dependency on get_db.
    :type db: Session, optional
    :return: The updated ResponseRecord object representing the updated record.
    :rtype: ResponseRecord
    :raises HTTPException 404: If the record with the specified ID does not exist.
    """
    record = await repository_record.make_favorite(record_id, is_favorite, user, db)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Record not found"
        )
    return record


@router.delete("/{record_id}", response_model=RecordResponse)
async def remove_record(
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(auth_service.get_current_user),
):
    """
    **Remove a record. / Удаление записи** \n

    :param record_id: The ID of the record to remove.
    :type record_id: int
    :param db: The database session. Dependency on get_db.
    :type db: Session, optional
    :return: The removed RecordModel object representing the removed record.
    :rtype: RecordModel
    :raises HTTPException 404: If the record with the specified ID does not exist.
    """
    record = await repository_record.delete_record(user, db, record_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Record not found"
        )
    return record
