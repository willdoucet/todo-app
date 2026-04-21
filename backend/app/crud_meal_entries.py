"""CRUD operations for meal_entries.

State-machine for the `soft_hidden_at` column (TWO writers, discriminated by `undo_token`)::

                    soft_hidden_at column has TWO writers
                    ─────────────────────────────────────
   parent item delete                    user clicks delete on a meal card
   (cascade-hide)                        (5s undo window)
          │                                          │
          ▼                                          ▼
   sets soft_hidden_at = now()           sets soft_hidden_at = now()
        undo_token = NULL                     undo_token = <uuid4>
          │                                          │
          └─────────────┬────────────────────────────┘
                        ▼
                  meal_entries row
                  (invisible to all reads via
                   visible_meal_entries_stmt)
                        │
              ┌─────────┴───────────┐
              ▼                     ▼
   undo_token IS NULL      undo_token IS NOT NULL
   (cascade-hidden)         (user-undo-hidden)
              │                     │
              ▼                     ▼
   sweeper purges when     sweeper purges after 15s
   parent.deleted_at is    grace; user can also flip
   set (any time)          back to live via POST
                           /meal-entries/{id}/undo
                           (atomic compare-and-swap on undo_token)

`_find_entry_for_undo` is the ONLY function that reads bypassing
`visible_meal_entries_stmt`. It MUST discriminate on `undo_token IS NOT NULL`
before letting the caller touch the row, otherwise the user-undo code path
could accidentally flip a cascade-hidden row back to live.
"""
import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from sqlalchemy import exists, or_, select, update, delete, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from . import models, schemas


def _token_fingerprint(token: str) -> str:
    """Stable 8-char log fingerprint. Hashing so we never leak bits of the
    bearer token itself into log storage."""
    return hashlib.sha256(token.encode()).hexdigest()[:8]

logger = logging.getLogger(__name__)

