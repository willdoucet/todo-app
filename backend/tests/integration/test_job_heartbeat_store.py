"""The two ``job_heartbeats`` writes the worker makes (M8 item 15), against the real table."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.job_health import record_heartbeat_error, upsert_heartbeat_success
from app.models import JobHeartbeat

TASK = "app.tasks.sweep_abandoned_uploads"
T0 = datetime(2026, 9, 21, 16, 0, 0, tzinfo=timezone.utc)


async def row(db):
    result = await db.execute(select(JobHeartbeat).where(JobHeartbeat.task_name == TASK))
    rows = result.scalars().all()
    assert len(rows) <= 1
    return rows[0] if rows else None


@pytest.mark.asyncio
async def test_first_success_inserts_a_clean_row(db_session):
    await upsert_heartbeat_success(db_session, TASK, T0)
    r = await row(db_session)
    assert (r.last_success_at, r.error_count, r.last_error, r.last_error_at) == (T0, 0, None, None)


@pytest.mark.asyncio
async def test_redelivered_success_is_idempotent(db_session):
    await upsert_heartbeat_success(db_session, TASK, T0)
    await upsert_heartbeat_success(db_session, TASK, T0 + timedelta(hours=1))
    r = await row(db_session)
    assert r.last_success_at == T0 + timedelta(hours=1)


@pytest.mark.asyncio
async def test_an_error_write_keeps_the_last_success_and_counts(db_session):
    await upsert_heartbeat_success(db_session, TASK, T0)
    await record_heartbeat_error(db_session, TASK, "OperationalError", T0 + timedelta(hours=1))
    await record_heartbeat_error(db_session, TASK, "InterfaceError", T0 + timedelta(hours=2))
    await db_session.refresh(r := await row(db_session))
    assert r.last_success_at == T0
    assert (r.last_error, r.last_error_at, r.error_count) == ("InterfaceError", T0 + timedelta(hours=2), 2)


@pytest.mark.asyncio
async def test_an_error_before_any_success_creates_the_row(db_session):
    """The fresh-deploy shape of "recorder broken, worker fine": the flag must be
    recordable even though no success ever was."""
    await record_heartbeat_error(db_session, TASK, "X" * 500, T0)
    r = await row(db_session)
    assert (r.last_success_at, r.error_count, r.last_error_at) == (None, 1, T0)
    assert r.last_error == "X" * 200  # class names only, bounded


@pytest.mark.asyncio
async def test_a_later_success_clears_the_error(db_session):
    """Otherwise one network blip paints "can't record job runs" forever (Adversarial review)."""
    await record_heartbeat_error(db_session, TASK, "OperationalError", T0)
    await upsert_heartbeat_success(db_session, TASK, T0 + timedelta(minutes=5))
    await db_session.refresh(r := await row(db_session))
    assert (r.last_success_at, r.error_count, r.last_error, r.last_error_at) == (
        T0 + timedelta(minutes=5), 0, None, None,
    )
