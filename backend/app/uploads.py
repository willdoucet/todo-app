"""Upload storage flow (M7).

The single write path for all four upload types. Compensating-transaction
semantics — R2 (or local disk) is written FIRST, then the ``assets`` manifest
row; a DB failure after a successful ``put`` triggers a compensating
``delete`` so no orphan object survives:

    1. validate + read (magic-byte, per-type cap)   → 413 / 415 on failure
    2. key = "{subdir}/{uuid4}.{ext}"
    3. storage.put(key, data, content_type)         ← storage-first
    4. INSERT assets(key, referenced=false) + commit
    5. on DB failure after put → storage.delete(key) (log if that also fails —
       the only residual-orphan path; the abandoned-upload sweep is the backstop)
    6. return "/uploads/{key}"                       ← unchanged public contract

Per-type caps (M7 Fork 3): icons 1 MB, photos / recipe images 5 MB.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from . import models
from .storage import get_storage
from .storage.keys import MANAGED_SUBDIRS
from .utils.upload_validation import validate_and_read

logger = logging.getLogger(__name__)

# Per-type size caps.
ICON_MAX_BYTES = 1 * 1024 * 1024   # item-icons, responsibility-icons
PHOTO_MAX_BYTES = 5 * 1024 * 1024  # family photos, recipe images


async def store_upload(
    db: AsyncSession,
    file: UploadFile,
    subdir: str,
    *,
    max_bytes: int,
) -> str:
    """Validate, store, and manifest an uploaded file. Returns the logical
    ``/uploads/{key}`` URL (unchanged contract). Raises HTTPException 413/415
    on validation failure (before anything is stored)."""
    # The media read route only serves the allowlisted subdirs, so a typo here
    # would mint keys that upload fine and then 404 forever on read. Fail at
    # the write site instead (caller bug, not user input — hence assert-style).
    if subdir not in MANAGED_SUBDIRS:
        raise ValueError(
            f"unknown upload subdir {subdir!r}; add it to "
            f"storage.keys.MANAGED_SUBDIRS"
        )

    validated = await validate_and_read(file, max_bytes=max_bytes)
    key = f"{subdir}/{uuid.uuid4()}{validated.ext}"

    # End the auth-dependency transaction BEFORE the storage call. `get_current_user`
    # already SELECTed on this session, which autobegan a transaction and checked
    # out a pool connection. PR2 puts that PUT on R2 (5 s + 15 s, one retry);
    # holding the connection across it is the same pool-starvation path the
    # media read route already closed. `commit()` of a read-only txn is how
    # every CRUD handler ends work, so the SAVEPOINT test wiring absorbs it.
    await db.commit()

    storage = get_storage()
    await storage.put(key, validated.content, validated.content_type)

    try:
        db.add(
            models.Asset(
                key=key,
                content_type=validated.content_type,
                size_bytes=validated.size_bytes,
                referenced=False,
            )
        )
        await db.commit()
    except BaseException:
        # Compensating delete — the just-written object would otherwise orphan.
        # BaseException (not Exception) so client-disconnect cancellation
        # after put still reclaims the object; CancelledError is not an
        # Exception on 3.9+.
        try:
            await db.rollback()
        except Exception:
            logger.exception("compensating delete: rollback failed for key=%s", key)
        try:
            await storage.delete(key)
        except Exception:
            # Residual-orphan path: object written, manifest row absent, delete
            # failed. The abandoned-upload sweep can't see it (no row), so this
            # is the one case that leaks — log loudly for ops.
            logger.exception(
                "compensating delete FAILED — orphaned storage object key=%s", key
            )
        raise

    return f"/uploads/{key}"
