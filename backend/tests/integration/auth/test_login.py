"""Integration tests for ``POST /auth/login``."""

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.auth.models import RefreshToken
from app.auth.tokens import hash_refresh_token
from tests.integration.auth.conftest import TEST_HOUSEHOLD_ACCESS_KEY


@pytest.mark.asyncio
async def test_login_success_returns_token_and_cookie(client, register_user, caplog):
    await register_user(email="alice@example.com", password="hunter2-secure-pwd")
    caplog.set_level(logging.INFO, logger="app.auth")
    caplog.clear()

    r = await client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "hunter2-secure-pwd"},
    )
    assert r.status_code == 200
    assert "access_token" in r.json()
    assert "__Host-refresh" in r.cookies

    records = [r for r in caplog.records if r.name == "app.auth"]
    assert len(records) == 1
    assert records[0].event == "auth.login"
    assert records[0].outcome == "success"


@pytest.mark.asyncio
async def test_login_unknown_email_byte_identical_to_wrong_password(
    client, register_user, caplog
):
    await register_user(email="alice@example.com", password="known-password")
    caplog.set_level(logging.INFO, logger="app.auth")
    caplog.clear()

    unknown = await client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "any-password"},
    )
    wrong = await client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "wrong-password"},
    )

    assert unknown.status_code == wrong.status_code == 401
    assert unknown.content == wrong.content
    for h in ("date", "server"):
        unknown.headers.pop(h, None)
        wrong.headers.pop(h, None)
    assert dict(unknown.headers) == dict(wrong.headers)

    # BOTH log lines record reason=bad_credentials — no enumeration via logs.
    failed = [r for r in caplog.records if r.name == "app.auth" and r.outcome == "failed"]
    assert len(failed) == 2
    assert all(r.reason == "bad_credentials" for r in failed)


@pytest.mark.asyncio
async def test_login_overlong_password_byte_identical_to_wrong_password(
    client, register_user, caplog
):
    """Login password >128 chars → 401 invalid_credentials, NOT 422.
    Reason in log is bad_credentials, NOT password_too_long."""
    await register_user(email="alice@example.com", password="known-password")
    caplog.set_level(logging.INFO, logger="app.auth")
    caplog.clear()

    overlong = await client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "x" * 200},
    )
    wrong = await client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "wrong"},
    )

    assert overlong.status_code == wrong.status_code == 401
    assert overlong.content == wrong.content

    failed = [r for r in caplog.records if r.name == "app.auth" and r.outcome == "failed"]
    assert all(r.reason == "bad_credentials" for r in failed)


@pytest.mark.asyncio
async def test_login_calls_password_verify_even_for_unknown_email(
    client, register_user
):
    """Timing-oracle defense: verify_or_dummy MUST be called even when the
    user doesn't exist. Mock-spy asserts."""
    await register_user(email="alice@example.com", password="known-password")

    with patch("app.auth.service.passwords.verify_or_dummy", wraps=__import__("app.auth.passwords", fromlist=["verify_or_dummy"]).verify_or_dummy) as spy:
        r = await client.post(
            "/auth/login",
            json={"email": "nobody@example.com", "password": "any-password"},
        )
        assert r.status_code == 401
        spy.assert_called()  # verify_or_dummy called on unknown-email path


@pytest.mark.asyncio
async def test_login_same_client_rotation_revokes_only_that_row(
    client, register_user, db_session
):
    """If login arrives carrying its own refresh cookie, ONLY that one
    row is revoked. Other devices' rows stay live."""
    access_a, cookie_a, _ = await register_user("alice@example.com", "pwd-1234567890")

    # Simulate device B logging in fresh — gets its own row.
    cookies_b = (await client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "pwd-1234567890"},
    )).cookies
    cookie_b = cookies_b.get("__Host-refresh")

    # Now device A re-logs in WITH its own cookie. ONLY A's row should be revoked.
    client.cookies.set("__Host-refresh", cookie_a)
    relogin_a = await client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "pwd-1234567890"},
    )
    assert relogin_a.status_code == 200

    # DB state: row for cookie_a is revoked; row for cookie_b is NOT revoked.
    a_hash = hash_refresh_token(cookie_a)
    b_hash = hash_refresh_token(cookie_b)
    a_row = (
        await db_session.execute(select(RefreshToken).where(RefreshToken.token_hash == a_hash))
    ).scalar_one()
    b_row = (
        await db_session.execute(select(RefreshToken).where(RefreshToken.token_hash == b_hash))
    ).scalar_one()
    assert a_row.revoked_at is not None
    assert b_row.revoked_at is None


@pytest.mark.asyncio
async def test_login_without_cookie_does_not_mutate_other_rows(
    client, register_user, db_session
):
    """Login with NO incoming refresh cookie must not touch any
    refresh-token rows beyond inserting the new one."""
    await register_user("alice@example.com", "pwd-1234567890")

    # Capture all refresh rows before.
    before = (
        await db_session.execute(select(RefreshToken))
    ).scalars().all()
    before_revokes = {r.id: r.revoked_at for r in before}

    # Login without cookie.
    client.cookies.delete("__Host-refresh")
    r = await client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "pwd-1234567890"},
    )
    assert r.status_code == 200

    # The original rows still have the same revoked_at (None).
    after = (await db_session.execute(select(RefreshToken))).scalars().all()
    for row in after:
        if row.id in before_revokes:
            assert row.revoked_at == before_revokes[row.id]
