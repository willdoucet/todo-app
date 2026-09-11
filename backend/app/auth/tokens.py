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
from enum import Enum
from typing import TYPE_CHECKING, Any

import jwt

from app.auth.config import get_settings

if TYPE_CHECKING:  # pragma: no cover - typing only
    # Annotation only: keeps this module free of a runtime model import so the
    # predicate stays pure and importable from anywhere in the auth package.
    from app.auth.models import RefreshToken

# Locked architecture (contract-freeze):
#  - 15-minute access TTL
#  - 30-day refresh TTL
#  - 60-second rotation grace window
#  - HS256
ACCESS_TOKEN_TTL_SECONDS = 15 * 60
REFRESH_TOKEN_TTL_DAYS = 30
REFRESH_TOKEN_GRACE_SECONDS = 60
JWT_ALGORITHM = "HS256"

# The refresh cookie's name. Defined here rather than in `routes.py` because
# two packages need it: the auth routes that set/clear it, and the M7 PR2
# media read guard in `dependencies.py`. `routes.py` imports `dependencies.py`,
# so the constant cannot live in `routes.py` without an import cycle.
# `__Host-` prefix requires Secure + Path=/ + no Domain (enforced at set time).
REFRESH_COOKIE_NAME = "__Host-refresh"


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


class RefreshStatus(Enum):
    """The five terminal states of a ``refresh_tokens`` row at a point in time.

    Extracted in M7 PR2 (eng review CQ1). Before this, "is this session
    valid?" existed only inline in :func:`app.auth.service.refresh`. PR2 adds
    a SECOND consumer — the media read guard behind ``GET /uploads/{key}`` —
    and a security predicate duplicated across two call sites drifts, silently
    re-opening the hole M7 exists to close. One function, two consumers:

      - ``service.refresh`` branches on it: ``LIVE`` → Case A (rotate),
        ``SUPERSEDED_IN_GRACE`` → Case B (walk successors), anything else →
        reject. Row locking and rotation stay in ``service.refresh``; only the
        pure predicate is shared.
      - the media read guard serves for :data:`REFRESH_STATUS_SERVES` and 401s
        otherwise. It does NOT rotate.

    ``SUPERSEDED_PAST_GRACE`` is a rejection, not a pass: without it a
    rotated-away cookie would authorize image reads for its full 30-day TTL
    even though it can no longer refresh.
    """

    LIVE = "live"
    REVOKED = "revoked"
    EXPIRED = "expired"
    SUPERSEDED_IN_GRACE = "superseded_in_grace"
    SUPERSEDED_PAST_GRACE = "superseded_past_grace"


#: Statuses that count as "this session may read". The media read guard treats
#: membership as serve and everything else as 401. In-grace is included so a
#: page mid-rotation does not flash broken images for up to 60 seconds.
REFRESH_STATUS_SERVES = frozenset(
    {RefreshStatus.LIVE, RefreshStatus.SUPERSEDED_IN_GRACE}
)


def refresh_row_status(row: "RefreshToken", now: datetime) -> RefreshStatus:
    """Classify a refresh-token row. Pure: no DB, no I/O, no mutation.

    ``now`` MUST be timezone-aware — every compared column is
    ``DateTime(timezone=True)``, so a naive ``now`` raises ``TypeError`` on
    the first comparison rather than silently mis-classifying.

    Check order mirrors ``service.refresh`` exactly (revoked → expired →
    superseded branch), so the reason strings that route logs are unchanged.
    """
    if row.revoked_at is not None:
        return RefreshStatus.REVOKED
    if row.expires_at < now:
        return RefreshStatus.EXPIRED
    if row.superseded_at is None:
        return RefreshStatus.LIVE
    if now < row.superseded_at + timedelta(seconds=REFRESH_TOKEN_GRACE_SECONDS):
        return RefreshStatus.SUPERSEDED_IN_GRACE
    return RefreshStatus.SUPERSEDED_PAST_GRACE
