"""Asset lifecycle hooks (M7).

Keeps uploaded-image storage in step with the entity columns that reference
it, so no orphan objects accumulate:

    adopt   an entity column takes a managed key   → assets.referenced = true
    release the column changes / the entity dies   → storage.delete + drop row

A *managed key* is a ``/uploads/{key}`` reference that is NOT a bundled stock
icon and NOT an external URL. Stock icons (``stock_icons/*``) are bundled +
unmanaged (no assets row); scraped recipe images are absolute ``http(s)://``
URLs — both resolve to ``None`` here and are never touched.

Ordering (adversarial review — post-commit cleanup):
  - ``adopt`` is DB-only (flip a boolean); run it INSIDE the entity's
    transaction so the flip is atomic with the write. If the entity write
    rolls back, the flip rolls back too. Doing it post-commit would risk the
    sweep reclaiming a just-adopted object if the flip then failed.
  - ``release`` performs an irreversible ``storage.delete``; run it ONLY AFTER
    the entity write has committed, so a rolled-back edit never erases a
    still-referenced object.

Invariant (A1): each managed key is adopted by at most one entity column, so
``release`` deletes unconditionally (no refcount).
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import delete as sa_delete, select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models
from ..storage import get_storage

logger = logging.getLogger(__name__)

_UPLOADS_PREFIX = "/uploads/"
_STOCK_PREFIX = "/uploads/stock_icons/"

# A managed key MUST match the exact shape `store_upload` produces:
# `{subdir}/{uuid4}.{png|jpg|webp}`. Validating this before the key ever
# reaches `storage.delete` is the trust boundary: `icon_url`/`photo_url`/
# `image_url` are unvalidated client strings, so a crafted value like
# `/uploads/../../etc/passwd` or `/uploads//etc/passwd` (leading slash — pathlib
# would discard the root) must NOT classify as managed, or it becomes an
# arbitrary-file-delete via the release hook. The subdir char class excludes
# `.` and `/`, so `..` and empty/absolute segments are rejected.
_KEY_RE = re.compile(
    r"^[a-z0-9_-]+/"
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    r"\.(png|jpg|webp)$"
)

# Abandoned uploads (never adopted) are swept after this age.
ABANDONED_UPLOAD_TTL = timedelta(hours=24)


def managed_key(url: str | None) -> str | None:
    """Return the storage key for a managed upload URL, else ``None``.

    ``None`` for: empty/None, external ``http(s)://`` URLs, and stock icons
    (``/uploads/stock_icons/*`` — bundled, no assets row, must never be
    deleted out from under other entities that share them)."""
    if not url or not url.startswith(_UPLOADS_PREFIX):
        return None
    if url.startswith(_STOCK_PREFIX):
        return None
    key = url[len(_UPLOADS_PREFIX):]
    # Reject anything that isn't a well-formed managed key — traversal
    # (`../`), leading-slash/absolute, and other malformed shapes all fail
    # here and classify as unmanaged (no adopt, no delete).
    if not _KEY_RE.match(key):
        return None
    return key


async def adopt(db: AsyncSession, url: str | None) -> None:
    """Flip ``assets.referenced = true`` for a managed key. DB-only — call
    INSIDE the entity transaction (before its commit). No-op for
    stock/external/None. Fail-closed if the key has no manifest row (the
    object was never uploaded, or the abandoned-upload sweep already
    reclaimed it) so the entity cannot store a dead ``/uploads/...`` link.
    Idempotent when the row is already ``referenced=true`` (repeat PATCH of
    the same URL, or the documented A1 shared-key case)."""
    key = managed_key(url)
    if key is None:
        return
    result = await db.execute(
        sa_update(models.Asset)
        .where(models.Asset.key == key)
        .values(referenced=True)
        .returning(models.Asset.key)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Unknown upload — the image was never saved or has expired. "
                "Please upload it again."
            ),
        )


async def release(db: AsyncSession, url: str | None) -> None:
    """Delete the storage object and drop its manifest row for a managed key.
    Call ONLY AFTER the entity write has committed. Commits the row drop
    itself. No-op for stock/external/None.

    If storage delete fails, keep the manifest row with ``referenced=false``
    so the abandoned-upload sweep can retry (the object is no longer live on
    any entity). Only drop the row after a successful delete."""
    key = managed_key(url)
    if key is None:
        return
    try:
        await get_storage().delete(key)
    except Exception:
        logger.exception("asset release: storage delete failed for key=%s", key)
        await db.execute(
            sa_update(models.Asset)
            .where(models.Asset.key == key)
            .values(referenced=False)
        )
        await db.commit()
        return
    await db.execute(sa_delete(models.Asset).where(models.Asset.key == key))
    await db.commit()


async def release_if_replaced(
    db: AsyncSession, old_url: str | None, new_url: str | None
) -> None:
    """Release ``old_url`` only if the column actually changed. Call AFTER the
    entity write commits. Cleanup keys off the PREVIOUS value alone — a
    managed→stock or managed→null swap still reclaims the old object."""
    if old_url != new_url:
        await release(db, old_url)


async def sweep_abandoned_uploads(db: AsyncSession) -> int:
    """Delete manifest rows + storage objects for uploads never adopted within
    the TTL — i.e. someone uploaded a file, then closed the tab before saving
    the entity. Returns the count deleted.

    Only ``referenced = false`` rows are candidates; adopted (referenced=true)
    objects are cleaned by the entity replace/delete hooks, never here. Uses
    naive-UTC comparison to match ``assets.created_at``'s ``now()`` default
    (same convention as the item hard-delete sweep).

    Rows are claimed with ``SELECT ... FOR UPDATE`` (so a concurrent adopt
    waits, then either sees ``referenced=true`` and is excluded, or sees the
    row gone and fail-closes). Storage delete runs while the lock is held;
    the manifest row is dropped only after a successful delete so a failed
    delete stays retryable."""
    cutoff = datetime.utcnow() - ABANDONED_UPLOAD_TTL
    claimed = await db.execute(
        select(models.Asset.key)
        .where(
            models.Asset.referenced.is_(False),
            models.Asset.created_at < cutoff,
        )
        .with_for_update()
    )
    keys = [key for (key,) in claimed.all()]
    if not keys:
        await db.commit()
        return 0

    storage = get_storage()
    reclaimed: list[str] = []
    for key in keys:
        try:
            await storage.delete(key)
            reclaimed.append(key)
        except Exception:
            logger.exception("sweep: storage delete failed for key=%s", key)

    if reclaimed:
        await db.execute(
            sa_delete(models.Asset).where(models.Asset.key.in_(reclaimed))
        )
    await db.commit()

    logger.info(
        "Abandoned-upload sweep: deleted %d unreferenced assets", len(reclaimed)
    )
    return len(reclaimed)
