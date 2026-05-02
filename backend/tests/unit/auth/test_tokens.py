"""Unit tests for app.auth.tokens — JWT roundtrip + refresh-token helpers."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.auth import config as auth_config
from app.auth import tokens


@pytest.fixture(autouse=True)
def install_test_settings():
    """Install dev-test config without reading env."""
    test_cfg = auth_config.AuthConfig(
        jwt_secret_key="x" * 64,  # 64-char string with no placeholder substring
        household_access_key="dev-access-key",
    )
    auth_config.configure(test_cfg)
    yield
    auth_config.reset()


# =============================================================================
# Access token JWT roundtrip
# =============================================================================

def test_access_token_encode_decode_roundtrip():
    token = tokens.encode_access_token(user_id=42, session_version=3)
    payload = tokens.decode_access_token(token)
    assert payload["sub"] == "42"  # JWT spec: sub is a string
    assert payload["session_version"] == 3
    assert payload["exp"] - payload["iat"] == tokens.ACCESS_TOKEN_TTL_SECONDS


def test_access_token_sub_is_string_per_jwt_spec():
    token = tokens.encode_access_token(user_id=1, session_version=0)
    payload = tokens.decode_access_token(token)
    assert isinstance(payload["sub"], str)


def test_decode_expired_token_raises():
    cfg = auth_config.get_settings()
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    payload = {
        "sub": "1",
        "iat": int(past.timestamp()),
        # Already expired by the time the test executes.
        "exp": int((past + timedelta(seconds=60)).timestamp()),
        "session_version": 0,
    }
    expired = jwt.encode(
        payload, cfg.jwt_secret_key, algorithm=tokens.JWT_ALGORITHM
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        tokens.decode_access_token(expired)


def test_decode_with_wrong_signature_raises():
    """A token signed with a different secret fails signature verification."""
    payload = {
        "sub": "1",
        "iat": 0,
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp()),
        "session_version": 0,
    }
    wrong_key = "y" * 64
    wrong = jwt.encode(payload, wrong_key, algorithm=tokens.JWT_ALGORITHM)
    with pytest.raises(jwt.InvalidSignatureError):
        tokens.decode_access_token(wrong)


def test_decode_garbage_raises_decode_error():
    with pytest.raises(jwt.DecodeError):
        tokens.decode_access_token("not.a.jwt")


# =============================================================================
# Refresh token helpers
# =============================================================================

def test_generate_refresh_token_returns_plaintext_and_sha256():
    plaintext, h = tokens.generate_refresh_token()
    assert isinstance(plaintext, str)
    assert isinstance(h, bytes)
    assert len(h) == 32  # sha256 = 32 bytes


def test_hash_refresh_token_is_deterministic():
    h1 = tokens.hash_refresh_token("the-same-value")
    h2 = tokens.hash_refresh_token("the-same-value")
    assert h1 == h2
    assert len(h1) == 32


def test_generate_refresh_token_yields_distinct_values():
    """secrets.token_urlsafe(32) is 256 bits of entropy. 100 generations
    must all be distinct."""
    seen: set[str] = set()
    for _ in range(100):
        plaintext, _ = tokens.generate_refresh_token()
        assert plaintext not in seen, "refresh token plaintexts must be unique"
        seen.add(plaintext)


def test_hash_of_generated_plaintext_matches_returned_hash():
    plaintext, h = tokens.generate_refresh_token()
    assert tokens.hash_refresh_token(plaintext) == h
