from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from cor_pass.schemas import Case as CaseModelScheema, CaseBase as CaseBaseScheema, Sample as SampleModelScheema, Cassette as CassetteModelScheema, Glass as GlassModelScheema
from cor_pass.database import models as db_models
import uuid
from datetime import datetime
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import selectinload
from cor_pass.services.logger import logger
async def generate_case_code(db: AsyncSession) -> str:
    """Асинхронно генерирует уникальный код кейса."""
    now = datetime.now()
    return f"{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

async def create_case_with_initial_data(db: AsyncSession, case_in: CaseBaseScheema) -> CaseModelScheema:
    """Асинхронно создает новый кейс и связанные с ним начальные данные."""
    now = datetime.now()
    # print(case_in.grossing_status)
    db_case = db_models.Case(
        id=str(uuid.uuid4()),
        patient_id=case_in.patient_id,
        creation_date=now,
        bank_count=0,
        cassette_count=0,
        glass_count=0,
        # grossing_status=case_in.grossing_status
    )
    db_case.case_code = await generate_case_code(db)
    db.add(db_case)
    await db.commit()
    await db.refresh(db_case)

    # Автоматически создаем одну банку
    db_sample = db_models.Sample(case_id=db_case.id, sample_number="A")
    db_case.bank_count +=1
    db.add(db_sample)
    await db.commit()
    await db.refresh(db_sample)
    await db.refresh(db_case)

    # Автоматически создаем одну кассету
    db_cassette = db_models.Cassette(sample_id=db_sample.id, cassette_number=f"{db_sample.sample_number}1")
    db.add(db_cassette)
    db_case.cassette_count +=1
    db_sample.cassette_count +=1
    await db.commit()
    await db.refresh(db_cassette)
    await db.refresh(db_case)
    await db.refresh(db_sample)

    # Автоматически создаем одно стекло
    db_glass = db_models.Glass(cassette_id=db_cassette.id, glass_number=0, staining=db_models.StainingType.HE)
    db.add(db_glass)
    db_case.glass_count +=1
    db_sample.glass_count +=1
    await db.commit()
    await db.refresh(db_glass)
    await db.refresh(db_case)
    await db.refresh(db_sample)

    return db_case



async def get_case(db: AsyncSession, case_id: str) -> db_models.Case | None:
    """Асинхронно получает информацию о кейсе по его ID, включая связанные банки."""
    result = await db.execute(
        select(db_models.Case)
        .where(db_models.Case.id == case_id)
    )
    case_db = result.scalar_one_or_none()
    # 2. Получаем семплы первого кейса и связанные с ними кассеты и стекла
    samples_result = await db.execute(
        select(db_models.Sample)
        .where(db_models.Sample.case_id == case_db.id)
        .options(
            selectinload(db_models.Sample.cassette).selectinload(db_models.Cassette.glass)
        )
    )
    first_case_samples_db = samples_result.scalars().all()
    first_case_samples = []
    for sample_db in first_case_samples_db:
        sample = SampleModelScheema.model_validate(sample_db).model_dump()
        sample["cassettes"] = []
        for cassette_db in sample_db.cassette:
            cassette = CassetteModelScheema.model_validate(cassette_db).model_dump()
            cassette["glasses"] = [GlassModelScheema.model_validate(glass).model_dump() for glass in cassette_db.glass]
            sample["cassettes"].append(cassette)
        first_case_samples.append(sample)

    first_case_details = {
        "id": case_db.id,
        "case_code": case_db.case_code,
        "creation_date": case_db.creation_date,
        "samples": first_case_samples,
    }

    return {"case_details": first_case_details}


async def get_single_case(db: AsyncSession, case_id: str) -> db_models.Case | None:
    """Асинхронно получает информацию о кейсе по его ID, включая связанные банки."""
    result = await db.execute(
        select(db_models.Case)
        .where(db_models.Case.id == case_id)
    )
    return result.scalar_one_or_none()


async def delete_case(db: AsyncSession, case_id: str) -> db_models.Case | None:
    """Асинхронно удаляет кейс."""
    result = await db.execute(select(db_models.Case).where(db_models.Case.id == case_id))
    db_case = result.scalar_one_or_none()
    if db_case:
        await db.delete(db_case)
        await db.commit()
        return {"message": f"Кейс с ID {case_id} успешно удалён"}
    return None



async def get_patient_first_case_details(db: AsyncSession, patient_id: str) -> dict | None:
    """
    Асинхронно получает список всех кейсов пациента и детализацию первого из них:
    семплы, кассеты первого семпла и стекла этих кассет (оптимизированная загрузка).
    Использует model_validate вместо устаревшего from_orm.
    """
    # 1. Получаем список всех кейсов пациента
    cases_result = await db.execute(
        select(db_models.Case)
        .where(db_models.Case.patient_id == patient_id)
    )
    all_cases_db = cases_result.scalars().all()
    all_cases = all_cases_db

    first_case_details = None
    if all_cases_db:
        first_case_db = all_cases_db[0]

        # 2. Получаем семплы первого кейса и связанные с ними кассеты и стекла
        samples_result = await db.execute(
            select(db_models.Sample)
            .where(db_models.Sample.case_id == first_case_db.id)
            .options(
                selectinload(db_models.Sample.cassette).selectinload(db_models.Cassette.glass)
            )
        )
        first_case_samples_db = samples_result.scalars().all()
        first_case_samples = []
        for sample_db in first_case_samples_db:
            sample = SampleModelScheema.model_validate(sample_db).model_dump()
            sample["cassettes"] = []
            for cassette_db in sample_db.cassette:
                cassette = CassetteModelScheema.model_validate(cassette_db).model_dump()
                cassette["glasses"] = [GlassModelScheema.model_validate(glass).model_dump() for glass in cassette_db.glass]
                sample["cassettes"].append(cassette)
            first_case_samples.append(sample)

        first_case_details = {
            "id": first_case_db.id,
            "case_code": first_case_db.case_code,
            "creation_date": first_case_db.creation_date,
            "samples": first_case_samples,
        }

    return {"all_cases": all_cases, "first_case_details": first_case_details}