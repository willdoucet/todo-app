from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from .. import schemas, crud_meal_slot_types
from ..database import get_db

router = APIRouter(
    prefix="/meal-slot-types",
    tags=["meal-slot-types"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=List[schemas.MealSlotType])
async def get_meal_slot_types(db: AsyncSession = Depends(get_db)):
    """Get all meal slot types (active + inactive), ordered by sort_order."""
    return await crud_meal_slot_types.get_meal_slot_types(db)


@router.post("/", response_model=schemas.MealSlotType, status_code=status.HTTP_201_CREATED)
async def create_meal_slot_type(
    slot_type: schemas.MealSlotTypeCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new custom meal slot type."""
    return await crud_meal_slot_types.create_meal_slot_type(db, slot_type)


@router.patch("/{slot_type_id}", response_model=schemas.MealSlotType)
async def update_meal_slot_type(
    slot_type_id: int,
    slot_type_update: schemas.MealSlotTypeUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a meal slot type (rename, recolor, reorder, toggle active)."""
    updated = await crud_meal_slot_types.update_meal_slot_type(db, slot_type_id, slot_type_update)
    if updated is None:
        raise HTTPException(status_code=404, detail="Meal slot type not found")
    return updated


@router.delete("/{slot_type_id}", response_model=schemas.MealSlotType)
async def delete_meal_slot_type(
    slot_type_id: int, db: AsyncSession = Depends(get_db)
):
    """Delete a meal slot type.

    Soft-deletes (sets is_active=false) if the slot has meal entries.
    Hard-deletes if the slot has no entries.
    """
    deleted = await crud_meal_slot_types.delete_meal_slot_type(db, slot_type_id)
    if deleted is None:
        raise HTTPException(status_code=404, detail="Meal slot type not found")
    return deleted


@router.post("/reset", response_model=List[schemas.MealSlotType])
async def reset_meal_slot_types(db: AsyncSession = Depends(get_db)):
    """Reset meal slot types to defaults (Breakfast, Lunch, Dinner, Snack).

    Re-activates default slots. Removes user-created slots without entries.
    Soft-deletes user-created slots that have entries.
    """
    return await crud_meal_slot_types.reset_to_defaults(db)
