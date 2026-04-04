"""Shopping list auto-sync service.

Handles ingredient aggregation when meals are added/removed from the planner.
Uses aggregation_key_name + aggregation_unit_group on Task model with a unique
constraint for concurrency safety.

Flow (on meal add):
  1. For each ingredient, normalize name + determine unit group
  2. SELECT FOR UPDATE existing task with same aggregation key
  3. If found: add quantities, update title, append to source_meals
  4. If not found: INSERT new task (catch unique violation → retry as UPDATE)

Flow (on meal remove):
  1. Find tasks whose source_meals JSON contains the deleted meal's ID
  2. For unchecked tasks: subtract contribution, update or delete
  3. Leave checked tasks alone (user already bought them)
"""
import logging
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from .. import models
from ..constants.units import (
    UNIT_TO_GROUP,
    to_base_unit,
    from_base_unit,
    format_ingredient_title,
)

logger = logging.getLogger(__name__)


async def _get_settings(db: AsyncSession) -> models.AppSettings:
    """Get app settings (singleton)."""
    from ..crud_app_settings import get_settings
    return await get_settings(db)


async def sync_meal_to_shopping_list(
    db: AsyncSession,
    meal_entry_id: int,
):
    """Sync a meal entry's ingredients/food item to the linked shopping list.

    Called by Celery task after meal entry creation.
    """
    settings = await _get_settings(db)
    shopping_list_id = settings.mealboard_shopping_list_id

    if not shopping_list_id:
        logger.info(f"No shopping list linked — skipping sync for meal entry {meal_entry_id}")
        return

    # Verify the linked list still exists
    list_exists = await db.execute(
        select(models.List.id).where(models.List.id == shopping_list_id)
    )
    if not list_exists.scalar_one_or_none():
        logger.warning(f"Linked shopping list {shopping_list_id} not found — unlinking")
        settings.mealboard_shopping_list_id = None
        await db.commit()
        return

    # Load the meal entry with recipe
    from sqlalchemy.orm import selectinload
    stmt = (
        select(models.MealEntry)
        .options(selectinload(models.MealEntry.recipe), selectinload(models.MealEntry.food_item))
        .where(models.MealEntry.id == meal_entry_id)
    )
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()

    if not entry:
        logger.warning(f"Meal entry {meal_entry_id} not found — skipping sync")
        return

    measurement_system = settings.measurement_system or "imperial"

    if entry.item_type == "recipe" and entry.recipe and entry.recipe.ingredients:
        # Sync recipe ingredients
        for ingredient in entry.recipe.ingredients:
            await _upsert_shopping_item(
                db,
                list_id=shopping_list_id,
                meal_entry_id=meal_entry_id,
                ingredient_name=ingredient.get("name", ""),
                quantity=ingredient.get("quantity"),
                unit=ingredient.get("unit"),
                measurement_system=measurement_system,
            )
    elif entry.item_type == "food_item" and entry.food_item:
        # Sync food item by name
        await _upsert_shopping_item(
            db,
            list_id=shopping_list_id,
            meal_entry_id=meal_entry_id,
            ingredient_name=entry.food_item.name,
            quantity=None,
            unit=None,
            measurement_system=measurement_system,
        )
    # Custom meals: NOT synced (no structured data)

    # Mark sync status
    await db.execute(
        update(models.MealEntry)
        .where(models.MealEntry.id == meal_entry_id)
        .values(shopping_sync_status="synced")
    )
    await db.commit()
    logger.info(f"Shopping sync complete for meal entry {meal_entry_id}")