# Server-side accept window = client 5s + 1.5s slack for network/clock skew.
UNDO_WINDOW_SECONDS = 6.5


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
    start_date,
    end_date,
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
    """Get a single meal entry by ID with all relationships loaded.

    Applies `soft_hidden_at IS NULL`, so any caller that needs to touch a
    user-undo-hidden row must use `_find_entry_for_undo` instead.
    """
    stmt = visible_meal_entries_stmt().where(models.MealEntry.id == entry_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _find_entry_for_undo(db: AsyncSession, entry_id: int):
    """Look up a meal entry bypassing the `soft_hidden_at IS NULL` filter.

    This is the ONLY intentional exception to the `visible_meal_entries_stmt()`
    convention. It exists solely for the undo endpoint's pre-flight read,
    which must see the soft-hidden row to disambiguate 404 (never existed)
    from 410 (expired / parent-deleted / etc). The caller MUST still refuse to
    operate on rows where `undo_token IS NULL` — those are cascade-hidden rows
    owned by the parent-item lifecycle, not this flow.
    """
    stmt = (
        select(models.MealEntry)
        .where(models.MealEntry.id == entry_id)
        .options(*_eager_load_options())
    )
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
    """Update an existing meal entry.

    `get_meal_entry` applies the `soft_hidden_at IS NULL` filter, so a PATCH on
    a soft-hidden entry naturally returns 404 — no extra guard needed.
    """
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
    """Soft-delete a meal entry and return the undo token + expiry.

    The row is not physically deleted — it's set to `soft_hidden_at = now()`
    with a fresh `undo_token`, making it invisible to every read path that
    goes through `visible_meal_entries_stmt()`. The hourly sweeper hard-deletes
    soft-hidden user-undo rows once they're past the 15-second grace window.

    Shopping-list groceries leave the list immediately (per CEO review 1.1):
    undo restores them by re-dispatching `sync_shopping_list_add`.

    Returns a dict with the fresh MealEntry row + undo metadata, or None if the
    entry didn't exist (or was already soft-hidden — mirrors "someone else
    deleted it" concurrent semantics per CEO review 4.2).
    """
    entry = await get_meal_entry(db, entry_id)
    if not entry:
        return None

    # Capture the list id BEFORE the soft-delete commit since the Celery task
    # needs it to target the right list.
    synced_to_list_id = entry.synced_to_list_id

    undo_token = secrets.token_hex(16)  # 32-char hex fits our VARCHAR(64)
    now = datetime.utcnow()

    await db.execute(
        update(models.MealEntry)
        .where(models.MealEntry.id == entry_id)
        .values(soft_hidden_at=now, undo_token=undo_token)
    )
    await db.commit()
    logger.info(
        "soft_delete meal_entry_id=%s token_fp=%s",
        entry_id, _token_fingerprint(undo_token),
    )

    # Dispatch shopping-list cleanup AFTER the commit, but delay it past the
    # undo window. If the user undoes within 5s (server CAS cutoff: 6.5s), the
    # subsequent `sync_shopping_list_add` dispatch can land on the Celery queue
    # first or second — Celery doesn't guarantee cross-worker ordering, so
    # remove-after-add can leave the shopping list missing the undone meal's
    # groceries. Delaying remove past UNDO_WINDOW_SECONDS makes the remove task
    # re-read state at execution time (see tasks.sync_shopping_list_remove) and
    # no-op when the entry was undone back to live.
    try:
        from .tasks import sync_shopping_list_remove
        sync_shopping_list_remove.apply_async(
            args=[entry_id, synced_to_list_id],
            countdown=int(UNDO_WINDOW_SECONDS) + 1,
        )
        logger.info(
            "Scheduled shopping removal for meal entry %s (list %s) in %ds",
            entry_id, synced_to_list_id, int(UNDO_WINDOW_SECONDS) + 1,
        )
    except Exception as e:
        logger.warning("Failed to dispatch shopping removal: %s", e)

    # Re-fetch the hidden row via the undo helper so the response payload has
    # the updated soft_hidden_at + undo_token + eager-loaded relationships.
    refreshed = await _find_entry_for_undo(db, entry_id)
    return {
        "entry": refreshed,
        "undo_token": undo_token,
        "expires_at": now + timedelta(seconds=UNDO_WINDOW_SECONDS),
    }


class UndoFailedError(Exception):
    """Raised by undo_delete_meal_entry when the row cannot be restored.

    `reason` is one of: not_found | token_mismatch | expired | parent_deleted.
    The route translates this into 404 (not_found) or 410 (everything else).
    """

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


async def undo_delete_meal_entry(db: AsyncSession, entry_id: int, token: str):
    """Atomically flip a soft-hidden user-undo row back to live.

    The atomic compare-and-swap (`UPDATE … WHERE id=? AND undo_token=? AND
    soft_hidden_at > now() - 6.5s RETURNING *`) is the linchpin: with two
    concurrent undo requests (phone + laptop, or rapid double-click escaping
    the UI guard), Postgres picks exactly one winner. The loser returns 0
    rows, we surface 410, and `sync_shopping_list_add` fires exactly once —
    no duplicated groceries on the shopping list.

    Pre-flight read is informational only: it distinguishes 404 (row never
    existed or is not a user-undo row) from 410 (parent item deleted during
    the window) so the response body has a useful `reason`. It does NOT
    decide whether to flip the row — only the CAS does.
    """
    # Step 1: pre-flight — learn why we'd fail before attempting the CAS.
    existing = await _find_entry_for_undo(db, entry_id)
    if existing is None:
        logger.info("undo_failed meal_entry_id=%s reason=not_found", entry_id)
        raise UndoFailedError("not_found")
    # Capture these now — the UPDATE below flushes the session and may refresh
    # existing's scalar columns to the post-update values, blanking them.
    pre_undo_token = existing.undo_token
    pre_soft_hidden_at = existing.soft_hidden_at
    pre_item_deleted_at = existing.item.deleted_at if existing.item is not None else None

    # Refuse rows that aren't user-undo rows. Cascade-hidden rows (undo_token
    # IS NULL) are owned by the parent-item delete lifecycle, not this flow.
    if pre_undo_token is None:
        logger.info("undo_failed meal_entry_id=%s reason=not_found", entry_id)
        raise UndoFailedError("not_found")
    # Parent-deleted precedence (premise 6): if the parent item is itself
    # soft-deleted, the user-undo row is orphaned — do not restore.
    if pre_item_deleted_at is not None:
        logger.info("undo_failed meal_entry_id=%s reason=parent_deleted", entry_id)
        raise UndoFailedError("parent_deleted")

    # Step 2: atomic CAS — single statement decides the winner under concurrency.
    # The predicate includes `Item.deleted_at IS NULL` so a concurrent parent
    # soft-delete that lands between the pre-flight read and this UPDATE cannot
    # leave us with a live entry pointing at a tombstoned item (which would
    # trip the hourly sweeper's assertion gate). Custom meals (item_id IS NULL)
    # have no parent to check, so they pass the OR branch unconditionally.
    cutoff = datetime.utcnow() - timedelta(seconds=UNDO_WINDOW_SECONDS)
    parent_live = exists().where(
        models.Item.id == models.MealEntry.item_id,
        models.Item.deleted_at.is_(None),
    )
    result = await db.execute(
        update(models.MealEntry)
        .where(models.MealEntry.id == entry_id)
        .where(models.MealEntry.undo_token == token)
        .where(models.MealEntry.soft_hidden_at > cutoff)
        .where(or_(models.MealEntry.item_id.is_(None), parent_live))
        .values(soft_hidden_at=None, undo_token=None)
        .returning(models.MealEntry.id)
    )
    flipped = result.scalar_one_or_none()
    if flipped is None:
        # Could be token_mismatch, expired, parent-deleted mid-window, or a
        # concurrent-undo race loser. Narrow using the values we captured
        # before the flush; for the parent-deleted case we re-read the item
        # (a concurrent parent soft-delete may have landed after our pre-flight).
        if pre_undo_token != token:
            reason = "token_mismatch"
        elif pre_soft_hidden_at and pre_soft_hidden_at <= cutoff:
            reason = "expired"
        else:
            fresh = await _find_entry_for_undo(db, entry_id)
            if (
                fresh is not None
                and fresh.item is not None
                and fresh.item.deleted_at is not None
            ):
                reason = "parent_deleted"
            else:
                # Pre-flight saw valid state + parent live, but the CAS lost
                # without parent-delete explaining it — another undo winner.
                reason = "token_mismatch"
        logger.info("undo_failed meal_entry_id=%s reason=%s", entry_id, reason)
        await db.rollback()
        raise UndoFailedError(reason)

    await db.commit()
    elapsed = (datetime.utcnow() - pre_soft_hidden_at).total_seconds()
    logger.info("undo_success meal_entry_id=%s within_s=%.2f", entry_id, elapsed)

    # Step 3: re-dispatch shopping sync. Mirror delete_meal_entry's Kombu
    # graceful-failure path so a broker outage can't block the user-visible
    # restore.
    try:
        from .tasks import sync_shopping_list_add
        sync_shopping_list_add.delay(entry_id)
    except Exception as e:
        logger.warning("undo_sync_add_failed meal_entry_id=%s err=%s", entry_id, e)

    return await get_meal_entry(db, entry_id)
