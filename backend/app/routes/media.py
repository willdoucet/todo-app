"""Private media reads (M7 PR2) — the route that replaces the StaticFiles mount.

Before this, `/uploads/*` was `app.mount("/uploads", StaticFiles(...))`: a
public static surface that BYPASSED the `protected` APIRouter entirely, gated
only by Cloudflare Access at the edge. That mount was the single load-bearing
reason CF Access Application 1 had to survive since M5 — a router dependency
can gate routes, but it cannot gate a mount. This module closes that hole.

Why it is not on the `protected` router
---------------------------------------
Every consumer is a plain ``<img src={apiUrl(...)}>``, and a browser cannot
attach an ``Authorization: Bearer`` header to a subresource load. So this route
hangs off `app` directly with its own cookie dependency,
:func:`app.auth.dependencies.require_media_session`.

⚠️  GUARDRAIL — do not add ``crossorigin`` to an `<img>` that points here, and
    do not switch image loading to ``fetch()``/``XMLHttpRequest`` or a CSS
    ``background-image``. All three suppress the ``__Host-refresh`` cookie on
    the subresource request, which would 401 EVERY image in the app. Verified
    at M7 planning: all 11 image consumers are plain `<img>` with no
    ``crossorigin``. The matching warning sits next to them in
    ``frontend/src/lib/apiBase.js``.

Path shape is unchanged (`/uploads/{key}`), which is the whole reason M7 needs
no data migration: the DB columns store logical paths, the frontend resolves
them with ``apiUrl()`` at render time, so swapping the storage backend and the
access model leaves every `<img>` consumer and every stored column untouched.

Response policy
---------------
``Cache-Control: private, no-cache`` + ``X-Content-Type-Options: nosniff`` +
``ETag`` + ``If-None-Match`` → 304. Deliberately NO ``Vary: Cookie``: the
refresh cookie rotates every ~15 minutes of use, and a browser treats a cached
entry whose Vary'd header changed as unusable — every rotation would turn every
image back into a full download, defeating the 304 path. ``private`` already
forbids shared caches, and a browser cache is per-profile by definition.

The conditional is evaluated ONLY after the key passes the allowlist and the
representation is proven to exist — see the comment in :func:`read_media`.

  - ``private`` is the load-bearing directive: it forbids the Cloudflare edge
    from caching a private image. A ``public``/``max-age`` directive would let
    CF serve family photos to an unauthenticated client.
  - ``no-cache`` (NOT ``no-store``) lets the *browser* keep the bytes but
    revalidate on every use. The revalidation request carries the cookie and
    re-runs the guard, so auth is still enforced on every load — a valid
    session just gets an empty 304 instead of re-streaming 5 MB through
    Fly + R2.
  - ``ETag = key`` is always safe because keys are immutable UUIDs: a new
    upload is a new key, so a matching ETag can never mean stale content.

Failure mapping (all four are distinct on purpose)
--------------------------------------------------
  malformed / unknown-subdir key   → 404, before any storage call
  no manifest row                  → 404
  manifest row but object gone     → 404
  storage unreachable (R2 down)    → 503 + a distinctly-logged error, so ops
                                     can tell "unknown key" from "R2 down"
"""

from __future__ import annotations

import logging
from typing import Optional

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import require_media_session
from ..database import get_db
from ..models import Asset
from ..storage import ObjectNotFound, get_storage
from ..storage.keys import is_managed_key, is_stock_icon_key, stock_icon_path

logger = logging.getLogger(__name__)

router = APIRouter(tags=["media"])

# All bundled stock icons are PNG. This is the one deliberate exception to
# "content_type comes from the manifest" — stock icons have no manifest row.
STOCK_ICON_CONTENT_TYPE = "image/png"

_CACHE_CONTROL = "private, no-cache"

# Sent on 200 and 304 alike.
#   nosniff — this route hands user-uploaded bytes back to a browser; never let
#     the browser second-guess the content-type we derived from magic bytes.
#   No `Vary: Cookie` — see the module docstring; it would void the 304 path on
#     every cookie rotation.
_MEDIA_HEADERS = {
    "Cache-Control": _CACHE_CONTROL,
    "X-Content-Type-Options": "nosniff",
}

# Error responses. Cloudflare caches by URL extension, and these URLs end in
# .png/.jpg/.webp — with no Cache-Control an authenticated user's 404 could be
# edge-cached for minutes and replayed to anyone. Keys are unguessable UUIDs so
# the exposure is nil, but the header costs nothing and makes it structurally
# impossible.
_ERROR_HEADERS = {"Cache-Control": "private, no-store"}


def _headers(etag: str) -> dict[str, str]:
    return {**_MEDIA_HEADERS, "ETag": etag}


def _etag(key: str) -> str:
    return f'"{key}"'


