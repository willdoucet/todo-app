"""Canonical /items routes — replaces /recipes and /food-items.

Endpoints:
    GET    /items                          — list all items
    GET    /items/{id}                     — fetch one item with its detail
    POST   /items                          — create
    PATCH  /items/{id}                     — update (partial)
    DELETE /items/{id}                     — soft-delete, returns {undo_token, expires_at}
    POST   /items/{id}/undo                — restore soft-deleted item
    POST   /items/suggest-icon             — AI-backed emoji suggestion
    POST   /items/import-from-url          — kick off async recipe extraction from a URL
    GET    /items/import-status/{task_id}  — poll extraction status / result
    POST   /uploads/item-icon              — file upload (lives in routes/uploads.py)
"""
from __future__ import annotations

import json
import logging
import os
import re
import uuid
from datetime import datetime
from typing import List, Literal, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, HttpUrl

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from .. import crud_items, schemas
from ..celery_app import celery_app
from ..constants import import_errors as codes
from ..database import get_db
from ..utils.url_safety import SSRFBlocked, URLResolutionFailed, validate_url_for_fetch

log = logging.getLogger(__name__)

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
# AI: Icon suggestion
# ---------------------------------------------------------------------------


class SuggestIconRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)


class SuggestIconResponse(BaseModel):
    emoji: Optional[str]
    fallback_used: bool = False


# One or two grapheme clusters covers nearly every food emoji (including
# multi-codepoint sequences like 🫶🏽). We conservatively extract the first
# one from the model's reply.
_EMOJI_FIRST_TOKEN = re.compile(r"\S+")


@router.post("/suggest-icon", response_model=SuggestIconResponse)
def suggest_icon(payload: SuggestIconRequest) -> SuggestIconResponse:
    """Ask Claude for the best single emoji for a food item name.

    Sync endpoint — the LLM call is short (one-token-ish response, ~1s
    latency). On any failure, returns ``{emoji: null, fallback_used: true}``
    so the client can fall back to its existing deterministic
    ``suggestEmoji()`` helper.
    """
    # Local import keeps route-module import cheap when AI deps are absent.
    from ..services import ai_client

    try:
        raw = ai_client.call_text(
            system_prompt=(
                "You suggest food-related emojis. Given a food item name, "
                "reply with EXACTLY ONE emoji character and nothing else — "
                "no words, no punctuation, no explanation."
            ),
            user_prompt=f"Food item: {payload.name.strip()}",
            # 32 tokens covers multi-codepoint emojis (family, ZWJ sequences,
            # skin-tone modifiers) without truncating mid-grapheme.
            max_tokens=32,
        )
    except Exception as exc:  # noqa: BLE001 — endpoint must never 500 on AI hiccups
        log.warning("suggest_icon.ai_failed", extra={"err": str(exc)[:200]})
        return SuggestIconResponse(emoji=None, fallback_used=True)

    # Extract the first non-whitespace token.
    match = _EMOJI_FIRST_TOKEN.search(raw or "")
    if not match:
        return SuggestIconResponse(emoji=None, fallback_used=True)
    return SuggestIconResponse(emoji=match.group(0), fallback_used=False)


# ---------------------------------------------------------------------------
# AI: Recipe URL import (async via Celery)
# ---------------------------------------------------------------------------


class ImportFromUrlRequest(BaseModel):
    url: HttpUrl


class ImportFromUrlResponse(BaseModel):
    task_id: str


# Accepted-task marker TTL — see plan. 15 minutes past the 60s polling ceiling.
_MARKER_TTL_SECONDS = 15 * 60
_MARKER_KEY_PREFIX = "recipe_import:accepted:"


_redis_singleton = None


def _redis_client():
    """Module-cached sync Redis client. Lazy so tests that stub the broker
    don't depend on redis being reachable at module import time."""
    global _redis_singleton
    if _redis_singleton is None:
        import redis  # noqa: F401 — lazy to keep import-time cheap

        url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        _redis_singleton = redis.Redis.from_url(url, decode_responses=True)
    return _redis_singleton


