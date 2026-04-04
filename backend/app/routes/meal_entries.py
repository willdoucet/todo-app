from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from .. import schemas, crud_meal_entries
from ..database import get_db

router = APIRouter(
    prefix="/meal-entries",
    tags=["meal-entries"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=List[schemas.MealEntry])
async def get_meal_entries(
    start_date: date,
    end_date: date,
    family_member_id: Optional[int] = Query(None, description="Filter by family member participant"),
    db: AsyncSession = Depends(get_db),
):
    """Get meal entries for a date range with optional per-person filter."""
    return await crud_meal_entries.get_meal_entries(
        db, start_date=start_date, end_date=end_date, family_member_id=family_member_id
    )


@router.get("/{entry_id}", response_model=schemas.MealEntry)
async def get_meal_entry(entry_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single meal entry by ID."""
    entry = await crud_meal_entries.get_meal_entry(db, entry_id=entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Meal entry not found")
    return entry


@router.post("/", response_model=schemas.MealEntry, status_code=status.HTTP_201_CREATED)
async def create_meal_entry(
    entry: schemas.MealEntryCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new meal entry.

    Participants are eagerly materialized:
    - If participant_ids provided → those family members
    - If not provided → slot type defaults, or all family members if no defaults
    """
    return await crud_meal_entries.create_meal_entry(db=db, entry=entry)


@router.patch("/{entry_id}", response_model=schemas.MealEntry)
async def update_meal_entry(
    entry_id: int,
    entry_update: schemas.MealEntryUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a meal entry (change slot, mark cooked, update participants, etc.)."""
    updated = await crud_meal_entries.update_meal_entry(db, entry_id, entry_update)
    if updated is None:
        raise HTTPException(status_code=404, detail="Meal entry not found")
    return updated


@router.delete("/{entry_id}", response_model=schemas.MealEntry)
async def delete_meal_entry(entry_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a meal entry."""
    deleted = await crud_meal_entries.delete_meal_entry(db, entry_id)
    if deleted is None:
        raise HTTPException(status_code=404, detail="Meal entry not found")
    return deleted
