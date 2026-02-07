from datetime import date
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from . import models, schemas


async def get_meal_plans(db: AsyncSession, start_date: date, end_date: date):
    """Get meal plans for a date range."""
    stmt = (
        select(models.MealPlan)
        .options(selectinload(models.MealPlan.recipe))
        .where(models.MealPlan.date >= start_date)
        .where(models.MealPlan.date <= end_date)
        .order_by(models.MealPlan.date, models.MealPlan.category)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_meal_plan(db: AsyncSession, meal_plan_id: int):
    """Get a single meal plan by ID."""
    stmt = (
        select(models.MealPlan)
        .options(selectinload(models.MealPlan.recipe))
        .where(models.MealPlan.id == meal_plan_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_meal_plan(db: AsyncSession, meal_plan: schemas.MealPlanCreate):
    """Create a new meal plan entry."""
    db_meal_plan = models.MealPlan(**meal_plan.model_dump())
    db.add(db_meal_plan)
    await db.commit()
    return await get_meal_plan(db, db_meal_plan.id)


async def update_meal_plan(
    db: AsyncSession, meal_plan_id: int, meal_plan: schemas.MealPlanUpdate
):
    """Update an existing meal plan."""
    stmt = (
        update(models.MealPlan)
        .where(models.MealPlan.id == meal_plan_id)
        .values(**meal_plan.model_dump(exclude_unset=True))
    )
    result = await db.execute(stmt)
    if result.rowcount == 0:
        return None
    await db.commit()
    return await get_meal_plan(db, meal_plan_id)


async def delete_meal_plan(db: AsyncSession, meal_plan_id: int):
    """Delete a meal plan entry."""
    meal_plan = await get_meal_plan(db, meal_plan_id)
    if meal_plan:
        await db.delete(meal_plan)
        await db.commit()
    return meal_plan