@router.post("/import-from-url", response_model=ImportFromUrlResponse)
def import_from_url(payload: ImportFromUrlRequest) -> ImportFromUrlResponse:
    """Queue a recipe-extraction task for the given URL. Returns the
    Celery task ID immediately; the client polls
    ``GET /items/import-status/{task_id}`` for progress and the final result.
    """
    url_str = str(payload.url)

    # SSRF pre-gate — validated again on every redirect hop inside the task.
    try:
        validate_url_for_fetch(url_str)
    except SSRFBlocked as exc:
        log.warning(
            "recipe_import.ssrf_blocked",
            extra={"url_host": urlparse(url_str).hostname or "unknown", "detail": str(exc)[:200]},
        )
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": codes.SSRF_BLOCKED,
                "message": codes.ERROR_CATALOG[codes.SSRF_BLOCKED].user_facing_message,
            },
        ) from exc
    except URLResolutionFailed as exc:
        # DNS failure is not a security event — don't return ssrf_blocked.
        # Fail fast at submit with fetch_failed rather than waiting ~15s for
        # httpx to hit the same failure inside the Celery task.
        log.info(
            "recipe_import.dns_failure_at_submit",
            extra={"url_host": urlparse(url_str).hostname or "unknown", "detail": str(exc)[:200]},
        )
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": codes.FETCH_FAILED,
                "message": codes.ERROR_CATALOG[codes.FETCH_FAILED].user_facing_message,
            },
        ) from exc

    # Pre-allocate the task_id so we can write the accepted-task marker
    # BEFORE dispatching. This closes the race where a very fast task
    # could complete + have its Celery result expire before the marker
    # write finished — leaving the status endpoint returning not_found
    # despite the task having run successfully.
    task_id = str(uuid.uuid4())
    url_host = urlparse(url_str).hostname or "unknown"

    # Write marker first. If Redis is down, fail loudly with 503 — we can't
    # safely queue a task whose result won't be trackable.
    try:
        _redis_client().setex(
            _MARKER_KEY_PREFIX + task_id,
            _MARKER_TTL_SECONDS,
            json.dumps({"url_host": url_host}),
        )
    except Exception as exc:  # noqa: BLE001 — redis.ConnectionError + friends
        log.error(
            "recipe_import.marker_write_failed",
            extra={"task_id": task_id, "detail": str(exc)[:200]},
            exc_info=True,
        )
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": codes.BROKER_UNAVAILABLE,
                "message": codes.ERROR_CATALOG[codes.BROKER_UNAVAILABLE].user_facing_message,
            },
        ) from exc

    # Now queue with the pre-allocated id. Catch broker unavailable
    # (Redis/Celery down) so the user sees a retryable 503.
    try:
        from ..tasks import extract_recipe_from_url as task  # local import to avoid app-init cycles
        task.apply_async(args=[url_str], task_id=task_id)
    except Exception as exc:  # kombu.OperationalError + friends
        log.error(
            "recipe_import.broker_unavailable",
            extra={"detail": str(exc)[:200]},
            exc_info=True,
        )
        # Clean up the orphaned marker to avoid a 15min ghost entry.
        try:
            _redis_client().delete(_MARKER_KEY_PREFIX + task_id)
        except Exception:  # noqa: BLE001
            pass
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": codes.BROKER_UNAVAILABLE,
                "message": codes.ERROR_CATALOG[codes.BROKER_UNAVAILABLE].user_facing_message,
            },
        ) from exc

    log.info(
        "recipe_import.queued",
        extra={"task_id": task_id, "url_host": url_host},
    )
    return ImportFromUrlResponse(task_id=task_id)


class ImportStatusResponse(BaseModel):
    status: Literal["pending", "progress", "complete", "failed", "not_found"]
    step: Optional[str] = None
    error_code: Optional[str] = None
    recipe: Optional[dict] = None


@router.get("/import-status/{task_id}", response_model=ImportStatusResponse)
def import_status(task_id: str) -> ImportStatusResponse:
    """Report the status of a queued recipe-import task.

    Resolution order:
    1. Check the accepted-task marker. If missing, return ``not_found`` so the
       client can surface a clear error instead of polling a fake ``pending``
       forever (Celery's default behavior for unknown IDs).
    2. Marker present → ask Celery. PROGRESS state includes the ``step`` meta
       we wrote in the task. SUCCESS → inspect the returned dict's ``status``
       field — the task stores structured failures there.
    """
    # 1. Accepted-task marker
    try:
        client = _redis_client()
        marker_exists = client.exists(_MARKER_KEY_PREFIX + task_id) == 1
    except Exception as exc:  # noqa: BLE001
        log.error(
            "recipe_import.status_redis_error",
            extra={"task_id": task_id, "detail": str(exc)[:200]},
            exc_info=True,
        )
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": codes.BROKER_UNAVAILABLE,
                "message": codes.ERROR_CATALOG[codes.BROKER_UNAVAILABLE].user_facing_message,
            },
        ) from exc

    if not marker_exists:
        return ImportStatusResponse(
            status="not_found",
            error_code=codes.UNKNOWN_OR_EXPIRED_TASK,
        )

    # 2. Celery AsyncResult
    async_result = celery_app.AsyncResult(task_id)
    state = async_result.state  # 'PENDING' | 'PROGRESS' | 'SUCCESS' | 'FAILURE' | 'REVOKED'

    if state == "PENDING":
        # Marker exists but Celery hasn't started — truly queued.
        return ImportStatusResponse(status="pending", step="queued")

    if state == "PROGRESS":
        meta = async_result.info or {}
        step = meta.get("step") if isinstance(meta, dict) else None
        return ImportStatusResponse(status="progress", step=step)

    if state == "SUCCESS":
        payload = async_result.result
        if not isinstance(payload, dict):
            # Defensive — should never happen with our task shape.
            return ImportStatusResponse(
                status="failed",
                error_code=codes.INTERNAL_ERROR,
            )
        inner_status = payload.get("status")
        if inner_status == "complete":
            return ImportStatusResponse(status="complete", recipe=payload.get("recipe"))
        if inner_status == "failed":
            return ImportStatusResponse(
                status="failed",
                error_code=payload.get("error_code") or codes.INTERNAL_ERROR,
            )
        return ImportStatusResponse(status="failed", error_code=codes.INTERNAL_ERROR)

    if state == "FAILURE":
        # The task raised an unhandled exception. Our task catches everything,
        # so this is rare. Distinguish between:
        #   - hard time-limit kill (Celery's SIGKILL bypasses our try/except)
        #     → task_timeout
        #   - genuine worker crash (OOM, segfault, etc.) → internal_error
        info = async_result.info
        info_type = type(info).__name__ if info else ""
        is_timeout = info_type in ("TimeLimitExceeded", "SoftTimeLimitExceeded")
        error_code = codes.TASK_TIMEOUT if is_timeout else codes.INTERNAL_ERROR
        log.warning(
            "recipe_import.status_celery_failure",
            extra={
                "task_id": task_id,
                "info_type": info_type,
                "info": str(info)[:200],
                "mapped_to": error_code,
            },
        )
        return ImportStatusResponse(status="failed", error_code=error_code)

    if state == "REVOKED":
        return ImportStatusResponse(status="failed", error_code=codes.INTERNAL_ERROR)

    # Unknown Celery state — treat as pending, let the client keep polling
    # (the 60s client-side ceiling will eventually give up).
    return ImportStatusResponse(status="pending", step="queued")
