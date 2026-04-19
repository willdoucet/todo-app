"""Canonical CRUD for the unified Item model.

Replaces `crud_recipes.py` and `crud_food_items.py` after the item-model refactor.

Query-builder convention: all list/detail/search reads build off `active_items_stmt()`
which enforces `deleted_at IS NULL` and eager-loads both detail relationships via
`selectinload` to avoid N+1 on list queries (adversarial review #3 + #7).

See plan §0.3 for the full API contract.
"""
import asyncio
import os
from datetime import datetime, timedelta
import secrets
from decimal import Decimal

import redis.asyncio as redis
from sqlalchemy import func, select, update, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from . import models, schemas


HARD_DELETE_SOAK_HOURS = 24
USER_UNDO_GRACE_SECONDS = 15


async def hard_delete_expired_soft_deletes_async(db: AsyncSession) -> dict:
    """Sweep expired soft-deleted items AND user-undo meal_entries past grace.

    Two sweeps, one pass:

    1. Items past HARD_DELETE_SOAK_HOURS (24h) — the cascade-in-code sweep:
       delete soft-hidden meal_entries referencing them, assertion-gate on
       stragglers, then delete the items. See Eng Review #3 Issue 3.
    2. Meal_entries with `undo_token IS NOT NULL` and `soft_hidden_at` older
       than USER_UNDO_GRACE_SECONDS (15s) — user-initiated soft-deletes whose
       undo window is closed. Parent items are still alive; only the entry
       rows need hard-deletion. 5s client window + 10s network/clock slack.

    Returns dict(items_deleted, user_undo_entries_deleted).
    """
    items_cutoff = datetime.utcnow() - timedelta(hours=HARD_DELETE_SOAK_HOURS)

    expired_res = await db.execute(
        select(models.Item.id).where(
            models.Item.deleted_at.is_not(None),
            models.Item.deleted_at < items_cutoff,
        )
    )
    expired_ids = [row[0] for row in expired_res.all()]
    items_deleted = 0

    if expired_ids:
        # Step 2a: delete soft-hidden meal_entries that reference expired items
        await db.execute(
            delete(models.MealEntry).where(
                models.MealEntry.item_id.in_(expired_ids),
                models.MealEntry.soft_hidden_at.is_not(None),
            )
        )
        await db.flush()

        # Step 2b: assertion gate — any remaining meal_entries means a bug
        remaining_res = await db.execute(
            select(func.count(models.MealEntry.id)).where(
                models.MealEntry.item_id.in_(expired_ids),
            )
        )
        remaining = remaining_res.scalar() or 0
        if remaining > 0:
            await db.rollback()
            raise RuntimeError(
                f"Hard-delete aborted: {remaining} active meal_entries still "
                f"reference {len(expired_ids)} expired items. Soft-delete "
                f"propagation bug — investigate before the next sweep run."
            )

        # Step 3: now delete the items (FK RESTRICT is satisfied)
        await db.execute(delete(models.Item).where(models.Item.id.in_(expired_ids)))
        items_deleted = len(expired_ids)

    # Second pass: hard-delete user-undo rows past the 15-second grace window.
    # Parent items are still alive; only the orphan entries need purging.
    undo_cutoff = datetime.utcnow() - timedelta(seconds=USER_UNDO_GRACE_SECONDS)
    undo_del = await db.execute(
        delete(models.MealEntry).where(
            models.MealEntry.undo_token.is_not(None),
            models.MealEntry.soft_hidden_at.is_not(None),
            models.MealEntry.soft_hidden_at < undo_cutoff,
        )
    )
    user_undo_entries_deleted = undo_del.rowcount or 0

    await db.commit()
    return {
        "items_deleted": items_deleted,
        "user_undo_entries_deleted": user_undo_entries_deleted,
    }


async def _attach_usage_counts(db: AsyncSession, items: list[models.Item]) -> None:
    """Populate `item.meal_entry_count` on each passed Item in place.

    Single GROUP BY over meal_entries, filtered to non-hidden rows only (matches
    the `visible_meal_entries_stmt()` invariant in crud_meal_entries — we don't
    count soft-hidden rows since they're already associated with a soft-deleted
    item in the cascade path). Household scale is cheap; for larger data this
    would want a correlated subquery at SELECT time instead.
    """
    if not items:
        return
    ids = [it.id for it in items]
    result = await db.execute(
        select(models.MealEntry.item_id, func.count(models.MealEntry.id))
        .where(models.MealEntry.soft_hidden_at.is_(None))
        .where(models.MealEntry.item_id.in_(ids))
        .group_by(models.MealEntry.item_id)
    )
    counts = dict(result.all())
    for it in items:
        it.meal_entry_count = counts.get(it.id, 0)


