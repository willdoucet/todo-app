import logging
from datetime import date
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from . import models, schemas

logger = logging.getLogger(__name__)


def _eager_load_options():
    """Standard eager loading for meal entries to prevent N+1 queries.

    Loads the unified Item (with both detail relationships), meal slot type,
    and participants. Use with `visible_meal_entries_stmt()` below.
    """
    return [
        selectinload(models.MealEntry.item).selectinload(models.Item.recipe_detail),
        selectinload(models.MealEntry.item).selectinload(models.Item.food_item_detail),
        selectinload(models.MealEntry.meal_slot_type),
        selectinload(models.MealEntry.participants),
    ]


def visible_meal_entries_stmt():
    """Canonical statement builder for non-hidden meal entries.

    Applies `soft_hidden_at IS NULL` so soft-hidden rows (from Expansion B
    cascade delete) drop out of all UI/CRUD reads. See Eng Review #3 Issue 6:
    never use `item.meal_entries` directly — that relationship loads soft-hidden
    rows too. Always go through this helper for UI reads.
    """
    return (
        select(models.MealEntry)
        .where(models.MealEntry.soft_hidden_at.is_(None))
        .options(*_eager_load_options())
    )


async def get_meal_entries(
    db: AsyncSession,
    start_date: date,
    end_date: date,
    family_member_id: int | None = None,
):
    """Get meal entries for a date range, with optional per-person filter."""
    stmt = (
        visible_meal_entries_stmt()
        .where(models.MealEntry.date >= start_date)
        .where(models.MealEntry.date <= end_date)
        .order_by(
            models.MealEntry.date,
            models.MealEntry.meal_slot_type_id,
            models.MealEntry.sort_order,
        )
    )

    if family_member_id is not None:
        # Filter to entries where this family member is a participant
        stmt = stmt.where(
            models.MealEntry.participants.any(
                models.FamilyMember.id == family_member_id
            )
        )

    result = await db.execute(stmt)
    return result.scalars().unique().all()


async def get_meal_entry(db: AsyncSession, entry_id: int):
    """Get a single meal entry by ID with all relationships loaded."""
    stmt = visible_meal_entries_stmt().where(models.MealEntry.id == entry_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _resolve_participant_ids(
    db: AsyncSession,
    participant_ids: list[int] | None,
    meal_slot_type_id: int,
) -> list[int]:
    """Resolve which family member IDs to assign to a meal entry.

    Participant Resolution Algorithm (3-level fallback):
    1. If explicit participant_ids provided → use those
    2. If None, check slot type default_participants → use those
    3. If slot type defaults are empty [] → assign ALL family members (= "everyone")
    """
    if participant_ids is not None:
        return participant_ids

    # Fall back to slot type defaults
    stmt = select(models.MealSlotType).where(models.MealSlotType.id == meal_slot_type_id)
    result = await db.execute(stmt)
    slot = result.scalar_one_or_none()

    if slot and slot.default_participants:
        return slot.default_participants

    # Empty defaults = "everyone"
    result = await db.execute(select(models.FamilyMember.id))
    return [row[0] for row in result.all()]


async def create_meal_entry(db: AsyncSession, entry: schemas.MealEntryCreate):
    """Create a new meal entry with participant materialization."""
    entry_data = entry.model_dump(exclude={"participant_ids"})
    db_entry = models.MealEntry(
        **entry_data,
        # Mark pending up-front so the meal entry and its sync state are committed
        # atomically. A second commit-after-commit pattern can leave the row with
        # NULL sync status if the second commit fails, permanently orphaning it
        # from the shopping list pipeline.
        shopping_sync_status="pending",
    )
    db.add(db_entry)
    await db.flush()  # Get the ID before inserting participants

    # Resolve and insert participants into junction table
    participant_ids = await _resolve_participant_ids(
        db, entry.participant_ids, entry.meal_slot_type_id
    )
    if participant_ids:
        for pid in participant_ids:
            await db.execute(
                models.meal_entry_participants.insert().values(
                    meal_entry_id=db_entry.id, family_member_id=pid
                )
            )

    await db.commit()

    # Dispatch shopping list sync AFTER the commit so the worker can find the row.
    try:
        from .tasks import sync_shopping_list_add
        sync_shopping_list_add.delay(db_entry.id)
        logger.info(f"Dispatched shopping sync for meal entry {db_entry.id}")
    except Exception as e:
        logger.warning(f"Failed to dispatch shopping sync: {e}")

    return await get_meal_entry(db, db_entry.id)


async def update_meal_entry(
    db: AsyncSession, entry_id: int, entry_update: schemas.MealEntryUpdate
):
    """Update an existing meal entry."""
    db_entry = await get_meal_entry(db, entry_id)
    if not db_entry:
        return None

    update_data = entry_update.model_dump(exclude_unset=True, exclude={"participant_ids"})

    # Apply scalar field updates via UPDATE statement (avoids lazy-load issues)
    if update_data:
        stmt = (
            update(models.MealEntry)
            .where(models.MealEntry.id == entry_id)
            .values(**update_data)
        )
        await db.execute(stmt)

    # Update participants if provided — replace all junction rows
    if entry_update.participant_ids is not None:
        # Delete existing participants
        await db.execute(
            delete(models.meal_entry_participants).where(
                models.meal_entry_participants.c.meal_entry_id == entry_id
            )
        )
        # Insert new participants
        slot_type_id = entry_update.meal_slot_type_id or db_entry.meal_slot_type_id
        participant_ids = await _resolve_participant_ids(
            db, entry_update.participant_ids, slot_type_id
        )
        for pid in participant_ids:
            await db.execute(
                models.meal_entry_participants.insert().values(
                    meal_entry_id=entry_id, family_member_id=pid
                )
            )

    await db.commit()
    # Expire cache so the participants relationship re-loads from DB
    db.expunge_all()
    return await get_meal_entry(db, entry_id)


async def delete_meal_entry(db: AsyncSession, entry_id: int):
    """Delete a meal entry, then dispatch shopping list cleanup."""
    entry = await get_meal_entry(db, entry_id)
    if not entry:
        return None

    # Capture the list id BEFORE deletion since the Celery task needs it to target
    # the right list (the entry row no longer exists by the time the task runs).
    synced_to_list_id = entry.synced_to_list_id

    # Commit the delete FIRST. If the commit fails, we must not have already told
    # Celery to clean up shopping items for an entry that still exists.
    await db.delete(entry)
    await db.commit()

    try:
        from .tasks import sync_shopping_list_remove
        sync_shopping_list_remove.delay(entry_id, synced_to_list_id)
        logger.info(f"Dispatched shopping removal for meal entry {entry_id} (list {synced_to_list_id})")
    except Exception as e:
        logger.warning(f"Failed to dispatch shopping removal: {e}")

    return entry
