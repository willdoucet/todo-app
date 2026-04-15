"""Canonical /items routes — replaces /recipes and /food-items.

Endpoints (plan §0.3 lines 830-841):
    GET    /items                    — list all items (?type=recipe|food_item, ?favorites_only, ?search)
    GET    /items/{id}               — fetch one item with its detail
    POST   /items                    — create
    PATCH  /items/{id}               — update (partial)
    DELETE /items/{id}               — soft-delete, returns {undo_token, expires_at}
    POST   /items/{id}/undo          — restore soft-deleted item (body: {undo_token})
    POST   /items/suggest-icon       — stub for Expansion C (AI icon suggest)
    POST   /uploads/item-icon        — the file upload path lives in routes/uploads.py already
"""
from datetime import datetime
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .. import crud_items, schemas
from ..database import get_db

router = APIRouter(
    prefix="/items",
    tags=["items"],
    responses={404: {"description": "Not found"}},
)


# ---------------------------------------------------------------------------
# Request/response models scoped to this router
# ---------------------------------------------------------------------------

class UndoResponse(BaseModel):
    undo_token: str
    expires_at: datetime


class DeleteResponse(BaseModel):
    id: int
    undo_token: str
    expires_at: datetime


class UndoRequest(BaseModel):
    undo_token: str


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

@router.get("/", response_model=List[schemas.ItemRead])
async def list_items(
    type: Optional[Literal["recipe", "food_item"]] = Query(
        None, description="Filter by item type"
    ),
    favorites_only: bool = Query(False, description="Only show favorited items"),
    search: Optional[str] = Query(None, description="Case-insensitive name search"),
    db: AsyncSession = Depends(get_db),
):
    """List items, optionally filtered by type/favorites/search."""
    return await crud_items.list_items(
        db, item_type=type, favorites_only=favorites_only, search=search
    )


@router.get("/{item_id}", response_model=schemas.ItemRead)
async def get_item(item_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single item by id with its detail eagerly loaded."""
    item = await crud_items.get_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.post("/", response_model=schemas.ItemRead, status_code=status.HTTP_201_CREATED)
async def create_item(
    payload: schemas.ItemCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new item (recipe or food_item) and its detail row."""
    try:
        return await crud_items.create_item(db, payload)
    except IntegrityError as e:
        # The partial unique index on (name, item_type) raises on duplicate name
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An item named '{payload.name}' of type '{payload.item_type.value}' already exists",
        )


@router.patch("/{item_id}", response_model=schemas.ItemRead)
async def update_item(
    item_id: int,
    payload: schemas.ItemUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Partial update of an item and/or its detail row."""
    try:
        updated = await crud_items.update_item(db, item_id, payload)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An item with that name and type already exists",
        )
    if updated is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return updated


@router.delete("/{item_id}", response_model=DeleteResponse)
async def delete_item(item_id: int, db: AsyncSession = Depends(get_db)):
    """Soft-delete an item. Returns an undo_token valid for ~15 seconds.

    The item is marked with `deleted_at = now()` and any meal_entries referencing
    it are soft-hidden. Use `POST /items/{id}/undo` with the returned token to
    restore within the window. After the window expires the item is hard-deleted
    by the Celery beat task `hard_delete_expired_soft_deletes` (see Expansion B).
    """
    result = await crud_items.soft_delete_item(db, item_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Item not found")
    item, token, expires_at = result
    return DeleteResponse(id=item.id, undo_token=token, expires_at=expires_at)


@router.post("/{item_id}/undo", response_model=schemas.ItemRead)
async def undo_delete_item(
    item_id: int,
    payload: UndoRequest,
    db: AsyncSession = Depends(get_db),
):
    """Restore a soft-deleted item using the undo_token issued by DELETE /items/{id}.

    Returns 410 Gone if the token is invalid, expired, or mismatched — matching
    the plan's Expansion B behavior for stale/wrong tokens.
    """
    try:
        restored = await crud_items.undo_soft_delete_item(db, item_id, payload.undo_token)
    except IntegrityError:
        # Undo collision against the partial unique index: another item with the
        # same name was created during the undo window. Eng Review #3 Issue 4.
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "name_collision"},
        )
    if restored is None:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Undo window expired, token mismatch, or item no longer deleted",
        )
    return restored


# ---------------------------------------------------------------------------
# Expansion C stubs — full implementation lives in Chunk 6
# ---------------------------------------------------------------------------

@router.post("/suggest-icon", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def suggest_icon():
    """AI icon suggestion stub — implemented in Chunk 6 / Expansion C."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Icon suggestion not yet implemented (Chunk 6 / Expansion C)",
    )
