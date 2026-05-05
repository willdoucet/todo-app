"""Integration tests for ``POST /auth/logout``."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from sqlalchemy import select

from app.auth import config as auth_config
from app.auth import tokens
from app.auth.models import RefreshToken, User


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_logout_success_revokes_all_active_refresh_rows(
    client, register_user, db_session, caplog
):
    access, _, _ = await register_user("alice@example.com", "pwd-1234567890")
    caplog.set_level(logging.INFO, logger="app.auth")
    caplog.clear()

    r = await client.post("/auth/logout", headers=_bearer(access))
    assert r.status_code == 204

    # All refresh rows for this user are revoked.
    rows = (await db_session.execute(select(RefreshToken))).scalars().all()
    assert all(row.revoked_at is not None for row in rows), (
        f"expected all rows revoked, got {[(r.id, r.revoked_at) for r in rows]}"
    )

    records = [r for r in caplog.records if r.name == "app.auth"]
    assert len(records) == 1
    assert records[0].outcome == "success"
    assert records[0].event == "auth.logout"


@pytest.mark.asyncio
async def test_logout_clears_cookie_with_correct_attributes(client, register_user):
    access, _, _ = await register_user("alice@example.com", "pwd-1234567890")
    r = await client.post("/auth/logout", headers=_bearer(access))
    assert r.status_code == 204

    set_cookie = r.headers.get("set-cookie", "")
    # Cookie clearing attribute set (Adversarial review run 2).
    assert "__Host-refresh=" in set_cookie
    assert "Path=/" in set_cookie
    assert "Secure" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=strict" in set_cookie
    assert "Domain=" not in set_cookie
    # Either Max-Age=0 or expires-in-the-past.
    assert ("Max-Age=0" in set_cookie) or ("expires=" in set_cookie.lower())


@pytest.mark.asyncio
async def test_logout_bumps_session_version_so_old_access_token_is_dead(
    client, register_user, db_session
):
    access, _, _ = await register_user("alice@example.com", "pwd-1234567890")

    r = await client.post("/auth/logout", headers=_bearer(access))
    assert r.status_code == 204

    user = (await db_session.execute(select(User))).scalar_one()
    assert user.session_version == 1

    # The same access token must no longer validate after logout. This is the
    # server-side backstop for stale tabs that have not yet heard about logout.
    second = await client.post("/auth/logout", headers=_bearer(access))
    assert second.status_code == 401


@pytest.mark.asyncio
async def test_logout_without_bearer_returns_401(client, register_user, caplog):
    """CSRF defense — a cookie alone is not enough to logout."""
    await register_user("alice@example.com", "pwd-1234567890")
    caplog.set_level(logging.INFO, logger="app.auth")
    caplog.clear()
    r = await client.post("/auth/logout")
    assert r.status_code == 401

    failed = [r for r in caplog.records if r.name == "app.auth" and r.outcome == "failed"]
    assert len(failed) == 1
    assert failed[0].event == "auth.logout"


@pytest.mark.asyncio
async def test_logout_with_non_bearer_scheme_returns_401(client, register_user):
    await register_user("alice@example.com", "pwd-1234567890")
    r = await client.post(
        "/auth/logout", headers={"Authorization": "Basic abc123"}
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_logout_with_expired_bearer_returns_401(client, register_user):
    await register_user("alice@example.com", "pwd-1234567890")
    cfg = auth_config.get_settings()
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    expired_payload = {
        "sub": "1",
        "iat": int(past.timestamp()),
        "exp": int((past + timedelta(seconds=60)).timestamp()),
        "session_version": 0,
    }
    expired_token = jwt.encode(
        expired_payload, cfg.jwt_secret_key, algorithm=tokens.JWT_ALGORITHM
    )
    r = await client.post("/auth/logout", headers=_bearer(expired_token))
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_logout_with_stale_bearer_after_rotation_does_not_revoke_new_token(
    client, register_user, db_session
):
    """Adversarial review run 2: stale-token mutation guard.

    Workflow:
    - Register → get access JWT (sv=0) + cookie A.
    - Simulate operator password rotation: bump session_version to 1, revoke cookie A.
    - User logs in fresh → gets new access JWT (sv=1) + cookie B (revoked_at=NULL).
    - Attacker sends the OLD access JWT (sv=0) to /auth/logout.
    - Server must 401 AND must NOT revoke the freshly-issued cookie B's row.
    """
    pre_access, cookie_a, _ = await register_user("alice@example.com", "pwd-1234567890")

    # Bump session_version + revoke cookie A (simulating password rotation).
    user = (await db_session.execute(select(User))).scalar_one()
    user.session_version = 1
    a_hash = tokens.hash_refresh_token(cookie_a)
    a_row = (
        await db_session.execute(select(RefreshToken).where(RefreshToken.token_hash == a_hash))
    ).scalar_one()
    a_row.revoked_at = datetime.now(timezone.utc)
    await db_session.commit()

    # User logs in fresh — gets new access JWT (sv=1) + cookie B.
    client.cookies.delete("__Host-refresh")
    relogin = await client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "pwd-1234567890"},
    )
    assert relogin.status_code == 200
    cookie_b = relogin.cookies.get("__Host-refresh")
    b_hash = tokens.hash_refresh_token(cookie_b)

    # Attacker sends the OLD access JWT to logout.
    r = await client.post("/auth/logout", headers=_bearer(pre_access))
    assert r.status_code == 401

    # Cookie B's row was NOT revoked by the failed logout.
    await db_session.commit()  # close any pending tx
    b_row = (
        await db_session.execute(select(RefreshToken).where(RefreshToken.token_hash == b_hash))
    ).scalar_one()
    assert b_row.revoked_at is None, "stale logout must not revoke fresh sessions"


@pytest.mark.asyncio
async def test_logout_revokes_refresh_tokens_on_other_devices(
    client, register_user, db_session
):
    """Concurrent-device case: logout from device A revokes device B's
    refresh row at the DB level too (logout revokes ALL active rows)."""
    access_a, cookie_a, _ = await register_user("alice@example.com", "pwd-1234567890")

    # Simulate device B login.
    relogin = await client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "pwd-1234567890"},
    )
    cookie_b = relogin.cookies.get("__Host-refresh")
    b_hash = tokens.hash_refresh_token(cookie_b)

    # A logs out.
    r = await client.post("/auth/logout", headers=_bearer(access_a))
    assert r.status_code == 204

    # B's row is now revoked.
    await db_session.commit()
    b_row = (
        await db_session.execute(select(RefreshToken).where(RefreshToken.token_hash == b_hash))
    ).scalar_one()
    assert b_row.revoked_at is not None
