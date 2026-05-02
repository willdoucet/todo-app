"""Unit tests for app.auth.dependencies.validate_bearer.

Covers:
- Missing Authorization header
- Non-Bearer scheme / malformed header
- Empty bearer value
- Each of the 4 PyJWT exception classes
- Malformed claim shapes (missing/non-int sub, missing/non-int session_version)
- User row deleted between issue and use
- Stale session_version
- Live valid case
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest
from fastapi import HTTPException

from app.auth import config as auth_config
from app.auth import tokens
from app.auth.dependencies import validate_bearer
from app.auth.models import User


@pytest.fixture(autouse=True)
def install_test_settings():
    test_cfg = auth_config.AuthConfig(
        jwt_secret_key="x" * 64,
        household_access_key="dev-access-key",
    )
    auth_config.configure(test_cfg)
    yield
    auth_config.reset()


@pytest.fixture
def db_returning(monkeypatch):
    """Factory that returns a mock AsyncSession whose execute() yields a
    result whose scalar_one_or_none returns the supplied object."""

    def _make(obj):
        db = MagicMock()
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=obj)
        db.execute = AsyncMock(return_value=result)
        return db

    return _make


def _user(id: int = 1, session_version: int = 0) -> User:
    return User(
        id=id, email="u@x.com", password_hash="phc", session_version=session_version
    )


def _raise(exc_type):
    def _f(*args, **kwargs):
        raise exc_type("forced")
    return _f


async def _expect_401(coro):
    with pytest.raises(HTTPException) as exc_info:
        await coro
    assert exc_info.value.status_code == 401


# =============================================================================
# Header presence / shape
# =============================================================================

@pytest.mark.asyncio
async def test_missing_authorization_header(db_returning):
    db = db_returning(_user())
    await _expect_401(validate_bearer(None, db))


@pytest.mark.asyncio
async def test_empty_authorization_header(db_returning):
    db = db_returning(_user())
    await _expect_401(validate_bearer("", db))


@pytest.mark.asyncio
async def test_non_bearer_scheme_rejected(db_returning):
    db = db_returning(_user())
    await _expect_401(validate_bearer("Basic abc123", db))


@pytest.mark.asyncio
async def test_bearer_without_value_rejected(db_returning):
    db = db_returning(_user())
    await _expect_401(validate_bearer("Bearer ", db))


@pytest.mark.asyncio
async def test_bearer_with_only_whitespace_rejected(db_returning):
    db = db_returning(_user())
    await _expect_401(validate_bearer("Bearer    ", db))


# =============================================================================
# PyJWT exception coverage (Eng review 1) — all 4 must 401
# =============================================================================

@pytest.mark.asyncio
async def test_expired_signature_error_401(db_returning, monkeypatch):
    db = db_returning(_user())
    monkeypatch.setattr(
        "app.auth.dependencies.tokens.decode_access_token",
        _raise(jwt.ExpiredSignatureError),
    )
    await _expect_401(validate_bearer("Bearer abc", db))


@pytest.mark.asyncio
async def test_invalid_signature_error_401(db_returning, monkeypatch):
    db = db_returning(_user())
    monkeypatch.setattr(
        "app.auth.dependencies.tokens.decode_access_token",
        _raise(jwt.InvalidSignatureError),
    )
    await _expect_401(validate_bearer("Bearer abc", db))


@pytest.mark.asyncio
async def test_decode_error_401(db_returning, monkeypatch):
    db = db_returning(_user())
    monkeypatch.setattr(
        "app.auth.dependencies.tokens.decode_access_token",
        _raise(jwt.DecodeError),
    )
    await _expect_401(validate_bearer("Bearer abc", db))


@pytest.mark.asyncio
async def test_invalid_token_error_401(db_returning, monkeypatch):
    """Catch-all: a non-specific InvalidTokenError subclass must also 401."""
    db = db_returning(_user())
    monkeypatch.setattr(
        "app.auth.dependencies.tokens.decode_access_token",
        _raise(jwt.ImmatureSignatureError),
    )
    await _expect_401(validate_bearer("Bearer abc", db))


# =============================================================================
# Malformed claim coverage (Adversarial review)
# =============================================================================

def _payload(**overrides):
    """Build a base payload and override individual fields."""
    base = {
        "sub": "1",
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=10)).timestamp()),
        "session_version": 0,
    }
    base.update(overrides)
    return base


def _encode(payload: dict) -> str:
    return jwt.encode(
        payload,
        auth_config.get_settings().jwt_secret_key,
        algorithm=tokens.JWT_ALGORITHM,
    )


@pytest.mark.asyncio
async def test_missing_sub_claim_401(db_returning):
    db = db_returning(_user())
    p = _payload()
    del p["sub"]
    token = _encode(p)
    await _expect_401(validate_bearer(f"Bearer {token}", db))


@pytest.mark.asyncio
async def test_non_integer_sub_claim_401(db_returning):
    db = db_returning(_user())
    token = _encode(_payload(sub="not-an-int"))
    await _expect_401(validate_bearer(f"Bearer {token}", db))


@pytest.mark.asyncio
async def test_negative_sub_claim_401(db_returning):
    db = db_returning(_user())
    token = _encode(_payload(sub="-1"))
    await _expect_401(validate_bearer(f"Bearer {token}", db))


@pytest.mark.asyncio
async def test_missing_session_version_claim_401(db_returning):
    db = db_returning(_user())
    p = _payload()
    del p["session_version"]
    token = _encode(p)
    await _expect_401(validate_bearer(f"Bearer {token}", db))


@pytest.mark.asyncio
async def test_non_integer_session_version_claim_401(db_returning):
    db = db_returning(_user())
    token = _encode(_payload(session_version="not-an-int"))
    await _expect_401(validate_bearer(f"Bearer {token}", db))


@pytest.mark.asyncio
async def test_bool_session_version_claim_401(db_returning):
    """Python bool is a subclass of int — must NOT pass as session_version."""
    db = db_returning(_user())
    token = _encode(_payload(session_version=True))
    await _expect_401(validate_bearer(f"Bearer {token}", db))


# =============================================================================
# DB-side rejections
# =============================================================================

@pytest.mark.asyncio
async def test_user_row_deleted_between_issue_and_use_401(db_returning):
    """User row gone (operator deleted singleton, or never existed)."""
    db = db_returning(None)
    token = _encode(_payload(sub="1", session_version=0))
    await _expect_401(validate_bearer(f"Bearer {token}", db))


@pytest.mark.asyncio
async def test_stale_session_version_401(db_returning):
    """Operator rotated password — token's session_version is older than DB."""
    db = db_returning(_user(id=1, session_version=5))
    token = _encode(_payload(sub="1", session_version=4))
    await _expect_401(validate_bearer(f"Bearer {token}", db))


# =============================================================================
# Happy path
# =============================================================================

@pytest.mark.asyncio
async def test_valid_token_returns_user(db_returning):
    user = _user(id=42, session_version=3)
    db = db_returning(user)
    token = _encode(_payload(sub="42", session_version=3))
    result = await validate_bearer(f"Bearer {token}", db)
    assert result is user
