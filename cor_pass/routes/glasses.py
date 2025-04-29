from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from cor_pass.database.db import get_db
from cor_pass.schemas import Cassette, CassetteCreate, Glass, Sample, SampleCreate
from cor_pass.repository import sample as sample_service
from cor_pass.repository import cassette as cassette_service
from cor_pass.repository import glass as glass_service
from typing import List

router = APIRouter(prefix="/glasses", tags=["Glass"])

@router.post("/cassettes/{cassettes_id}/glass", 
            #  response_model=Cassette
             )
async def create_glass_for_cassette(cassette_id: str, num_glasses: int = 1, db: AsyncSession = Depends(get_db)):
    return await glass_service.create_glass(db=db, cassette_id=cassette_id, num_glasses=num_glasses)


@router.get("/{glass_id}", response_model=Glass)
async def read_cassette(glass_id: str, db: AsyncSession = Depends(get_db)):
    db_glass = await glass_service.get_glass(db=db, glass_id=glass_id)
    if db_glass is None:
        raise HTTPException(status_code=404, detail="Glass not found")
    return db_glass


@router.delete("/{glass_id}", 
            #    response_model=Glass
               )
async def delete_glass(glass_id: str, db: AsyncSession = Depends(get_db)):
    db_glass = await glass_service.delete_glass(db, glass_id)
    if db_glass is None:
        raise HTTPException(status_code=404, detail="Glass not found")
    return db_glass