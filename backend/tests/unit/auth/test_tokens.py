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


# =============================================================================
# refresh_row_status — the shared session-validity predicate (M7 PR2, CQ1)
# =============================================================================
#
# This predicate is the single source of truth for "is this session valid?"
# across THREE consumers: service.refresh steps 2-4, service.refresh's Case-B
# terminal re-check, and the media read guard behind GET /uploads/{key}. The
# matrix below is what stops the image-read path from drifting away from the
# refresh path — a drift that would let a logged-out cookie keep loading
# private images.


class _Row:
    """Minimal stand-in for a RefreshToken row. The predicate is pure and
    touches only these three columns, so a real ORM row (and a DB) would add
    nothing but setup cost."""

    def __init__(self, *, revoked_at=None, expires_at=None, superseded_at=None):
        self.revoked_at = revoked_at
        self.expires_at = expires_at
        self.superseded_at = superseded_at


NOW = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
FUTURE = NOW + timedelta(days=30)
PAST = NOW - timedelta(seconds=1)
GRACE = timedelta(seconds=tokens.REFRESH_TOKEN_GRACE_SECONDS)


def test_live_row_is_live():
    row = _Row(expires_at=FUTURE)
    assert tokens.refresh_row_status(row, NOW) is tokens.RefreshStatus.LIVE


def test_revoked_row_is_revoked():
    row = _Row(revoked_at=PAST, expires_at=FUTURE)
    assert tokens.refresh_row_status(row, NOW) is tokens.RefreshStatus.REVOKED


def test_expired_row_is_expired():
    row = _Row(expires_at=PAST)
    assert tokens.refresh_row_status(row, NOW) is tokens.RefreshStatus.EXPIRED


def test_revoked_precedes_expired():
    """Check ORDER matters: service.refresh reports `bad_refresh_revoked` for a
    row that is both revoked and expired. If the predicate reordered these,
    that log reason would silently change."""
    row = _Row(revoked_at=PAST, expires_at=PAST)
    assert tokens.refresh_row_status(row, NOW) is tokens.RefreshStatus.REVOKED


def test_superseded_within_grace():
    row = _Row(expires_at=FUTURE, superseded_at=NOW - GRACE + timedelta(seconds=1))
    assert (
        tokens.refresh_row_status(row, NOW)
        is tokens.RefreshStatus.SUPERSEDED_IN_GRACE
    )


def test_superseded_exactly_at_grace_boundary_is_past_grace():
    """The window is half-open: `now < superseded_at + grace`. At exactly the
    boundary the row is PAST grace (matches service.refresh's Case C)."""
    row = _Row(expires_at=FUTURE, superseded_at=NOW - GRACE)
    assert (
        tokens.refresh_row_status(row, NOW)
        is tokens.RefreshStatus.SUPERSEDED_PAST_GRACE
    )


def test_superseded_past_grace():
    row = _Row(expires_at=FUTURE, superseded_at=NOW - GRACE - timedelta(seconds=1))
    assert (
        tokens.refresh_row_status(row, NOW)
        is tokens.RefreshStatus.SUPERSEDED_PAST_GRACE
    )


def test_revoked_precedes_superseded_in_grace():
    """A logout during the rotation grace window must reject, not serve."""
    row = _Row(revoked_at=PAST, expires_at=FUTURE, superseded_at=NOW)
    assert tokens.refresh_row_status(row, NOW) is tokens.RefreshStatus.REVOKED


def test_serves_set_is_exactly_live_and_in_grace():
    """The media read guard's allowlist. Adding a state here without thinking
    would hand image access to a dead session — hence an exact-equality
    assertion, not a membership check."""
    assert tokens.REFRESH_STATUS_SERVES == {
        tokens.RefreshStatus.LIVE,
        tokens.RefreshStatus.SUPERSEDED_IN_GRACE,
    }
    for dead in (
        tokens.RefreshStatus.REVOKED,
        tokens.RefreshStatus.EXPIRED,
        tokens.RefreshStatus.SUPERSEDED_PAST_GRACE,
    ):
        assert dead not in tokens.REFRESH_STATUS_SERVES


def test_naive_now_raises_rather_than_misclassifying():
    """Every compared column is DateTime(timezone=True). A naive `now` must
    blow up loudly instead of silently classifying a live row as expired."""
    row = _Row(expires_at=FUTURE)
    with pytest.raises(TypeError):
        tokens.refresh_row_status(row, datetime(2026, 7, 15, 12, 0, 0))