# ---------------------------------------------------------------------------
# Query builders
# ---------------------------------------------------------------------------

def active_items_stmt(
    item_type: str | None = None,
    favorites_only: bool = False,
    search: str | None = None,
):
    """Canonical statement builder for non-deleted items with detail eager-loaded.
    All list/detail/search endpoints build off this.
    """
    stmt = (
        select(models.Item)
        .where(models.Item.deleted_at.is_(None))
        .options(
            selectinload(models.Item.recipe_detail),
            selectinload(models.Item.food_item_detail),
        )
    )
    if item_type is not None:
        stmt = stmt.where(models.Item.item_type == item_type)
    if favorites_only:
        stmt = stmt.where(models.Item.is_favorite.is_(True))
    if search:
        stmt = stmt.where(models.Item.name.ilike(f"%{search}%"))
    return stmt


def items_by_id_stmt(item_id: int, *, include_deleted: bool = False):
    """Detail query for a single item by id. Does NOT eager-load meal_entries."""
    stmt = (
        select(models.Item)
        .where(models.Item.id == item_id)
        .options(
            selectinload(models.Item.recipe_detail),
            selectinload(models.Item.food_item_detail),
        )
    )
    if not include_deleted:
        stmt = stmt.where(models.Item.deleted_at.is_(None))
    return stmt


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------

async def list_items(
    db: AsyncSession,
    *,
    item_type: str | None = None,
    favorites_only: bool = False,
    search: str | None = None,
) -> list[models.Item]:
    stmt = active_items_stmt(
        item_type=item_type, favorites_only=favorites_only, search=search
    ).order_by(models.Item.name)
    result = await db.execute(stmt)
    items = list(result.scalars().all())
    await _attach_usage_counts(db, items)
    return items


async def get_item(
    db: AsyncSession, item_id: int, *, include_deleted: bool = False
) -> models.Item | None:
    result = await db.execute(items_by_id_stmt(item_id, include_deleted=include_deleted))
    item = result.scalar_one_or_none()
    if item is not None:
        await _attach_usage_counts(db, [item])
    return item


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------

def _ingredients_to_dicts(ingredients) -> list[dict]:
    """Normalize ingredient payload for JSONB storage."""
    if not ingredients:
        return []
    return [
        ing if isinstance(ing, dict) else ing.model_dump()
        for ing in ingredients
    ]


async def create_item(db: AsyncSession, payload: schemas.ItemCreate) -> models.Item:
    """Create a new item + its detail row in a single transaction."""
    item = models.Item(
        name=payload.name,
        item_type=payload.item_type.value,
        icon_emoji=payload.icon_emoji,
        icon_url=payload.icon_url,
        tags=payload.tags or [],
        is_favorite=payload.is_favorite,
    )
    db.add(item)
    await db.flush()  # populates item.id

    if payload.item_type == schemas.ItemType.RECIPE:
        assert payload.recipe_detail is not None  # validated by schema
        detail = models.RecipeDetail(
            item_id=item.id,
            description=payload.recipe_detail.description,
            ingredients=_ingredients_to_dicts(payload.recipe_detail.ingredients),
            instructions=payload.recipe_detail.instructions,
            prep_time_minutes=payload.recipe_detail.prep_time_minutes,
            cook_time_minutes=payload.recipe_detail.cook_time_minutes,
            servings=payload.recipe_detail.servings,
            image_url=payload.recipe_detail.image_url,
            source_url=payload.recipe_detail.source_url,
        )
        db.add(detail)
    else:
        assert payload.food_item_detail is not None  # validated by schema
        detail = models.FoodItemDetail(
            item_id=item.id,
            category=payload.food_item_detail.category,
            shopping_quantity=Decimal(str(payload.food_item_detail.shopping_quantity)),
            shopping_unit=payload.food_item_detail.shopping_unit,
        )
        db.add(detail)

    await db.commit()
    return await get_item(db, item.id)  # re-fetch with eager loads populated


async def update_item(
    db: AsyncSession, item_id: int, payload: schemas.ItemUpdate
) -> models.Item | None:
    """Patch an item and/or its detail row. Does NOT support changing item_type."""
    item = await get_item(db, item_id)
    if item is None:
        return None

    # --- Update scalar fields on Item ---
    item_fields = payload.model_dump(
        exclude_unset=True, exclude={"recipe_detail", "food_item_detail"}
    )
    if item_fields:
        for key, value in item_fields.items():
            setattr(item, key, value)

    # --- Update detail row (type-specific) ---
    if payload.recipe_detail is not None and item.item_type == "recipe":
        detail = item.recipe_detail
        if detail is None:
            # Defensive: shouldn't happen for a well-formed item, but handle it
            detail = models.RecipeDetail(item_id=item.id)
            db.add(detail)
        patch = payload.recipe_detail.model_dump(exclude_unset=True)
        if "ingredients" in patch:
            patch["ingredients"] = _ingredients_to_dicts(patch["ingredients"])
        for key, value in patch.items():
            setattr(detail, key, value)

    if payload.food_item_detail is not None and item.item_type == "food_item":
        detail = item.food_item_detail
        if detail is None:
            detail = models.FoodItemDetail(item_id=item.id)
            db.add(detail)
        patch = payload.food_item_detail.model_dump(exclude_unset=True)
        if "shopping_quantity" in patch:
            patch["shopping_quantity"] = Decimal(str(patch["shopping_quantity"]))
        for key, value in patch.items():
            setattr(detail, key, value)

    await db.commit()
    return await get_item(db, item_id)


