from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from .. import schemas, crud_meal_plans
from ..database import get_db

router = APIRouter(
    prefix="/meal-plans",
    tags=["meal-plans"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=List[schemas.MealPlan])
async def get_meal_plans(
    start_date: date,
    end_date: date,
    db: AsyncSession = Depends(get_db),
):
    """Get meal plans for a date range. Required: start_date, end_date."""
    meal_plans = await crud_meal_plans.get_meal_plans(
        db, start_date=start_date, end_date=end_date
    )
    return meal_plans


@router.get("/{meal_plan_id}", response_model=schemas.MealPlan)
async def get_meal_plan(meal_plan_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single meal plan by ID."""
    meal_plan = await crud_meal_plans.get_meal_plan(db, meal_plan_id=meal_plan_id)
    if meal_plan is None:
        raise HTTPException(status_code=404, detail="Meal plan not found")
    return meal_plan


@router.post("/", response_model=schemas.MealPlan, status_code=status.HTTP_201_CREATED)
async def create_meal_plan(
    meal_plan: schemas.MealPlanCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new meal plan entry."""
    return await crud_meal_plans.create_meal_plan(db=db, meal_plan=meal_plan)


@router.patch("/{meal_plan_id}", response_model=schemas.MealPlan)
async def update_meal_plan(
    meal_plan_id: int,
    meal_plan_update: schemas.MealPlanUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a meal plan (e.g., mark as cooked, add notes)."""
    updated_meal_plan = await crud_meal_plans.update_meal_plan(
        db, meal_plan_id, meal_plan_update
    )
    if updated_meal_plan is None:
        raise HTTPException(status_code=404, detail="Meal plan not found")
    return updated_meal_plan


@router.delete("/{meal_plan_id}", response_model=schemas.MealPlan)
async def delete_meal_plan(meal_plan_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a meal plan entry."""
    deleted_meal_plan = await crud_meal_plans.delete_meal_plan(db, meal_plan_id)
    if deleted_meal_plan is None:
        raise HTTPException(status_code=404, detail="Meal plan not found")
    return deleted_meal_plan
