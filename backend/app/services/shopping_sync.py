"""Shopping list auto-sync service.

Aggregation bucket: (list_id, aggregation_source, aggregation_key_name, aggregation_unit)

Celery guard flow for ADD tasks:
  status != pending → no-op (already synced, or already cleaned up by swap/unlink)
  AppSettings.mealboard_shopping_list_id is NULL → set meal_entry to "skipped", no-op
  else → sync against current linked list; set status="synced", synced_to_list_id=<list>

REMOVE tasks use provenance (meal_entry.synced_to_list_id), NOT the current linked list.

Recipe ingredients with quantity=0 are treated as pantry staples
(aggregation_unit=NULL, name-only match). NOT falling back to 1.0.
"""
import json
import logging
import re

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.attributes import flag_modified

from .. import models
from ..constants.irregulars import IRREGULAR_PLURALS
from ..constants.units import (
    UNIT_TO_GROUP,
    to_base_unit,
    from_base_unit,
    format_ingredient_title,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Name canonicalization
# =============================================================================

def canonicalize_name(name: str) -> str:
    """Normalize an ingredient name for aggregation matching.

    Steps: lowercase, trim, collapse whitespace, singularize.
    No fuzzy matching, no synonyms.
    """
    if not name:
        return ""
    # Lowercase + trim + collapse whitespace
    result = re.sub(r"\s+", " ", name.strip().lower())

    # Check irregular plurals table first (exact match on full name)
    if result in IRREGULAR_PLURALS:
        return IRREGULAR_PLURALS[result]

    # Check if last word is an irregular plural
    words = result.split()
    if words and words[-1] in IRREGULAR_PLURALS:
        words[-1] = IRREGULAR_PLURALS[words[-1]]
        return " ".join(words)

    # Simple suffix-stripping singularization on last word
    if words:
        last = words[-1]
        if last.endswith("ies") and len(last) > 4:
            # berries → already handled by irregulars; but e.g. "bodies" → "body"
            words[-1] = last[:-3] + "y"
        elif last.endswith("ves") and len(last) > 4:
            # handled by irregulars, but catch others
            words[-1] = last[:-3] + "f"
        elif last.endswith("es") and len(last) > 3:
            # "peaches" → handled by irregulars
            # For remaining: "boxes" → "box", "dishes" → "dish"
            stem = last[:-2]
            if stem.endswith(("sh", "ch", "x", "z", "ss")):
                words[-1] = stem
            else:
                # "tomatoes" → handled by irregulars; "plates" → "plate"
                words[-1] = last[:-1]  # Just strip the 's'
        elif last.endswith("s") and not last.endswith("ss") and len(last) > 2:
            words[-1] = last[:-1]
        return " ".join(words)

    return result


# =============================================================================
# Internal helpers
# =============================================================================

async def _get_settings(db: AsyncSession) -> models.AppSettings:
    """Get app settings (singleton)."""
    from ..crud_app_settings import get_settings
    return await get_settings(db)


async def _upsert_shopping_item(
    db: AsyncSession,
    list_id: int,
    meal_entry_id: int,
    source_kind: str,
    source_id: int | None,
    display_name: str,
    quantity: float | None,
    unit: str | None,
    measurement_system: str,
):
    """Insert or update a shopping list task for an ingredient.

    Bucket: (list_id, 'mealboard_auto', canonical_name, aggregation_unit)

    Flow:
      input → canonicalize → bucket SELECT FOR UPDATE →
        existing → add qty + update title + append source_meals
        missing → INSERT, catch unique-violation → retry as UPDATE
    """
    if not display_name:
        return

    canonical = canonicalize_name(display_name)
    unit_group = UNIT_TO_GROUP.get(unit, "none") if unit else "none"

    # Determine aggregation_unit and base values
    if quantity is not None and quantity > 0 and unit is not None and unit_group in ("weight", "volume"):
        base_qty, base_unit = to_base_unit(quantity, unit)
        agg_unit = base_unit  # Use base unit (g/ml) for bucket to enable cross-unit aggregation
        agg_base_unit = base_unit
    elif quantity is not None and quantity > 0 and unit is not None and unit_group == "count":
        base_qty = quantity
        base_unit = unit
        agg_unit = unit  # Specific unit for bucket (ear ≠ bunch ≠ each)
        agg_base_unit = unit
    elif quantity is not None and quantity > 0 and unit is None:
        # Has quantity but no unit → default to "each"
        base_qty = quantity
        base_unit = "each"
        agg_unit = "each"
        agg_base_unit = "each"
        unit_group = "count"
    else:
        # Pantry staple: no quantity or quantity=0
        base_qty = 0
        base_unit = None
        agg_unit = None
        agg_base_unit = None
        unit_group = "none"

    source_entry = {
        "meal_entry_id": meal_entry_id,
        "source_kind": source_kind,
        "item_id": source_id,  # unified — was split into recipe_id/food_item_id pre-refactor
        "display_name": display_name,
        "ingredient_name": canonical,
        "quantity": base_qty,
        "unit": base_unit,
    }

    # SELECT FOR UPDATE existing task with same aggregation bucket
    if agg_unit is not None:
        # Standard case: match on source + key + unit
        stmt = (
            select(models.Task)
            .where(
                models.Task.list_id == list_id,
                models.Task.aggregation_source == "mealboard_auto",
                models.Task.aggregation_key_name == canonical,
                models.Task.aggregation_unit == agg_unit,
            )
            .with_for_update()
        )
    else:
        # Pantry staple: aggregation_unit is NULL — explicit lookup
        stmt = (
            select(models.Task)
            .where(
                models.Task.list_id == list_id,
                models.Task.aggregation_source == "mealboard_auto",
                models.Task.aggregation_key_name == canonical,
                models.Task.aggregation_unit.is_(None),
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
        title = _format_title(total_base_qty, agg_base_unit, unit_group, display_name, measurement_system)

        existing.title = title
        existing.source_meals = sources
        existing.aggregation_base_quantity = total_base_qty
        flag_modified(existing, "source_meals")
        await db.flush()
        logger.debug("Aggregated '%s' → '%s' (sources: %d)", canonical, title, len(sources))
    else:
        # Insert new task
        title = _format_title(base_qty, agg_base_unit, unit_group, display_name, measurement_system)

        fm_result = await db.execute(select(models.FamilyMember.id).limit(1))
        default_fm_id = fm_result.scalar_one_or_none() or 1

        new_task = models.Task(
            title=title,
            list_id=list_id,
            assigned_to=default_fm_id,
            completed=False,
            source_meals=[source_entry],
            aggregation_key_name=canonical,
            aggregation_unit_group=unit_group,
            aggregation_source="mealboard_auto",
            aggregation_unit=agg_unit,
            aggregation_base_unit=agg_base_unit,
            aggregation_base_quantity=base_qty,
        )
        db.add(new_task)
        try:
            await db.flush()
            logger.debug("Created shopping item '%s'", title)
        except IntegrityError:
            await db.rollback()
            logger.debug("Unique constraint hit for '%s' — retrying as update", canonical)
            await _upsert_shopping_item(
                db, list_id, meal_entry_id, source_kind, source_id,
                display_name, quantity, unit, measurement_system,
            )


def _format_title(
    total_base_qty: float,
    base_unit: str | None,
    unit_group: str,
    display_name: str,
    measurement_system: str,
) -> str:
    """Format a shopping item title from aggregation data."""
    if unit_group in ("weight", "volume") and base_unit:
        display_qty, display_unit = from_base_unit(total_base_qty, base_unit, measurement_system)
        return format_ingredient_title(display_qty, display_unit, display_name)
    elif unit_group == "count" and base_unit:
        return format_ingredient_title(round(total_base_qty), base_unit, display_name)
    else:
        return display_name


# =============================================================================
# Sync entry points
# =============================================================================

async def sync_meal_to_shopping_list(
    db: AsyncSession,
    meal_entry_id: int,
):
    """Sync a meal entry's ingredients/food item to the linked shopping list.

    Called by Celery task after meal entry creation.
    Guards: status must be "pending", linked list must exist.
    """
    # Lock the meal entry
    stmt = (
        select(models.MealEntry)
        .where(models.MealEntry.id == meal_entry_id)
        .with_for_update()
    )
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()

    if not entry:
        logger.warning("Meal entry %d not found — skipping sync", meal_entry_id)
        return

    # Guard: status must be "pending"
    if entry.shopping_sync_status != "pending":
        logger.info(
            "Meal entry %d status is '%s', not 'pending' — no-op",
            meal_entry_id, entry.shopping_sync_status,
        )
        return

    settings = await _get_settings(db)
    shopping_list_id = settings.mealboard_shopping_list_id

    if not shopping_list_id:
        logger.warning("No shopping list linked — marking meal entry %d as skipped", meal_entry_id)
        entry.shopping_sync_status = "skipped"
        entry.synced_to_list_id = None
        await db.commit()
        return

    # Verify the linked list still exists
    list_exists = await db.execute(
        select(models.List.id).where(models.List.id == shopping_list_id)
    )
    if not list_exists.scalar_one_or_none():
        logger.warning("Linked shopping list %d not found — marking skipped", shopping_list_id)
        entry.shopping_sync_status = "skipped"
        entry.synced_to_list_id = None
        await db.commit()
        return

    # Load the unified item + both detail relationships (selectinload avoids N+1).
    from sqlalchemy.orm import selectinload
    entry_stmt = (
        select(models.MealEntry)
        .options(
            selectinload(models.MealEntry.item).selectinload(models.Item.recipe_detail),
            selectinload(models.MealEntry.item).selectinload(models.Item.food_item_detail),
        )
        .where(models.MealEntry.id == meal_entry_id)
    )
    entry_result = await db.execute(entry_stmt)
    entry = entry_result.scalar_one_or_none()

    measurement_system = settings.measurement_system or "imperial"

    item = entry.item if entry else None
    if item and item.item_type == "recipe" and item.recipe_detail and item.recipe_detail.ingredients:
        for ingredient in item.recipe_detail.ingredients:
            await _upsert_shopping_item(
                db,
                list_id=shopping_list_id,
                meal_entry_id=meal_entry_id,
                source_kind="recipe_ingredient",
                source_id=item.id,
                display_name=ingredient.get("name", ""),
                quantity=ingredient.get("quantity"),
                unit=ingredient.get("unit"),
                measurement_system=measurement_system,
            )
    elif item and item.item_type == "food_item" and item.food_item_detail:
        fid = item.food_item_detail
        await _upsert_shopping_item(
            db,
            list_id=shopping_list_id,
            meal_entry_id=meal_entry_id,
            source_kind="food_item",
            source_id=item.id,
            display_name=item.name,
            quantity=float(fid.shopping_quantity) if fid.shopping_quantity is not None else None,
            unit=fid.shopping_unit,
            measurement_system=measurement_system,
        )

    # Mark sync complete
    entry.shopping_sync_status = "synced"
    entry.synced_to_list_id = shopping_list_id
    await db.commit()
    logger.info(
        "Shopping sync complete for meal entry %d → list %d",
        meal_entry_id, shopping_list_id,
    )


async def remove_meal_from_shopping_list(
    db: AsyncSession,
    meal_entry_id: int,
    target_list_id: int | None = None,
):
    """Remove a meal entry's contribution from the shopping list.

    Uses target_list_id (from meal_entry.synced_to_list_id) to scope removal.
    If target_list_id is None, no-op (meal was never synced or already cleaned up).

    Rules:
    - Checked (completed) tasks: leave alone (they flipped to manual via on_item_checked)
    - Unchecked mealboard_auto tasks: subtract this meal's contribution
    - If quantity reaches 0: delete the task
    """
    if target_list_id is None:
        logger.info("Meal entry %d has no synced_to_list_id — no-op", meal_entry_id)
        return

    settings = await _get_settings(db)
    measurement_system = settings.measurement_system or "imperial"

    # Find all mealboard_auto tasks on the target list
    stmt = (
        select(models.Task)
        .where(
            models.Task.list_id == target_list_id,
            models.Task.aggregation_source == "mealboard_auto",
            models.Task.source_meals.isnot(None),
            models.Task.completed == False,
        )
        .with_for_update()
    )
    result = await db.execute(stmt)
    tasks = result.scalars().all()

    for task in tasks:
        sources = task.source_meals or []
        matching = [s for s in sources if s.get("meal_entry_id") == meal_entry_id]
        if not matching:
            continue

        remaining = [s for s in sources if s.get("meal_entry_id") != meal_entry_id]

        if not remaining:
            await db.delete(task)
            logger.debug("Deleted shopping item '%s' (no remaining sources)", task.title)
        else:
            total_base_qty = sum(s.get("quantity", 0) for s in remaining)
            title = _format_title(
                total_base_qty,
                task.aggregation_base_unit,
                task.aggregation_unit_group,
                task.aggregation_key_name or task.title.lower(),
                measurement_system,
            )
            task.title = title
            task.source_meals = remaining
            task.aggregation_base_quantity = total_base_qty
            flag_modified(task, "source_meals")
            logger.debug("Updated shopping item → '%s' (sources: %d)", title, len(remaining))

    # Clear synced_to_list_id on the meal entry
    await db.execute(
        update(models.MealEntry)
        .where(models.MealEntry.id == meal_entry_id)
        .values(synced_to_list_id=None)
    )

    await db.commit()
    logger.info("Shopping removal complete for meal entry %d from list %d", meal_entry_id, target_list_id)


# =============================================================================
# Check / Swap / Unlink
# =============================================================================

async def on_item_checked(db: AsyncSession, task: models.Task):
    """When a mealboard_auto task is checked (completed=True), flip to manual.

    Retains all aggregation fields for provenance. Concurrent sync writes
    will see aggregation_source=NULL and create a fresh mealboard_auto row.
    """
    if task.aggregation_source != "mealboard_auto":
        return

    # Lock the row
    stmt = (
        select(models.Task)
        .where(models.Task.id == task.id)
        .with_for_update()
    )
    result = await db.execute(stmt)
    locked_task = result.scalar_one_or_none()
    if not locked_task:
        return

    old_source = locked_task.aggregation_source
    locked_task.aggregation_source = None
    await db.flush()
    logger.info(
        "on_item_checked: task %d '%s' flipped %s → NULL",
        task.id, task.aggregation_key_name, old_source,
    )


async def swap_mealboard_list(db: AsyncSession, old_list_id: int, new_list_id: int):
    """Move mealboard auto-items from old list to new list atomically.

    1. Update meal_entries synced_to_list_id from old → new
    2. Delete all mealboard_auto rows from old list
    3. Recompute fresh rows on new list from meal entries
    """
    logger.info("swap_mealboard_list: %d → %d", old_list_id, new_list_id)

    # 1. Rebucket meal entries
    await db.execute(
        update(models.MealEntry)
        .where(
            models.MealEntry.synced_to_list_id == old_list_id,
            models.MealEntry.shopping_sync_status == "synced",
        )
        .values(synced_to_list_id=new_list_id)
    )

    # 2. Delete all mealboard_auto rows from old list
    del_result = await db.execute(
        delete(models.Task)
        .where(
            models.Task.list_id == old_list_id,
            models.Task.aggregation_source == "mealboard_auto",
        )
    )
    rows_deleted = del_result.rowcount

    # 3. Recompute on new list from all synced meal entries
    await _recompute_shopping_list(db, new_list_id)

    logger.info(
        "swap_mealboard_list complete: deleted %d from old, recomputed on new",
        rows_deleted,
    )


async def unlink_mealboard_list(db: AsyncSession, list_id: int):
    """Unlink mealboard from shopping list.

    1. Delete all mealboard_auto rows from list
    2. Mark all meal entries with synced_to_list_id=list_id as skipped
    """
    logger.info("unlink_mealboard_list: %d", list_id)

    del_result = await db.execute(
        delete(models.Task)
        .where(
            models.Task.list_id == list_id,
            models.Task.aggregation_source == "mealboard_auto",
        )
    )
    rows_deleted = del_result.rowcount

    update_result = await db.execute(
        update(models.MealEntry)
        .where(models.MealEntry.synced_to_list_id == list_id)
        .values(synced_to_list_id=None, shopping_sync_status="skipped")
    )
    entries_skipped = update_result.rowcount

    logger.info(
        "unlink_mealboard_list complete: deleted %d rows, skipped %d entries",
        rows_deleted, entries_skipped,
    )


async def change_mealboard_list(db: AsyncSession, new_list_id: int | None):
    """Atomic list-link transition. Owns the full stateful workflow.

    Locks AppSettings, dispatches swap/unlink/link based on old→new transition,
    then updates the setting. All in one transaction.
    """
    from ..crud_app_settings import get_settings

    # Lock AppSettings row
    stmt = (
        select(models.AppSettings)
        .with_for_update()
    )
    result = await db.execute(stmt)
    settings = result.scalar_one_or_none()

    if not settings:
        # Create settings if missing (shouldn't happen)
        settings = models.AppSettings(timezone="UTC")
        db.add(settings)
        await db.flush()

    old_list_id = settings.mealboard_shopping_list_id

    if old_list_id == new_list_id:
        logger.info("change_mealboard_list: no-op (same list %s)", old_list_id)
        return

    if old_list_id is None and new_list_id is not None:
        # Link: no pre-existing rows to clean up; recompute if meal entries exist
        logger.info("change_mealboard_list: link to %d", new_list_id)
        settings.mealboard_shopping_list_id = new_list_id
        await db.flush()
        await _recompute_shopping_list(db, new_list_id)
    elif old_list_id is not None and new_list_id is None:
        # Unlink
        await unlink_mealboard_list(db, old_list_id)
        settings.mealboard_shopping_list_id = None
    elif old_list_id is not None and new_list_id is not None:
        # Swap
        await swap_mealboard_list(db, old_list_id, new_list_id)
        settings.mealboard_shopping_list_id = new_list_id

    await db.commit()
    logger.info(
        "change_mealboard_list complete: %s → %s",
        old_list_id, new_list_id,
    )


async def _recompute_shopping_list(db: AsyncSession, list_id: int):
    """Recompute all mealboard_auto shopping rows on a list from synced meal entries."""
    settings = await _get_settings(db)
    measurement_system = settings.measurement_system or "imperial"

    from sqlalchemy.orm import selectinload
    stmt = (
        select(models.MealEntry)
        .options(
            selectinload(models.MealEntry.item).selectinload(models.Item.recipe_detail),
            selectinload(models.MealEntry.item).selectinload(models.Item.food_item_detail),
        )
        .where(
            models.MealEntry.synced_to_list_id == list_id,
            models.MealEntry.shopping_sync_status == "synced",
        )
    )
    result = await db.execute(stmt)
    entries = result.scalars().all()

    for entry in entries:
        item = entry.item
        if item and item.item_type == "recipe" and item.recipe_detail and item.recipe_detail.ingredients:
            for ingredient in item.recipe_detail.ingredients:
                await _upsert_shopping_item(
                    db,
                    list_id=list_id,
                    meal_entry_id=entry.id,
                    source_kind="recipe_ingredient",
                    source_id=item.id,
                    display_name=ingredient.get("name", ""),
                    quantity=ingredient.get("quantity"),
                    unit=ingredient.get("unit"),
                    measurement_system=measurement_system,
                )
        elif item and item.item_type == "food_item" and item.food_item_detail:
            fid = item.food_item_detail
            await _upsert_shopping_item(
                db,
                list_id=list_id,
                meal_entry_id=entry.id,
                source_kind="food_item",
                source_id=item.id,
                display_name=item.name,
                quantity=float(fid.shopping_quantity) if fid.shopping_quantity is not None else None,
                unit=fid.shopping_unit,
                measurement_system=measurement_system,
            )