# ---------------------------------------------------------------------------
# Soft-delete + undo (Expansion B minimal implementation)
# ---------------------------------------------------------------------------

# Undo tokens live in Redis (already running for Celery) so any API worker can
# consume a token issued by any other worker, and tokens survive an API restart.
# Key: undo:item:{token}  Value: item id (string)  TTL: _UNDO_WINDOW seconds.
_UNDO_WINDOW = timedelta(seconds=15)
_UNDO_KEY_PREFIX = "undo:item:"
_REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# redis.asyncio binds connections to the running event loop, so we cache one
# client per loop. Production runs a single loop forever (one entry); tests
# create a fresh loop per case (one entry per test).
_redis_clients: dict[int, redis.Redis] = {}


def _get_redis() -> redis.Redis:
    loop = asyncio.get_running_loop()
    key = id(loop)
    client = _redis_clients.get(key)
    if client is None:
        client = redis.from_url(_REDIS_URL, decode_responses=True)
        _redis_clients[key] = client
    return client


async def _issue_undo_token(item_id: int) -> tuple[str, datetime]:
    token = secrets.token_urlsafe(24)
    expires_at = datetime.utcnow() + _UNDO_WINDOW
    await _get_redis().set(
        f"{_UNDO_KEY_PREFIX}{token}",
        str(item_id),
        ex=int(_UNDO_WINDOW.total_seconds()),
    )
    return token, expires_at


async def _consume_undo_token(token: str, item_id: int) -> bool:
    """Atomically consume a token. Returns True iff the token existed, matched
    the expected item id, and was not yet expired. Uses Redis GETDEL so two
    concurrent undo requests can't both succeed."""
    raw = await _get_redis().getdel(f"{_UNDO_KEY_PREFIX}{token}")
    if raw is None:
        return False
    try:
        return int(raw) == item_id
    except (TypeError, ValueError):
        return False


async def soft_delete_item(
    db: AsyncSession, item_id: int
) -> tuple[models.Item, str, datetime] | None:
    """Mark an item as soft-deleted and cascade-hide its meal_entries.

    Returns (item, undo_token, expires_at) on success, None if the item doesn't
    exist or is already deleted.
    """
    item = await get_item(db, item_id)
    if item is None:
        return None

    now = datetime.utcnow()
    item.deleted_at = now

    # Cascade soft-hide the item's meal_entries so they drop from visible queries.
    await db.execute(
        update(models.MealEntry)
        .where(models.MealEntry.item_id == item_id)
        .where(models.MealEntry.soft_hidden_at.is_(None))
        .values(soft_hidden_at=now)
    )

    await db.commit()
    token, expires_at = await _issue_undo_token(item_id)
    return item, token, expires_at


async def undo_soft_delete_item(
    db: AsyncSession, item_id: int, undo_token: str
) -> models.Item | None:
    """Restore a soft-deleted item if the undo_token matches and hasn't expired.

    Returns the restored item, or None if the token is invalid/expired/mismatched.
    Caller should map None to HTTP 410.
    """
    if not await _consume_undo_token(undo_token, item_id):
        return None

    item = await get_item(db, item_id, include_deleted=True)
    if item is None or item.deleted_at is None:
        return None

    item.deleted_at = None

    # Cascade restore the item's soft-hidden meal_entries. Clear undo_token too:
    # if an entry had a user-undo token when the parent was soft-deleted, restoring
    # the parent brings the entry back to live — the state-machine invariant
    # (crud_meal_entries.py module docstring) requires live rows to have
    # undo_token=NULL. Without this, the CAS in undo_delete_meal_entry still
    # refuses to flip a live row (soft_hidden_at IS NULL fails the WHERE), but
    # the stale token is a latent hazard for future readers.
    await db.execute(
        update(models.MealEntry)
        .where(models.MealEntry.item_id == item_id)
        .where(models.MealEntry.soft_hidden_at.is_not(None))
        .values(soft_hidden_at=None, undo_token=None)
    )

    await db.commit()
    return await get_item(db, item_id)
