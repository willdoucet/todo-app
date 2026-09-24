"""The worker's ``task_postrun`` heartbeat handler (M8 item 15): what it writes, and when.

The two SQL writes have integration tests (``tests/integration/test_job_heartbeat_store.py``).
Here ``_in_app_session`` and ``run_async`` are replaced, so each test sees the sequence of
writes the handler asked for — and can make one raise — without a database or an event loop.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from celery.signals import task_postrun

from app import job_health, tasks

NOW = datetime(2026, 9, 21, 17, 2, 40, tzinfo=timezone.utc)
CAL = "app.tasks.sync_all_icloud_integrations"


@pytest.fixture
def writes(monkeypatch):
    """Record each write as (function name, args); a test sets `fail` to make writes raise."""
    calls = []
    fail = []

    def in_session(write, *args):
        return (write.__name__, args)

    def run(item):
        calls.append(item)
        if fail and len(calls) <= len(fail):
            raise fail[len(calls) - 1]

    monkeypatch.setattr(tasks, "_in_app_session", in_session)
    monkeypatch.setattr(tasks, "run_async", run)
    monkeypatch.setattr(job_health, "utcnow", lambda: NOW)
    return SimpleNamespace(calls=calls, fail=fail)


def finish(name: str, state: str) -> None:
    tasks.record_job_heartbeat(sender=SimpleNamespace(name=name), state=state, retval=None)


def test_a_beat_task_success_upserts_its_row(writes):
    finish(CAL, "SUCCESS")
    assert writes.calls == [("upsert_heartbeat_success", (CAL, NOW))]


@pytest.mark.parametrize("state", ["FAILURE", "RETRY", "REVOKED", None])
def test_anything_but_success_writes_nothing(writes, state):
    """The signal fires on failure too; recording a failed task as a success would lie in
    the reassuring direction (Eng review 3)."""
    finish(CAL, state)
    assert writes.calls == []


@pytest.mark.parametrize(
    "name",
    ["app.tasks.health_check", "app.tasks.extract_recipe_from_url", "app.tasks.sync_single_integration", None],
)
def test_one_shot_tasks_never_get_a_row(writes, name):
    """Smoke check 4 fires health_check on every release; a recipe import succeeds whenever
    someone imports one. Neither is on beat_schedule, so neither may become a row that the
    card would then read as stale forever (Adversarial review)."""
    finish(name, "SUCCESS")
    assert writes.calls == []


def test_a_failed_upsert_records_the_error_class_and_warns(writes, caplog):
    caplog.set_level(logging.WARNING, logger="app.tasks")
    writes.fail.append(ConnectionRefusedError("postgres://user:hunter2@db/app refused"))
    finish(CAL, "SUCCESS")
    assert writes.calls == [
        ("upsert_heartbeat_success", (CAL, NOW)),
        ("record_heartbeat_error", (CAL, "ConnectionRefusedError", NOW)),
    ]
    messages = [r.getMessage() for r in caplog.records]
    assert messages == [f"Job heartbeat not recorded for {CAL}: ConnectionRefusedError"]
    assert "hunter2" not in " ".join(messages)


def test_when_the_error_write_fails_too_it_warns_once_more_and_stops(writes, caplog):
    caplog.set_level(logging.WARNING, logger="app.tasks")
    writes.fail.extend([OSError("down"), TimeoutError("still down")])
    finish(CAL, "SUCCESS")  # must not raise: a heartbeat never taints the task's result
    assert len(writes.calls) == 2
    assert [r.getMessage() for r in caplog.records] == [
        f"Job heartbeat not recorded for {CAL}: OSError",
        f"Job heartbeat error not recorded either for {CAL}: TimeoutError",
    ]


def test_an_uncomputable_schedule_does_not_break_every_task(writes, monkeypatch, caplog):
    def broken():
        raise TypeError("crontab has no interval")

    monkeypatch.setattr(job_health, "scheduled_intervals", broken)
    caplog.set_level(logging.WARNING, logger="app.tasks")
    finish(CAL, "SUCCESS")
    assert writes.calls == []
    assert caplog.records[0].getMessage() == "Job heartbeat filter failed: TypeError"


def test_the_handler_is_connected_to_celerys_task_postrun(writes):
    """Structural: the worker only records heartbeats if the receiver is registered."""
    task_postrun.send(
        sender=tasks.sync_all_reminders, task_id="t-1", task=tasks.sync_all_reminders,
        args=(), kwargs={}, retval=None, state="SUCCESS",
    )
    assert writes.calls == [("upsert_heartbeat_success", ("app.tasks.sync_all_reminders", NOW))]
