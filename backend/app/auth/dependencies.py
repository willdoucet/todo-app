"""FastAPI dependencies for auth.

:func:`get_current_user` is the canonical "is this request authenticated"
dep. M3 SHIPS it (fully unit-tested) but does NOT apply it to any
non-auth route — M5 PR #1 turns it on across the API.

The only M3 use site is ``/auth/logout``, which does NOT use the FastAPI
dep wrapper because it needs to emit a structured log line on failure
(FastAPI's dep raises before the route handler runs, so we'd never see
the failure inside the handler). The route calls :func:`validate_bearer`
directly in a try/except.

Behavior on every protected request:
1. Read ``Authorization: Bearer <token>`` header. Missing/malformed → 401.
2. PyJWT decode (HS256). All four exception classes
   (:class:`jwt.ExpiredSignatureError`, :class:`jwt.InvalidSignatureError`,
   :class:`jwt.DecodeError`, :class:`jwt.InvalidTokenError`) → 401.
3. Validate claim shape — ``sub`` must parse to a non-negative int,
   ``session_version`` must be an int. Adversarial review: missing /
   stringified non-int / negative / otherwise malformed claims all 401
   without leaking 500.
4. Live DB lookup. Row missing → 401. Stale ``session_version`` → 401.
5. Return :class:`User`.

Cost: ONE indexed PK lookup per request. Below noise floor at
household scale.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional

import jwt
from fastapi import Cookie, Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import errors, tokens
from app.auth.logging_utils import emit_log_line
from app.auth.models import RefreshToken, User
from app.database import get_db


async def validate_bearer(
    authorization: Optional[str],
    db: AsyncSession,
) -> User:
    """Core validation. Importable as a plain async function so route
    handlers can wrap it in try/except for explicit log emission."""
    # 1. Header presence + shape.
    if not authorization:
        raise errors.unauthorized()
    parts = authorization.split(" ", 1)
    if (
        len(parts) != 2
        or parts[0].lower() != "bearer"
        or not parts[1].strip()
    ):
        raise errors.unauthorized()
    token = parts[1].strip()

    # 2. Decode + verify exp / signature. PyJWT's exception hierarchy:
    #    InvalidTokenError
    #    ├── DecodeError
    #    │   └── InvalidSignatureError
    #    └── ExpiredSignatureError
    # Listing all four explicitly so any future PyJWT change that adds
    # a new sibling class doesn't silently bubble up as 500.
    try:
        payload = tokens.decode_access_token(token)
    except (
        jwt.ExpiredSignatureError,
        jwt.InvalidSignatureError,
        jwt.DecodeError,
        jwt.InvalidTokenError,
    ):
        raise errors.unauthorized()

    # 3. Validate claim shape.
    sub_raw = payload.get("sub")
    sv_raw = payload.get("session_version")
    if sv_raw is None or not isinstance(sv_raw, int) or isinstance(sv_raw, bool):
        # bool is a subclass of int in Python — exclude explicitly.
        raise errors.unauthorized()
    if sub_raw is None:
        raise errors.unauthorized()
    try:
        user_id = int(sub_raw)
    except (TypeError, ValueError):
        raise errors.unauthorized()
    if user_id < 0:
        raise errors.unauthorized()

    # 4. Live DB lookup.
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise errors.unauthorized()
    if user.session_version != sv_raw:
        raise errors.unauthorized()
    return user


async def get_current_user(
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency wrapper. Equivalent to ``validate_bearer`` but
    declares its inputs as FastAPI parameters so it can be used as
    ``Depends(get_current_user)`` on a route."""
    return await validate_bearer(authorization, db)


# =============================================================================
# Media read guard (M7 PR2)
# =============================================================================
#
# `GET /uploads/{key}` is loaded by plain `<img src=...>`, and a browser cannot
# attach an `Authorization: Bearer` header to a subresource load. So the media
# route CANNOT ride the `protected` router — it needs a cookie-based check.
#
# This guard is a strict READ-ONLY subset of `service.refresh`: same shared
# validity predicate (`tokens.refresh_row_status`, eng review CQ1), but NO row
# lock, NO rotation, NO successor walk, and no new cookie. An image load must
# never perturb the 60-second rotation grace window that `/auth/refresh` owns.
#
# Cost: one indexed lookup on `ix_refresh_tokens_token_hash` per image load.
#
# Deliberately NOT checked here: `users.session_version`. Read-access
# revocation rides on the M3 invariant that logout and password/session-version
# rotation ALSO set `revoked_at` on the user's refresh rows. That invariant is
# now load-bearing for private image reads, and
# `tests/integration/auth/test_media_read.py` locks it (eng review T2).
#
# The guard is IDENTICAL in every environment — there is no dev/test bypass
# branch (eng review A2). A bypass flag that leaked to production would make
# every private image public, defeating the whole milestone. Test coverage
# splits by layer instead: pytest sets the cookie directly against the real
# route; the Playwright visual suite shims `/uploads/*` with fixture bytes;
# local dev works because `localhost:5173` and `localhost:8000` are same-site.


async def require_media_session(
    request: Request,
    media_cookie: Optional[str] = Cookie(
        default=None, alias=tokens.REFRESH_COOKIE_NAME
    ),
    db: AsyncSession = Depends(get_db),
) -> int:
    """Authorize a private media read from the refresh cookie alone.

    Returns the owning ``user_id`` (used only for the failure log line — this
    is a single-family instance, so there is no per-user media ownership).
    Raises a 401 ``unauthorized`` — byte-identical to every other 401 — for an
    absent, unknown, revoked, expired, or past-grace-superseded cookie.

    Only failures are logged. One INFO line per image load would be pure noise
    at household scale and carries no security signal; an unauthenticated hit
    on a private image does.
    """
    started = time.perf_counter()

    def _reject(reason: str, user_id: Optional[int] = None):
        emit_log_line(
            request,
            event="media_read",
            outcome="failure",
            reason=reason,
            user_id=user_id,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )
        # Same `private, no-store` the media route puts on 404/503. Cloudflare
        # caches by URL extension and these URLs end in .png/.jpg/.webp; 401
        # is not in the default cached-status table, but after CF Access
        # comes down this is the unauthenticated response for every private
        # image URL, and the header makes an edge-cached 401 structurally
        # impossible the same way it does for 404.
        exc = errors.unauthorized(reason)
        exc.headers = {"Cache-Control": "private, no-store"}
        return exc

    if not media_cookie:
        raise _reject("media_no_cookie")

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == tokens.hash_refresh_token(media_cookie)
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise _reject("media_unknown_cookie")

    # Named `session_status`, not `status`: `fastapi.status` is the conventional
    # import name in this codebase's route modules, and shadowing it in a
    # security check is how a future edit ends up comparing the wrong thing.
    session_status = tokens.refresh_row_status(row, datetime.now(timezone.utc))
    if session_status not in tokens.REFRESH_STATUS_SERVES:
        raise _reject(f"media_{session_status.value}", row.user_id)

    return row.user_id
