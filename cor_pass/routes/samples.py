from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from cor_pass.database.db import get_db
from cor_pass.schemas import Sample, SampleCreate
from cor_pass.repository import sample as sample_service
from typing import List

router = APIRouter(prefix="/samples", tags=["Samples"])

@router.post("/cases/{case_id}/samples", response_model=Sample)
async def create_sample_for_case(case_id: str, sample_in: SampleCreate, db: AsyncSession = Depends(get_db)):
    return await sample_service.create_sample(db, case_id, sample_in)


@router.get("/{sample_id}", response_model=Sample)
async def read_sample(sample_id: str, db: AsyncSession = Depends(get_db)):
    db_sample = await sample_service.get_sample(db, sample_id)
    if db_sample is None:
        raise HTTPException(status_code=404, detail="Sample not found")
    return db_sample


@router.delete("/{sample_id}", 
            #    response_model=Sample
               )
async def delete_sample(sample_id: str, db: AsyncSession = Depends(get_db)):
    db_sample = await sample_service.delete_sample(db, sample_id)
    if db_sample is None:
        raise HTTPException(status_code=404, detail="Sample not found")
    return db_sample

