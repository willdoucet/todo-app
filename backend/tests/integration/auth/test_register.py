"""Integration tests for ``POST /auth/register``.

Covers:
- Success → user row, refresh cookie, access token.
- Wrong access key → byte-identical 401.
- Account already exists → byte-identical 401.
- Concurrent register race (different valid emails) → exactly one wins.
- Password > 128 chars → 422 (Pydantic body validation).
- ``hmac.compare_digest`` is the access-key compare primitive (source-grep).
"""

from __future__ import annotations

import asyncio
import logging

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import RefreshToken, User
from tests.integration.auth.conftest import (
    TEST_HOUSEHOLD_ACCESS_KEY,
)


@pytest.mark.asyncio
async def test_register_success_returns_token_and_cookie(
    client, db_session, caplog
):
    caplog.set_level(logging.INFO, logger="app.auth")
    r = await client.post(
        "/auth/register",
        json={
            "email": "primary@example.com",
            "password": "correct-horse-battery-staple",
            "access_key": TEST_HOUSEHOLD_ACCESS_KEY,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert "__Host-refresh" in r.cookies

    # Cookie attribute set: HttpOnly, Secure, SameSite=lax, Path=/.
    set_cookie = r.headers.get("set-cookie", "")
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "Path=/" in set_cookie
    # __Host- prefix forbids Domain — must NOT appear.
    assert "Domain=" not in set_cookie

    # DB state: exactly one user, one refresh token row.
    n = await db_session.execute(select(func.count()).select_from(User))
    assert n.scalar_one() == 1
    user = (
        await db_session.execute(select(User).where(User.email == "primary@example.com"))
    ).scalar_one()
    assert user.session_version == 0
    rts = (
        await db_session.execute(select(RefreshToken).where(RefreshToken.user_id == user.id))
    ).scalars().all()
    assert len(rts) == 1
    assert rts[0].revoked_at is None
    assert rts[0].superseded_at is None

    # Log line.
    records = [r for r in caplog.records if r.name == "app.auth" and r.event == "auth.register"]
    assert len(records) == 1
    assert records[0].outcome == "success"
    assert records[0].user_id == user.id


@pytest.mark.asyncio
async def test_register_wrong_access_key_byte_identical(client, caplog):
    caplog.set_level(logging.INFO, logger="app.auth")
    r = await client.post(
        "/auth/register",
        json={
            "email": "u@example.com",
            "password": "hunter2-something-long-enough",
            "access_key": "this-is-not-the-right-key",
        },
    )
    assert r.status_code == 401
    assert r.json() == {"detail": "registration_unavailable"}

    records = [r for r in caplog.records if r.name == "app.auth"]
    assert len(records) == 1
    assert records[0].outcome == "failed"
    assert records[0].reason == "bad_access_key"


@pytest.mark.asyncio
async def test_register_already_exists_byte_identical(
    client, register_user, caplog
):
    """Second register with right key but account already claimed → same body."""
    # First register.
    _, _, first = await register_user("a@example.com")
    caplog.set_level(logging.INFO, logger="app.auth")
    caplog.clear()

    # Wrong-key response (for byte-identicality comparison).
    wrong = await client.post(
        "/auth/register",
        json={
            "email": "b@example.com",
            "password": "another-strong-password",
            "access_key": "wrong-key",
        },
    )

    # Account-exists response.
    duplicate = await client.post(
        "/auth/register",
        json={
            "email": "c@example.com",
            "password": "another-strong-password",
            "access_key": TEST_HOUSEHOLD_ACCESS_KEY,
        },
    )

    assert wrong.status_code == duplicate.status_code == 401
    assert wrong.content == duplicate.content
    # Strip headers that legitimately vary (Date, Server) before comparing.
    for h in ("date", "server"):
        wrong.headers.pop(h, None)
        duplicate.headers.pop(h, None)
    assert dict(wrong.headers) == dict(duplicate.headers)

    # Log lines: bad_access_key for the first, account_exists for the second.
    failed = [r for r in caplog.records if r.name == "app.auth" and r.outcome == "failed"]
    reasons = sorted(r.reason for r in failed)
    assert reasons == ["account_exists", "bad_access_key"]


@pytest.mark.asyncio
async def test_register_password_over_128_chars_returns_422(client):
    """Pydantic body validation kicks in BEFORE the auth handler — 422 is fine."""
    r = await client.post(
        "/auth/register",
        json={
            "email": "u@example.com",
            "password": "x" * 129,
            "access_key": TEST_HOUSEHOLD_ACCESS_KEY,
        },
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_register_concurrent_race_with_different_emails(
    postgres_url, caplog
):
    """Two concurrent register calls with DIFFERENT valid emails.
    Advisory lock + count check must serialize them — exactly one
    succeeds, exactly one user row exists, loser gets the byte-identical
    registration_unavailable response."""
    from sqlalchemy import text
    from app.auth import service
    from app.models import Base
    from fastapi import HTTPException

    engine = create_async_engine(postgres_url, echo=False)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS citext"))
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def attempt(email: str) -> tuple[str, object]:
        async with Session() as session:
            try:
                await service.register(
                    session,
                    email=email,
                    password="correct-horse-battery-staple",
                    access_key=TEST_HOUSEHOLD_ACCESS_KEY,
                )
                return ("ok", None)
            except HTTPException as exc:
                return ("failed", exc.detail)

    results = await asyncio.gather(
        attempt("a@example.com"),
        attempt("b@example.com"),
    )
    statuses = [r[0] for r in results]
    assert statuses.count("ok") == 1
    assert statuses.count("failed") == 1

    # Loser response has the byte-identical detail string.
    loser = next(r for r in results if r[0] == "failed")
    assert loser[1] == "registration_unavailable"

    # Exactly ONE user row in the DB.
    async with Session() as session:
        n = await session.execute(select(func.count()).select_from(User))
        assert n.scalar_one() == 1

    # Cleanup so other tests' fresh-DB assumption holds.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def test_compare_digest_is_used_for_access_key_compare():
    """Source-code grep — the timing-microbenchmark approach is brittle
    and explicitly NOT used (Eng review run 1)."""
    import inspect

    from app.auth import service

    src = inspect.getsource(service.register)
    assert "hmac.compare_digest" in src, (
        "service.register MUST use hmac.compare_digest for the access-key compare"
    )
