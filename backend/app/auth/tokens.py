"""JWT access tokens + opaque refresh tokens.

Access tokens are HS256 JWTs carrying ``{sub, iat, exp, session_version}``.
Refresh tokens are NOT JWTs — they are opaque ``secrets.token_urlsafe(32)``
strings. Their identity in the database is the 32-byte SHA-256 hash row in
``refresh_tokens``; the plaintext lives only in the ``__Host-refresh``
cookie and is never persisted.

JWT secrets are read through :func:`app.auth.config.get_settings` so tests
can install dev-only values via ``configure()`` without touching env.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.auth.config import get_settings

# Locked architecture (contract-freeze):
#  - 15-minute access TTL
#  - 30-day refresh TTL
#  - 60-second rotation grace window
#  - HS256
ACCESS_TOKEN_TTL_SECONDS = 15 * 60
REFRESH_TOKEN_TTL_DAYS = 30
REFRESH_TOKEN_GRACE_SECONDS = 60
JWT_ALGORITHM = "HS256"


def encode_access_token(user_id: int, session_version: int) -> str:
    """Mint an access JWT. Caller passes the user's *current*
    ``session_version`` at issue time. The dependency check compares the
    claim against the live DB value on every protected request, so any
    rotation since issue time fails 401.
    """
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        # JWT spec: sub MUST be a string.
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ACCESS_TOKEN_TTL_SECONDS)).timestamp()),
        "session_version": session_version,
    }
    return jwt.encode(payload, get_settings().jwt_secret_key, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and verify exp. PyJWT raises one of:

    - :class:`jwt.ExpiredSignatureError` (exp passed)
    - :class:`jwt.InvalidSignatureError` (signature mismatch)
    - :class:`jwt.DecodeError` (malformed)
    - :class:`jwt.InvalidTokenError` (anything else)

    All four collapse to 401 in :func:`app.auth.dependencies.get_current_user`;
    the dependency assigns the categorical reason in the structured log line.
    """
    return jwt.decode(
        token, get_settings().jwt_secret_key, algorithms=[JWT_ALGORITHM]
    )


def generate_refresh_token() -> tuple[str, bytes]:
    """Mint a fresh refresh-token plaintext + its SHA-256 hash.

    The plaintext goes in the ``__Host-refresh`` cookie. The hash is
    inserted into ``refresh_tokens.token_hash``. ``secrets.token_urlsafe(32)``
    is 32 bytes of CSPRNG output, base64-url-encoded into ~43 chars.
    """
    plaintext = secrets.token_urlsafe(32)
    return plaintext, hash_refresh_token(plaintext)


def hash_refresh_token(plaintext: str) -> bytes:
    """SHA-256 over the cookie value's UTF-8 bytes. Always 32 bytes."""
    return hashlib.sha256(plaintext.encode("utf-8")).digest()
