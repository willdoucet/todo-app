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

from typing import Optional

import jwt
from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import errors, tokens
from app.auth.models import User
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