async def _upsert_shopping_item(
    db: AsyncSession,
    list_id: int,
    meal_entry_id: int,
    ingredient_name: str,
    quantity: float | None,
    unit: str | None,
    measurement_system: str,
):
    """Insert or update a shopping list task for an ingredient.

    Uses aggregation_key_name + aggregation_unit_group for deduplication.
    SELECT FOR UPDATE on existing rows; catches unique violation on INSERT.
    """
    if not ingredient_name:
        return

    # Normalize
    key_name = ingredient_name.strip().lower()
    unit_group = UNIT_TO_GROUP.get(unit, "none") if unit else "none"

    # Convert to base unit for storage
    if quantity is not None and unit is not None and unit_group in ("weight", "volume"):
        base_qty, base_unit = to_base_unit(quantity, unit)
    else:
        base_qty = quantity or 1.0
        base_unit = unit  # count units or None

    source_entry = {"meal_entry_id": meal_entry_id, "quantity": base_qty, "base_unit": base_unit}

    # Try to find existing task with same aggregation key (SELECT FOR UPDATE)
    stmt = (
        select(models.Task)
        .where(
            models.Task.list_id == list_id,
            models.Task.aggregation_key_name == key_name,
            models.Task.aggregation_unit_group == unit_group,
        )
        .with_for_update()
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        # Aggregate: add quantity, update title, append source
        sources = existing.source_meals or []
        sources.append(source_entry)
        total_base_qty = sum(s.get("quantity", 0) for s in sources)

        # Format display title
        if unit_group in ("weight", "volume") and base_unit:
            display_qty, display_unit = from_base_unit(total_base_qty, base_unit, measurement_system)
            title = format_ingredient_title(display_qty, display_unit, ingredient_name)
        elif unit_group == "count" and unit:
            title = format_ingredient_title(round(total_base_qty), unit, ingredient_name)
        else:
            title = ingredient_name

        existing.title = title
        existing.source_meals = sources  # Triggers JSON update
        # Force SQLAlchemy to detect the JSON change
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(existing, "source_meals")
        await db.flush()
        logger.debug(f"Aggregated '{key_name}' → '{title}' (sources: {len(sources)})")
    else:
        # Insert new task
        if unit_group in ("weight", "volume") and base_unit:
            display_qty, display_unit = from_base_unit(base_qty, base_unit, measurement_system)
            title = format_ingredient_title(display_qty, display_unit, ingredient_name)
        elif unit_group == "count" and unit:
            title = format_ingredient_title(round(base_qty), unit, ingredient_name)
        else:
            title = ingredient_name

        # Need an assigned_to — get the first family member as a default
        fm_result = await db.execute(select(models.FamilyMember.id).limit(1))
        default_fm_id = fm_result.scalar_one_or_none() or 1

        new_task = models.Task(
            title=title,
            list_id=list_id,
            assigned_to=default_fm_id,
            completed=False,
            source_meals=[source_entry],
            aggregation_key_name=key_name,
            aggregation_unit_group=unit_group,
        )
        db.add(new_task)
        try:
            await db.flush()
            logger.debug(f"Created shopping item '{title}'")
        except IntegrityError:
            # Another worker beat us — retry as UPDATE
            await db.rollback()
            logger.debug(f"Unique constraint hit for '{key_name}' — retrying as update")
            await _upsert_shopping_item(
                db, list_id, meal_entry_id, ingredient_name,
                quantity, unit, measurement_system,
            )


async def remove_meal_from_shopping_list(
    db: AsyncSession,
    meal_entry_id: int,
):
    """Remove a meal entry's contribution from the shopping list.

    Called by Celery task before/after meal entry deletion.
    Rules:
    - Checked (completed) tasks: leave alone
    - Unchecked tasks: subtract this meal's contribution
    - If quantity reaches 0: delete the task
    """
    settings = await _get_settings(db)
    shopping_list_id = settings.mealboard_shopping_list_id

    if not shopping_list_id:
        return

    measurement_system = settings.measurement_system or "imperial"

    # Find all tasks on the shopping list that have this meal in source_meals
    # We need to scan all tasks with non-null source_meals on this list
    stmt = (
        select(models.Task)
        .where(
            models.Task.list_id == shopping_list_id,
            models.Task.source_meals.isnot(None),
            models.Task.completed == False,  # Only touch unchecked items
        )
        .with_for_update()
    )
    result = await db.execute(stmt)
    tasks = result.scalars().all()

    for task in tasks:
        sources = task.source_meals or []
        # Find entries from this meal
        matching = [s for s in sources if s.get("meal_entry_id") == meal_entry_id]
        if not matching:
            continue

        # Remove this meal's contributions
        remaining = [s for s in sources if s.get("meal_entry_id") != meal_entry_id]

        if not remaining:
            # No other sources — delete the task entirely
            await db.delete(task)
            logger.debug(f"Deleted shopping item '{task.title}' (no remaining sources)")
        else:
            # Recalculate quantity from remaining sources
            total_base_qty = sum(s.get("quantity", 0) for s in remaining)
            base_unit = remaining[0].get("base_unit") if remaining else None
            unit_group = task.aggregation_unit_group

            # Reformat title
            key_name = task.aggregation_key_name or task.title.lower()
            if unit_group in ("weight", "volume") and base_unit:
                display_qty, display_unit = from_base_unit(total_base_qty, base_unit, measurement_system)
                title = format_ingredient_title(display_qty, display_unit, key_name)
            elif unit_group == "count" and base_unit:
                title = format_ingredient_title(round(total_base_qty), base_unit, key_name)
            else:
                title = key_name

            task.title = title
            task.source_meals = remaining
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(task, "source_meals")
            logger.debug(f"Updated shopping item → '{title}' (sources: {len(remaining)})")

    await db.commit()
    logger.info(f"Shopping removal complete for meal entry {meal_entry_id}")
