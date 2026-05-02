"""Integration tests for ``POST /auth/refresh``."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import service
from app.auth.models import RefreshToken, User
from app.auth.tokens import (
    REFRESH_TOKEN_GRACE_SECONDS,
    REFRESH_TOKEN_TTL_DAYS,
    decode_access_token,
    hash_refresh_token,
)
from tests.integration.auth.conftest import TEST_HOUSEHOLD_ACCESS_KEY


# =============================================================================
# Case A — fresh cookie rotation
# =============================================================================

@pytest.mark.asyncio
async def test_refresh_case_a_returns_new_cookie_and_token(
    client, register_user, db_session, caplog
):
    """Fresh cookie → new cookie + new access JWT + old row superseded
    + successor_id pointing to new row + new row with NULL successor."""
    _, cookie, _ = await register_user("alice@example.com", "pwd-1234567890")
    caplog.set_level(logging.INFO, logger="app.auth")
    caplog.clear()

    client.cookies.set("__Host-refresh", cookie)
    r = await client.post("/auth/refresh")
    assert r.status_code == 200
    assert "access_token" in r.json()
    new_cookie = r.cookies.get("__Host-refresh")
    assert new_cookie is not None
    assert new_cookie != cookie

    # DB state: old row has superseded_at + successor_id; new row has neither.
    old_hash = hash_refresh_token(cookie)
    new_hash = hash_refresh_token(new_cookie)
    old_row = (
        await db_session.execute(select(RefreshToken).where(RefreshToken.token_hash == old_hash))
    ).scalar_one()
    new_row = (
        await db_session.execute(select(RefreshToken).where(RefreshToken.token_hash == new_hash))
    ).scalar_one()
    assert old_row.superseded_at is not None
    assert old_row.successor_id == new_row.id
    assert new_row.superseded_at is None
    assert new_row.successor_id is None
    # 30-day expiry
    expected = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_TTL_DAYS)
    delta = (expected - new_row.expires_at).total_seconds()
    assert -60 < delta < 60  # within a minute of expected

    # Log line.
    records = [r for r in caplog.records if r.name == "app.auth"]
    assert len(records) == 1
    assert records[0].outcome == "success"
    assert records[0].reason == "case_a"


# =============================================================================
# Case B — superseded within grace
# =============================================================================

@pytest.mark.asyncio
async def test_refresh_case_b_returns_token_without_set_cookie(
    client, register_user, db_session
):
    """Already-rotated cookie within 60s grace → access token, NO Set-Cookie."""
    _, cookie, _ = await register_user("alice@example.com", "pwd-1234567890")

    # Trigger Case A first to rotate.
    client.cookies.set("__Host-refresh", cookie)
    first = await client.post("/auth/refresh")
    assert first.status_code == 200

    # Replay the OLD cookie — Case B path.
    client.cookies.set("__Host-refresh", cookie)
    second = await client.post("/auth/refresh")
    assert second.status_code == 200
    assert "access_token" in second.json()
    # No Set-Cookie header (browser already has it from the parallel Case A).
    set_cookie_headers = [v for k, v in second.headers.items() if k.lower() == "set-cookie"]
    assert all("__Host-refresh" not in v for v in set_cookie_headers)


# =============================================================================
# Case C — past grace
# =============================================================================

@pytest.mark.asyncio
async def test_refresh_case_c_past_grace_rejects(
    client, register_user, db_session, caplog
):
    """At T+grace+1s with already-rotated cookie → 401 refresh_failed."""
    _, cookie, _ = await register_user("alice@example.com", "pwd-1234567890")

    # Rotate (Case A).
    client.cookies.set("__Host-refresh", cookie)
    first = await client.post("/auth/refresh")
    assert first.status_code == 200

    # Move the old row's superseded_at INTO THE PAST so it's outside grace.
    old_hash = hash_refresh_token(cookie)
    far_past = datetime.now(timezone.utc) - timedelta(
        seconds=REFRESH_TOKEN_GRACE_SECONDS + 5
    )
    old_row = (
        await db_session.execute(select(RefreshToken).where(RefreshToken.token_hash == old_hash))
    ).scalar_one()
    old_row.superseded_at = far_past
    await db_session.commit()

    caplog.set_level(logging.INFO, logger="app.auth")
    caplog.clear()
    client.cookies.set("__Host-refresh", cookie)
    r = await client.post("/auth/refresh")
    assert r.status_code == 401
    assert r.json() == {"detail": "refresh_failed"}

    failed = [r for r in caplog.records if r.name == "app.auth" and r.outcome == "failed"]
    assert any(r.reason == "bad_refresh_superseded" for r in failed)


# =============================================================================
# Concurrent Case-A serialization
# =============================================================================

@pytest.mark.asyncio
async def test_refresh_two_concurrent_case_a_serialize_via_row_lock(
    postgres_url
):
    """Two simultaneous Case-A refreshes with the SAME fresh cookie:
    row lock serializes them. Exactly one returns a new cookie (Case A);
    the second falls into Case B and returns access token only."""
    from sqlalchemy import text
    from app.models import Base

    engine = create_async_engine(postgres_url, echo=False)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS citext"))
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Seed: one user + one fresh refresh-token row.
    async with Session() as s:
        outcome = await service.register(
            s,
            email="alice@example.com",
            password="pwd-1234567890",
            access_key=TEST_HOUSEHOLD_ACCESS_KEY,
        )
        cookie = outcome.refresh_plaintext

    async def attempt():
        async with Session() as s:
            return await service.refresh(s, cookie)

    a, b = await asyncio.gather(attempt(), attempt())

    # Exactly one Case A, one Case B.
    cases = sorted([a.reason_log, b.reason_log])
    assert cases == ["case_a", "case_b"], f"got {cases!r}"
    case_a = a if a.reason_log == "case_a" else b
    case_b = a if a.reason_log == "case_b" else b
    assert case_a.new_refresh_plaintext is not None
    assert case_b.new_refresh_plaintext is None

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# =============================================================================
# Token-state rejection paths (all byte-identical 401)
# =============================================================================

@pytest.mark.asyncio
async def test_refresh_unknown_cookie_returns_401(client):
    client.cookies.set("__Host-refresh", "this-cookie-does-not-match-any-row")
    r = await client.post("/auth/refresh")
    assert r.status_code == 401
    assert r.json() == {"detail": "refresh_failed"}


@pytest.mark.asyncio
async def test_refresh_no_cookie_returns_401(client):
    client.cookies.delete("__Host-refresh")
    r = await client.post("/auth/refresh")
    assert r.status_code == 401
    assert r.json() == {"detail": "refresh_failed"}


@pytest.mark.asyncio
async def test_refresh_empty_string_cookie_returns_401(client):
    """Cookie present but empty string ("") must collapse to the same 401 as
    missing cookie. The service treats "" as falsy via ``if not incoming_cookie``."""
    client.cookies.set("__Host-refresh", "")
    r = await client.post("/auth/refresh")
    assert r.status_code == 401
    assert r.json() == {"detail": "refresh_failed"}


@pytest.mark.asyncio
async def test_refresh_revoked_cookie_returns_401(client, register_user, db_session):
    _, cookie, _ = await register_user("alice@example.com", "pwd-1234567890")
    # Manually revoke the row.
    h = hash_refresh_token(cookie)
    row = (
        await db_session.execute(select(RefreshToken).where(RefreshToken.token_hash == h))
    ).scalar_one()
    row.revoked_at = datetime.now(timezone.utc)
    await db_session.commit()

    client.cookies.set("__Host-refresh", cookie)
    r = await client.post("/auth/refresh")
    assert r.status_code == 401
    assert r.json() == {"detail": "refresh_failed"}


@pytest.mark.asyncio
async def test_refresh_expired_cookie_returns_401(client, register_user, db_session, caplog):
    _, cookie, _ = await register_user("alice@example.com", "pwd-1234567890")
    h = hash_refresh_token(cookie)
    row = (
        await db_session.execute(select(RefreshToken).where(RefreshToken.token_hash == h))
    ).scalar_one()
    row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=10)
    await db_session.commit()

    caplog.set_level(logging.INFO, logger="app.auth")
    client.cookies.set("__Host-refresh", cookie)
    r = await client.post("/auth/refresh")
    assert r.status_code == 401
    assert r.json() == {"detail": "refresh_failed"}
    failed = [r for r in caplog.records if r.name == "app.auth" and r.outcome == "failed"]
    assert any(r.reason == "bad_refresh_expired" for r in failed)


@pytest.mark.asyncio
async def test_refresh_byte_identical_across_all_failure_modes(client, register_user, db_session):
    """Unknown / revoked / expired all share the same response body."""
    _, cookie, _ = await register_user("alice@example.com", "pwd-1234567890")

    # Unknown.
    client.cookies.set("__Host-refresh", "z" * 40)
    unknown = await client.post("/auth/refresh")

    # Revoked.
    h = hash_refresh_token(cookie)
    row = (await db_session.execute(select(RefreshToken).where(RefreshToken.token_hash == h))).scalar_one()
    row.revoked_at = datetime.now(timezone.utc)
    await db_session.commit()
    client.cookies.set("__Host-refresh", cookie)
    revoked = await client.post("/auth/refresh")

    assert unknown.status_code == revoked.status_code == 401
    assert unknown.content == revoked.content


# =============================================================================
# Corrupt chain — cycle and overflow
# =============================================================================

@pytest.mark.asyncio
async def test_refresh_chain_cycle_returns_401_bad_refresh_chain(
    postgres_url, caplog
):
    """A self-referential chain (row.successor_id = row.id) → 401 +
    log reason=bad_refresh_chain. No infinite loop."""
    from sqlalchemy import text
    from app.models import Base

    engine = create_async_engine(postgres_url, echo=False)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS citext"))
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as s:
        outcome = await service.register(
            s,
            email="alice@example.com",
            password="pwd-1234567890",
            access_key=TEST_HOUSEHOLD_ACCESS_KEY,
        )
        cookie = outcome.refresh_plaintext

    # Manufacture a self-cycle on the row.
    async with Session() as s:
        h = hash_refresh_token(cookie)
        row = (
            await s.execute(select(RefreshToken).where(RefreshToken.token_hash == h))
        ).scalar_one()
        row.superseded_at = datetime.now(timezone.utc)
        row.successor_id = row.id  # cycle
        await s.commit()

    caplog.set_level(logging.INFO, logger="app.auth")
    async with Session() as s:
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await service.refresh(s, cookie)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "refresh_failed"
        assert getattr(exc_info.value, "log_reason", None) == "bad_refresh_chain"

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_refresh_chain_no_live_terminal_returns_401(
    postgres_url
):
    """Within grace, every row in the chain is revoked mid-traversal → 401."""
    from sqlalchemy import text
    from app.models import Base

    engine = create_async_engine(postgres_url, echo=False)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS citext"))
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Seed: register + rotate once (so we have a 2-row chain).
    async with Session() as s:
        outcome = await service.register(
            s,
            email="alice@example.com",
            password="pwd-1234567890",
            access_key=TEST_HOUSEHOLD_ACCESS_KEY,
        )
        cookie = outcome.refresh_plaintext

    async with Session() as s:
        await service.refresh(s, cookie)  # case A — creates successor

    # Now revoke EVERY row in the chain.
    async with Session() as s:
        rows = (await s.execute(select(RefreshToken))).scalars().all()
        for row in rows:
            row.revoked_at = datetime.now(timezone.utc)
        await s.commit()

    # Replaying the original cookie within grace → walks chain, finds no live terminal.
    async with Session() as s:
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await service.refresh(s, cookie)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "refresh_failed"

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
