"""Legacy meal plans CRUD — delegates to meal entries.

This module exists for backward compatibility while the frontend transitions
from /meal-plans to /meal-entries. It will be removed after the frontend migration.
"""
from datetime import date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from . import models


async def get_meal_plans(db: AsyncSession, start_date: date, end_date: date):
    """Get meal entries for a date range (legacy compatibility)."""
    stmt = (
        select(models.MealEntry)
        .options(
            selectinload(models.MealEntry.recipe),
            selectinload(models.MealEntry.meal_slot_type),
        )
        .where(models.MealEntry.date >= start_date)
        .where(models.MealEntry.date <= end_date)
        .order_by(models.MealEntry.date, models.MealEntry.meal_slot_type_id)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_meal_plan(db: AsyncSession, meal_plan_id: int):
    """Get a single meal entry by ID (legacy compatibility)."""
    stmt = (
        select(models.MealEntry)
        .options(
            selectinload(models.MealEntry.recipe),
            selectinload(models.MealEntry.meal_slot_type),
        )
        .where(models.MealEntry.id == meal_plan_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
