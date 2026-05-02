"""Log hygiene: secrets, password hashes, and refresh-token plaintext
must NEVER appear in any caplog record produced during the integration
suite. Verified via regex scan (test artifact §Operational Invariants)."""

from __future__ import annotations

import logging
import re

import pytest

from app.auth.tokens import hash_refresh_token
from tests.integration.auth.conftest import (
    TEST_HOUSEHOLD_ACCESS_KEY,
    TEST_JWT_SECRET_KEY,
)


# Patterns that should NEVER appear in any record.
def _record_strings(record: logging.LogRecord) -> list[str]:
    """Stringify everything attached to the record so the scan doesn't
    miss values lurking in `extra` keys."""
    parts = [str(record.getMessage())]
    for key, value in record.__dict__.items():
        # Skip standard LogRecord attrs that legitimately contain non-secret data.
        if key in {
            "args",
            "msg",
            "name",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "message",
            "asctime",
            "taskName",
        }:
            continue
        if value is not None:
            parts.append(repr(value))
    return parts


def _scan_for(records, *forbidden):
    for record in records:
        s = " ".join(_record_strings(record))
        for pat in forbidden:
            assert pat not in s, (
                f"Forbidden value {pat!r} leaked into log record: {s!r}"
            )


@pytest.mark.asyncio
async def test_register_log_does_not_leak_password_hash_or_token(
    client, register_user, caplog
):
    caplog.set_level(logging.DEBUG)
    access, cookie, _ = await register_user(
        "alice@example.com", "correct-horse-battery-staple"
    )

    auth_records = [r for r in caplog.records if r.name == "app.auth"]
    _scan_for(
        auth_records,
        "correct-horse-battery-staple",  # plaintext password
        cookie,  # refresh-token plaintext
        access,  # access JWT
        TEST_HOUSEHOLD_ACCESS_KEY,  # access key
        TEST_JWT_SECRET_KEY,  # JWT signing secret
    )

    # SHA-256 hash of the cookie also forbidden (hex form).
    cookie_hash_hex = hash_refresh_token(cookie).hex()
    _scan_for(auth_records, cookie_hash_hex)

    # Argon2 PHC string starts with "$argon2" — make sure no record contains it.
    for r in auth_records:
        s = " ".join(_record_strings(r))
        assert "$argon2" not in s, f"argon2 hash leaked into log: {s!r}"


@pytest.mark.asyncio
async def test_login_failure_log_does_not_leak_password(client, register_user, caplog):
    await register_user("alice@example.com", "the-real-password")
    caplog.set_level(logging.DEBUG)
    caplog.clear()

    r = await client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "wrong-password-attempt"},
    )
    assert r.status_code == 401

    records = [r for r in caplog.records if r.name == "app.auth"]
    _scan_for(records, "the-real-password", "wrong-password-attempt")


@pytest.mark.asyncio
async def test_refresh_log_does_not_leak_cookie_value(client, register_user, caplog):
    _, cookie, _ = await register_user("alice@example.com", "pwd-1234567890")
    caplog.set_level(logging.DEBUG)
    caplog.clear()

    client.cookies.set("__Host-refresh", cookie)
    r = await client.post("/auth/refresh")
    assert r.status_code == 200
    new_cookie = r.cookies.get("__Host-refresh")

    records = [r for r in caplog.records if r.name == "app.auth"]
    _scan_for(records, cookie, new_cookie)


@pytest.mark.asyncio
async def test_chain_corrupt_log_does_not_leak_cookie_or_hashes(
    client, register_user, caplog, db_session
):
    """The bad_refresh_chain warning path must not log the cookie value
    or the row's token_hash bytes."""
    from datetime import datetime, timezone
    from sqlalchemy import select

    from app.auth.models import RefreshToken

    _, cookie, _ = await register_user("alice@example.com", "pwd-1234567890")

    # Manufacture a self-cycle.
    h = hash_refresh_token(cookie)
    row = (
        await db_session.execute(select(RefreshToken).where(RefreshToken.token_hash == h))
    ).scalar_one()
    row.superseded_at = datetime.now(timezone.utc)
    row.successor_id = row.id
    await db_session.commit()

    caplog.set_level(logging.DEBUG)
    caplog.clear()

    client.cookies.set("__Host-refresh", cookie)
    r = await client.post("/auth/refresh")
    assert r.status_code == 401

    records = [r for r in caplog.records if r.name == "app.auth"]
    _scan_for(records, cookie, h.hex())