def _not_found() -> HTTPException:
    """One 404 for every not-servable case. Byte-identical bodies so the
    response cannot be used to probe which keys exist or which subdirs are
    real."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="not_found", headers=_ERROR_HEADERS
    )


def _if_none_match_hit(header: Optional[str], etag: str) -> bool:
    """RFC 9110 If-None-Match comparison, weak-compare (correct for GET).

    Handles the shapes a real client sends: a bare tag, a comma-separated
    list, ``W/``-prefixed weak tags, and ``*``.
    """
    if not header:
        return False
    for candidate in header.split(","):
        candidate = candidate.strip()
        if candidate == "*":
            return True
        if candidate.startswith("W/"):
            candidate = candidate[2:]
        if candidate == etag:
            return True
    return False


@router.get("/uploads/{key:path}")
async def read_media(
    key: str,
    if_none_match: Optional[str] = Header(default=None, alias="If-None-Match"),
    _user_id: int = Depends(require_media_session),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Serve a private upload to an authenticated session.

    The cookie guard has already run as a dependency — an absent, unknown,
    revoked, expired, or past-grace-superseded session never reaches this body.
    """
    # ORDER IS LOAD-BEARING — validate, then prove the representation exists,
    # and only THEN consider `If-None-Match`. Two bugs the pre-landing review
    # found by building the ETag from the raw path param first:
    #   * `key` is `{key:path}`, so it can hold any character. `ETag: "<key>"`
    #     with a non-latin-1 byte raised UnicodeEncodeError inside Starlette's
    #     header encoding — an unhandled 500 on this route, post-auth.
    #   * RFC 9110 §13.1.2: a conditional is only evaluated against a CURRENT
    #     representation. Returning 304 for a key with no object let a browser
    #     keep rendering a deleted photo from its own cache indefinitely.
    # After the gates below, `key` is either `stock_icons/[a-z0-9-]+\.png` or
    # `{allowlisted subdir}/{lowercase-hex uuid}.{png|jpg|webp}` — ASCII by
    # construction, and known to exist.

    # Stock-icon compat branch. These are bundled in the image, have no
    # manifest row, and were never in R2 — but entity columns adopted them as
    # `/uploads/stock_icons/*.png` long before M7, so without this branch every
    # responsibility and item that picked a stock icon would 404.
    if is_stock_icon_key(key):
        try:
            data = stock_icon_path(key).read_bytes()
        except (OSError, ValueError):
            raise _not_found()
        # Read-then-compare: the bundled icons are a handful of KB already in
        # the page cache, so proving existence costs the same as serving.
        etag = _etag(key)
        if _if_none_match_hit(if_none_match, etag):
            return _not_modified(etag)
        return _media_response(data, STOCK_ICON_CONTENT_TYPE, etag)

    # Reject malformed keys BEFORE any storage lookup: traversal (`../`),
    # absolute paths, unknown subdirs, non-UUID names, wrong extensions.
    if not is_managed_key(key):
        raise _not_found()

    # The manifest is the single authority for content-type (LocalDiskBackend
    # stores none, and trusting an R2-reported type would trust the upload).
    # It is also the existence proof the conditional below needs — one indexed
    # PK lookup, which is what a 304 now costs on top of the guard's lookup.
    row = (
        await db.execute(select(Asset).where(Asset.key == key))
    ).scalar_one_or_none()
    if row is None:
        raise _not_found()

    content_type = row.content_type

    etag = _etag(key)
    if _if_none_match_hit(if_none_match, etag):
        # The validator matched a representation that exists, so the browser's
        # copy is current. The guard above already re-authorized this load,
        # which is the entire reason `no-cache` is safe. Skips the R2 GET —
        # the whole point of the ETag.
        return _not_modified(etag)

    # Give the pooled connection back BEFORE the storage call. The SELECT above
    # autobegan a transaction, and `get_db` would otherwise hold that connection
    # for the whole request — including an R2 round trip that, on a bad day, is
    # bounded only by the client timeouts in `storage/r2.py`. The pool is 15
    # wide; one page of images against a hung R2 would starve `/auth/refresh`
    # and every protected route. Nothing here is written, so `commit()` is
    # purely "end the transaction"; `expire_on_commit=False` keeps
    # `content_type` readable, and it is the same call every CRUD handler makes,
    # so the test suite's SAVEPOINT wiring absorbs it (a `close()` would tear
    # the test session down instead — pre-landing review, run 2).
    await db.commit()

    try:
        data = await get_storage().get(key)
    except ObjectNotFound:
        # Manifest row exists but the object is gone. A real 404 — the page
        # degrades to a broken image rather than crashing.
        raise _not_found()
    except (ClientError, BotoCoreError, OSError, TimeoutError):
        # Storage genuinely unreachable: R2 down, timeout, credentials
        # rejected, disk error. Logged distinctly from the 404 above so ops
        # can tell "unknown key" from "R2 is down", and surfaced as 503 (a
        # dependency is unavailable) rather than a misleading 404.
        #
        # Deliberately NOT a bare `except Exception`: a TypeError or an
        # AttributeError from our own code is a bug, not an outage, and
        # reporting it as `storage_unavailable` sends whoever is on call to
        # the Cloudflare dashboard for a Python mistake. Those raise and
        # become a real 500.
        logger.exception(
            "media read: STORAGE UNREACHABLE for key=%s (not a missing-key 404)",
            key,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="storage_unavailable",
            headers=_ERROR_HEADERS,
        )

    return _media_response(data, content_type, etag)


def _not_modified(etag: str) -> Response:
    return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=_headers(etag))


def _media_response(data: bytes, content_type: str, etag: str) -> Response:
    return Response(content=data, media_type=content_type, headers=_headers(etag))
