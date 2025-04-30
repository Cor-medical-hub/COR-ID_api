from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from cor_pass.database.db import get_db
from cor_pass.schemas import Case, CaseCreate, Sample
from cor_pass.database import models as db_models
from cor_pass.repository import case as case_service

router = APIRouter(prefix="/cases", tags=["Cases"])

@router.post("/", 
            #  response_model=Case
            )
async def create_case(case_in: CaseCreate, db: AsyncSession = Depends(get_db), 
                    num_cases: int = 1,
                    urgency: db_models.UrgencyType = Query(db_models.UrgencyType.S, description="Срочность"),
                    material_type: db_models.MaterialType = Query(db_models.MaterialType.R, description="Тип исследования"),):
    return await case_service.create_cases_with_initial_data(db=db, case_in=case_in, num_cases=num_cases, urgency=urgency, material_type=material_type)

@router.get("/{case_id}", 
            # response_model=Case
            )
async def read_case(case_id: str, db: AsyncSession = Depends(get_db)):
    db_case = await case_service.get_case(db, case_id)
    if db_case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return db_case


@router.get("/{case_id}/case_parameters", 
            # response_model=Case
            )
async def read_case_parameters(case_id: str, db: AsyncSession = Depends(get_db)):
    db_case_parameters = await case_service.get_case_parameters(db, case_id)
    if db_case_parameters is None:
        raise HTTPException(status_code=404, detail="Case parameters not found")
    return db_case_parameters



@router.patch("/{case_id}/case_parameters", 
            # response_model=Case
            )
async def update_case_parameters(case_id: str,  
                                macro_description: str,
                                container_count_actual: int,
                                urgency: db_models.UrgencyType = db_models.UrgencyType.S,
                                material_type: db_models.MaterialType = db_models.MaterialType.R,
                                macro_archive: db_models.MacroArchive = db_models.MacroArchive.ESS,
                                decalcification: db_models.DecalcificationType = db_models.DecalcificationType.ABSENT,
                                sample_type: db_models.SampleType = db_models.SampleType.NATIVE,
                                fixation: db_models.FixationType = db_models.FixationType.NBF_10,
                                db: AsyncSession = Depends(get_db),):
    db_case_parameters = await case_service.update_case_parameters(db, case_id, macro_description, container_count_actual, urgency, material_type, macro_archive, decalcification, sample_type, fixation)
    if db_case_parameters is None:
        raise HTTPException(status_code=404, detail="Case parameters not found")
    return db_case_parameters


@router.delete("/{case_id}", 
            #    response_model=Case
               )
async def delete_case(case_id: str, db: AsyncSession = Depends(get_db)):
    db_case = await case_service.delete_case(db, case_id)
    if db_case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return db_case


@router.get("/patients/{patient_id}/overview")
async def read_patient_overview_details(patient_id: str, db: AsyncSession = Depends(get_db)):
    """
    Возвращает список всех кейсов пациента и детализацию первого из них:
    семплы, кассеты первого семпла и стекла этих кассет.
    """
    overview_data = await case_service.get_patient_first_case_details(db, patient_id)
    if overview_data is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return overview_data