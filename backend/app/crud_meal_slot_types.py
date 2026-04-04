from sqlalchemy import select, update, exists
from sqlalchemy.ext.asyncio import AsyncSession
from . import models, schemas


async def get_meal_slot_types(db: AsyncSession, include_inactive: bool = True):
    """Get all meal slot types, ordered by sort_order."""
    stmt = select(models.MealSlotType).order_by(models.MealSlotType.sort_order)
    if not include_inactive:
        stmt = stmt.where(models.MealSlotType.is_active == True)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_meal_slot_type(db: AsyncSession, slot_type_id: int):
    """Get a single meal slot type by ID."""
    stmt = select(models.MealSlotType).where(models.MealSlotType.id == slot_type_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_meal_slot_type(db: AsyncSession, slot_type: schemas.MealSlotTypeCreate):
    """Create a new meal slot type."""
    db_slot = models.MealSlotType(
        **slot_type.model_dump(),
        is_default=False,  # User-created slots are never defaults
    )
    db.add(db_slot)
    await db.commit()
    await db.refresh(db_slot)
    return db_slot


async def update_meal_slot_type(
    db: AsyncSession, slot_type_id: int, slot_type: schemas.MealSlotTypeUpdate
):
    """Update an existing meal slot type."""
    data = slot_type.model_dump(exclude_unset=True)
    if not data:
        return await get_meal_slot_type(db, slot_type_id)
    stmt = (
        update(models.MealSlotType)
        .where(models.MealSlotType.id == slot_type_id)
        .values(**data)
    )
    result = await db.execute(stmt)
    if result.rowcount == 0:
        return None
    await db.commit()
    return await get_meal_slot_type(db, slot_type_id)


async def delete_meal_slot_type(db: AsyncSession, slot_type_id: int):
    """Delete a meal slot type.

    Soft-delete (set is_active=false) if the slot has meal entries.
    Hard-delete if the slot has no entries.
    Returns the slot type (soft-deleted or before hard-delete), or None if not found.
    """
    slot = await get_meal_slot_type(db, slot_type_id)
    if not slot:
        return None

    # Check if any meal entries reference this slot type
    has_entries_stmt = select(
        exists().where(models.MealEntry.meal_slot_type_id == slot_type_id)
    )
    result = await db.execute(has_entries_stmt)
    has_entries = result.scalar()

    if has_entries:
        # Soft-delete: set is_active=false
        stmt = (
            update(models.MealSlotType)
            .where(models.MealSlotType.id == slot_type_id)
            .values(is_active=False)
        )
        await db.execute(stmt)
        await db.commit()
        return await get_meal_slot_type(db, slot_type_id)
    else:
        # Hard-delete: no entries reference it
        await db.delete(slot)
        await db.commit()
        return slot


async def reset_to_defaults(db: AsyncSession):
    """Reset meal slot types to defaults (Breakfast, Lunch, Dinner, Snack).

    Deletes all user-created slots that have no meal entries.
    Soft-deletes user-created slots that have entries.
    Re-activates and restores default slots.
    """
    # Re-activate all default slots
    stmt = (
        update(models.MealSlotType)
        .where(models.MealSlotType.is_default == True)
        .values(is_active=True)
    )
    await db.execute(stmt)

    # Get all non-default slots
    non_defaults_stmt = select(models.MealSlotType).where(
        models.MealSlotType.is_default == False
    )
    result = await db.execute(non_defaults_stmt)
    non_defaults = result.scalars().all()

    for slot in non_defaults:
        # Check if it has entries
        has_entries_stmt = select(
            exists().where(models.MealEntry.meal_slot_type_id == slot.id)
        )
        result = await db.execute(has_entries_stmt)
        has_entries = result.scalar()

        if has_entries:
            slot.is_active = False  # Soft-delete
        else:
            await db.delete(slot)  # Hard-delete

    await db.commit()
    return await get_meal_slot_types(db)
