"""Legacy /meal-plans routes — kept for frontend backward compatibility.

The frontend still uses /meal-plans endpoints. These routes delegate to
the MealEntry model (the meal_plans table was renamed to meal_entries).
Will be removed when the frontend migrates to /meal-entries.
"""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from .. import crud_meal_plans
from ..database import get_db

router = APIRouter(
    prefix="/meal-plans",
    tags=["meal-plans (legacy)"],
    responses={404: {"description": "Not found"}},
)


@router.get("/")
async def get_meal_plans(
    start_date: date,
    end_date: date,
    db: AsyncSession = Depends(get_db),
):
    """Get meal entries for a date range (legacy /meal-plans endpoint)."""
    return await crud_meal_plans.get_meal_plans(db, start_date=start_date, end_date=end_date)


@router.get("/{meal_plan_id}")
async def get_meal_plan(meal_plan_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single meal entry by ID (legacy /meal-plans endpoint)."""
    entry = await crud_meal_plans.get_meal_plan(db, meal_plan_id=meal_plan_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Meal plan not found")
    return entry
