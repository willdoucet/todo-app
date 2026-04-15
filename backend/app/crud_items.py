"""Canonical CRUD for the unified Item model.

Replaces `crud_recipes.py` and `crud_food_items.py` after the item-model refactor.

Query-builder convention: all list/detail/search reads build off `active_items_stmt()`
which enforces `deleted_at IS NULL` and eager-loads both detail relationships via
`selectinload` to avoid N+1 on list queries (adversarial review #3 + #7).

See plan §0.3 for the full API contract.
"""
from datetime import datetime, timedelta
import secrets
from decimal import Decimal

from sqlalchemy import func, select, update, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from . import models, schemas


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

# Undo token → (item_id, expires_at). In-memory for single-instance deployments;
# for multi-instance this would live in Redis. Family-app scale = single-instance.
_undo_tokens: dict[str, tuple[int, datetime]] = {}
_UNDO_WINDOW = timedelta(seconds=15)


def _issue_undo_token(item_id: int) -> tuple[str, datetime]:
    token = secrets.token_urlsafe(24)
    expires_at = datetime.utcnow() + _UNDO_WINDOW
    _undo_tokens[token] = (item_id, expires_at)
    # Opportunistic cleanup of expired tokens
    now = datetime.utcnow()
    for t in list(_undo_tokens.keys()):
        if _undo_tokens[t][1] < now:
            del _undo_tokens[t]
    return token, expires_at


def _consume_undo_token(token: str, item_id: int) -> bool:
    entry = _undo_tokens.get(token)
    if entry is None:
        return False
    expected_item_id, expires_at = entry
    if expected_item_id != item_id:
        return False
    if expires_at < datetime.utcnow():
        del _undo_tokens[token]
        return False
    del _undo_tokens[token]
    return True


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
    token, expires_at = _issue_undo_token(item_id)
    return item, token, expires_at


async def undo_soft_delete_item(
    db: AsyncSession, item_id: int, undo_token: str
) -> models.Item | None:
    """Restore a soft-deleted item if the undo_token matches and hasn't expired.

    Returns the restored item, or None if the token is invalid/expired/mismatched.
    Caller should map None to HTTP 410.
    """
    if not _consume_undo_token(undo_token, item_id):
        return None

    item = await get_item(db, item_id, include_deleted=True)
    if item is None or item.deleted_at is None:
        return None

    item.deleted_at = None

    # Cascade restore the item's soft-hidden meal_entries
    await db.execute(
        update(models.MealEntry)
        .where(models.MealEntry.item_id == item_id)
        .where(models.MealEntry.soft_hidden_at.is_not(None))
        .values(soft_hidden_at=None)
    )

    await db.commit()
    return await get_item(db, item_id)
