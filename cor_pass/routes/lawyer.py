from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from cor_pass.database.db import get_db
from cor_pass.services.auth import auth_service
from cor_pass.database.models import User, Status
from cor_pass.services.access import admin_access, lawyer_access
from cor_pass.schemas import UserDb, DoctorsResponseSchema
from cor_pass.repository import person
from cor_pass.repository import lawyer
from pydantic import EmailStr
from cor_pass.database.redis_db import redis_client


from cor_pass.services.logger import logger

router = APIRouter(prefix="/lawyer", tags=["Lawyer"])


@router.get(
    "/get_all", response_model=list[UserDb], dependencies=[Depends(lawyer_access)]
)
async def get_all_doctors(
    skip: int = 0,
    limit: int = 10,
    user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db),
):
    """
    **Get a list of users. / Получение списка всех пользователей**\n
    This route allows to get a list of pagination-aware users.
    Level of Access:
    - Current authorized user
    :param skip: int: Number of users to skip.
    :param limit: int: Maximum number of users to return.
    :param current_user: User: Current authenticated user.
    :param db: Session: Database session.
    :return: List of users with their last activity.
    :rtype: List[UserDb]
    """

    list_doctors = await lawyer.get_doctors(skip, limit, db)

    users_list_with_activity = []
    for doctor in list_doctors:
        oid = doctor.doctor_id
        doctor_response = DoctorsResponseSchema(
            id=doctor.id,
            cor_id=doctor.doctor_id,
            first_name=doctor.first_name,
            surname=doctor.surname,
            last_name=doctor.last_name,
            account_status=doctor.status,
            scientific_degree=doctor.scientific_degree,
            date_of_last_attestation=doctor.date_of_last_attestation,
            
        )

        users_list_with_activity.append(doctor_response)

    return users_list_with_activity


@router.patch("/asign_status/{account_status}", dependencies=[Depends(admin_access)])
async def assign_status(
    email: EmailStr, account_status: Status, db: Session = Depends(get_db)
):
    """
    **Assign a account_status to a user by email. / Применение нового статуса аккаунта пользователя**\n

    This route allows to assign the selected account_status to a user by their email.

    :param email: EmailStr: Email of the user to whom you want to assign the status.

    :param account_status: Status: The selected account_status for the assignment (Premium, Basic).

    :param db: Session: Database Session.

    :return: Message about successful status change.

    :rtype: dict
    """
    user = await person.get_user_by_email(email, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if account_status == user.account_status:
        return {"message": "The acount status has already been assigned"}
    else:
        await person.make_user_status(email, account_status, db)
        return {"message": f"{email} - {account_status.value}"}



@router.patch("/activate/{email}", dependencies=[Depends(admin_access)])
async def activate_user(email: EmailStr, db: Session = Depends(get_db)):
    """
    **Activate user by email. / Активация аккаунта пользователя**\n

    This route allows to assign the selected account_status to a user by their email.

    :param email: EmailStr: Email of the user to whom you want to assign the status.

    :param account_status: Status: The selected account_status for the assignment (Premium, Basic).

    :param db: Session: Database Session.

    :return: Message about successful status change.

    :rtype: dict
    """
    user = await person.get_user_by_email(email, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if user.is_active:
        return {"message": f"The {user.email} account is already active"}
    else:
        await person.activate_user(email, db)
        return {"message": f"{user.email} - account is activated"}


