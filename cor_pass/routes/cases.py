from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from cor_pass.database.db import get_db
from cor_pass.schemas import Case, CaseCreate, Sample
from cor_pass.repository import case as case_service

router = APIRouter(prefix="/cases", tags=["Cases"])

@router.post("/", 
            #  response_model=Case
            )
async def create_case(case_in: CaseCreate, db: AsyncSession = Depends(get_db)):
    return await case_service.create_case_with_initial_data(db, case_in)

@router.get("/{case_id}", response_model=Case)
async def read_case(case_id: str, db: AsyncSession = Depends(get_db)):
    db_case = await case_service.get_case(db, case_id)
    print(db_case)
    if db_case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    #Преобразуем список db_models.Sample в список schemas.Sample
    samples_pydantic = [Sample.from_orm(sample) for sample in db_case.samples]

    # Создаем Pydantic-модель Case с преобразованными samples
    case_pydantic = Case.from_orm(db_case)
    case_pydantic.samples = samples_pydantic

    return case_pydantic



@router.delete("/{case_id}", 
            #    response_model=Case
               )
async def delete_case(case_id: str, db: AsyncSession = Depends(get_db)):
    db_case = await case_service.delete_case(db, case_id)
    if db_case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return db_case


@router.get("/api/patients/{patient_id}/overview/details")
async def read_patient_overview_details(patient_id: str, db: AsyncSession = Depends(get_db)):
    """
    Возвращает список всех кейсов пациента и детализацию первого из них:
    семплы, кассеты первого семпла и стекла этих кассет.
    """
    overview_data = await case_service.get_patient_first_case_details(db, patient_id)
    if overview_data is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return overview_data