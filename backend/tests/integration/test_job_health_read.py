"""``app.job_health.read_heartbeats`` against the real ``job_heartbeats`` table.

The unit tests drive the refresher with fake readers; this pins the one real read: the
columns it selects, that timestamptz comes back timezone-aware (so the payload can serialize
it with a `Z` instead of raising), and that a row outside ``beat_schedule`` is returned for
``build_jobs_payload`` to ignore.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.job_health import build_jobs_payload, Reading, read_heartbeats
from app.models import JobHeartbeat


@pytest.mark.asyncio
async def test_read_heartbeats_returns_aware_timestamps(db_session):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    db_session.add_all(
        [
            JobHeartbeat(task_name="app.tasks.sync_all_reminders", last_success_at=now - timedelta(minutes=3)),
            JobHeartbeat(
                task_name="app.tasks.sweep_abandoned_uploads",
                last_success_at=now - timedelta(hours=5),
                last_error="OperationalError",
                last_error_at=now - timedelta(minutes=2),
                error_count=3,
            ),
            JobHeartbeat(task_name="app.tasks.health_check", last_success_at=now),
        ]
    )
    await db_session.flush()

    rows = await read_heartbeats(db_session)

    assert set(rows) == {
        "app.tasks.sync_all_reminders",
        "app.tasks.sweep_abandoned_uploads",
        "app.tasks.health_check",
    }
    reminders = rows["app.tasks.sync_all_reminders"]
    assert reminders.last_success_at == now - timedelta(minutes=3)
    assert reminders.last_success_at.tzinfo is not None
    assert reminders.last_error_at is None

    payload = build_jobs_payload(Reading("ok", now, rows), now, now - timedelta(days=1))
    by_task = {r["task"]: r for r in payload["rows"]}
    assert "app.tasks.health_check" not in by_task
    assert by_task["app.tasks.sync_all_reminders"]["stale"] is False
    sweep = by_task["app.tasks.sweep_abandoned_uploads"]
    assert (sweep["stale"], sweep["write_error"]) == (True, True)
    # No row at all, and the web process started a day ago: the never-run sync is overdue.
    assert by_task["app.tasks.sync_all_icloud_integrations"]["last_success_at"] is None
    assert by_task["app.tasks.sync_all_icloud_integrations"]["stale"] is True
