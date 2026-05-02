"""End-to-end auth flow (Eng review 3).

Walks through the canonical Definition-of-Done sequence from the
test artifact: register → status → duplicate-rejected → login → refresh
→ logout → refresh-rejected → multi-device path.

If any step doesn't behave as specified, M3 isn't done.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from sqlalchemy import select

from app.auth import config as auth_config
from app.auth import tokens
from app.auth.models import RefreshToken, User
from tests.integration.auth.conftest import TEST_HOUSEHOLD_ACCESS_KEY


@pytest.mark.asyncio
async def test_full_e2e_register_login_refresh_logout(client, db_session):
    # ---- Step 1: status reports no account.
    r = await client.get("/auth/status")
    assert r.json() == {"account_exists": False}

    # ---- Step 2: register the singleton.
    r = await client.post(
        "/auth/register",
        json={
            "email": "alice@example.com",
            "password": "correct-horse-battery-staple",
            "access_key": TEST_HOUSEHOLD_ACCESS_KEY,
        },
    )
    assert r.status_code == 200
    register_access = r.json()["access_token"]
    register_cookie = r.cookies.get("__Host-refresh")

    # Access JWT decodes with session_version=0.
    payload = tokens.decode_access_token(register_access)
    assert payload["session_version"] == 0
    assert payload["sub"] == "1"

    # ---- Step 3: status now reports the account exists.
    r = await client.get("/auth/status")
    assert r.json() == {"account_exists": True}

    # ---- Step 4: duplicate register rejected with byte-identical body.
    r = await client.post(
        "/auth/register",
        json={
            "email": "elsewhere@example.com",
            "password": "another-strong-pw",
            "access_key": TEST_HOUSEHOLD_ACCESS_KEY,
        },
    )
    assert r.status_code == 401
    assert r.json() == {"detail": "registration_unavailable"}

    # ---- Step 5: login with correct creds returns fresh cookie.
    client.cookies.delete("__Host-refresh")
    r = await client.post(
        "/auth/login",
        json={
            "email": "alice@example.com",
            "password": "correct-horse-battery-staple",
        },
    )
    assert r.status_code == 200
    login_access = r.json()["access_token"]
    login_cookie = r.cookies.get("__Host-refresh")
    assert login_cookie is not None
    assert login_cookie != register_cookie

    # ---- Step 6: refresh with login cookie → Case A → new cookie.
    client.cookies.set("__Host-refresh", login_cookie)
    r = await client.post("/auth/refresh")
    assert r.status_code == 200
    refresh_access = r.json()["access_token"]
    refresh_cookie = r.cookies.get("__Host-refresh")
    assert refresh_cookie is not None
    assert refresh_cookie != login_cookie

    # Access JWT still session_version=0.
    assert tokens.decode_access_token(refresh_access)["session_version"] == 0

    # ---- Step 7: logout with the latest bearer.
    r = await client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {refresh_access}"},
    )
    assert r.status_code == 204

    # ---- Step 8: refresh with the now-revoked cookie → 401 refresh_failed.
    client.cookies.set("__Host-refresh", refresh_cookie)
    r = await client.post("/auth/refresh")
    assert r.status_code == 401
    assert r.json() == {"detail": "refresh_failed"}

    # All refresh rows should be revoked.
    rows = (await db_session.execute(select(RefreshToken))).scalars().all()
    assert all(row.revoked_at is not None for row in rows)


@pytest.mark.asyncio
async def test_multi_device_household_path(client, db_session):
    """Adversarial review path: device B login does NOT revoke device A's
    cookie. Only same-client rotation revokes."""
    # Register on device A.
    r = await client.post(
        "/auth/register",
        json={
            "email": "alice@example.com",
            "password": "pwd-1234567890",
            "access_key": TEST_HOUSEHOLD_ACCESS_KEY,
        },
    )
    cookie_a = r.cookies.get("__Host-refresh")

    # Login on device B (no incoming cookie).
    client.cookies.delete("__Host-refresh")
    r = await client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "pwd-1234567890"},
    )
    cookie_b = r.cookies.get("__Host-refresh")
    assert cookie_b != cookie_a

    # Device A can still refresh successfully.
    client.cookies.set("__Host-refresh", cookie_a)
    r = await client.post("/auth/refresh")
    assert r.status_code == 200, "device A's cookie must still refresh after B logs in"


@pytest.mark.asyncio
async def test_simulated_password_rotation_invalidates_old_tokens(
    client, db_session
):
    """Operator password rotation: bumps session_version + revokes all
    refresh rows. Old access JWT fails the dependency check, old refresh
    cookie 401s on /auth/refresh."""
    # Register.
    r = await client.post(
        "/auth/register",
        json={
            "email": "alice@example.com",
            "password": "pwd-1234567890",
            "access_key": TEST_HOUSEHOLD_ACCESS_KEY,
        },
    )
    pre_access = r.json()["access_token"]
    pre_cookie = r.cookies.get("__Host-refresh")

    # Simulate rotation.
    user = (await db_session.execute(select(User))).scalar_one()
    user.session_version = 1
    rows = (await db_session.execute(select(RefreshToken))).scalars().all()
    for row in rows:
        row.revoked_at = datetime.now(timezone.utc)
    await db_session.commit()

    # Pre-rotation refresh cookie → 401.
    client.cookies.set("__Host-refresh", pre_cookie)
    r = await client.post("/auth/refresh")
    assert r.status_code == 401

    # Pre-rotation access token → logout returns 401 via session_version mismatch.
    r = await client.post(
        "/auth/logout", headers={"Authorization": f"Bearer {pre_access}"}
    )
    assert r.status_code == 401
