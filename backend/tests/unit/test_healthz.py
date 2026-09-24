"""Pin the /healthz contract (M8 items 14 and 15; plan item 15 → "The /healthz.jobs contract").

Shallow by design (LESSONS Decisions 2026-04-23): the handler reads only process state and
never awaits a database or Redis. It reports the deployed commit (`version`, REVIEW_CHECKLIST
FastAPI → Operations), whether the break-glass flag is on, and — from step 14 — the
background-job reading. Future drift fails the key-set test instead of silently shipping more
health metadata than intended.
"""

import asyncio
import time
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from app import job_health
from app.job_health import HeartbeatRow, Reading
from app.main import app

PROBE_BUDGET_S = 2.0  # Fly's health-check timeout


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("GIT_COMMIT", raising=False)
    monkeypatch.delenv("GATE_BREAK_GLASS", raising=False)
    # Not a context manager: the lifespan (and so the refresher) does not run.
    return TestClient(app)


def test_healthz_reports_status_version_and_break_glass(client, monkeypatch):
    monkeypatch.setenv("GIT_COMMIT", "abc123")
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == "abc123"
    assert body["gate_break_glass"] is False


@pytest.mark.parametrize("value", [None, "", "   "])
def test_healthz_version_is_unknown_without_the_build_arg(client, monkeypatch, value):
    if value is not None:
        monkeypatch.setenv("GIT_COMMIT", value)
    assert client.get("/healthz").json()["version"] == "unknown"


def test_healthz_is_never_cached(client):
    assert client.get("/healthz").headers["cache-control"] == "no-store"


@pytest.mark.parametrize(("value", "reported"), [("1", True), ("0", False), ("true", False)])
def test_healthz_reports_the_break_glass_flag(client, monkeypatch, value, reported):
    monkeypatch.setenv("GATE_BREAK_GLASS", value)
    assert client.get("/healthz").json()["gate_break_glass"] is reported


def test_healthz_body_has_exactly_the_contract_keys(client):
    body = client.get("/healthz").json()
    assert set(body) == {"status", "version", "gate_break_glass", "jobs"}
    assert set(body["jobs"]) == {"read", "read_at", "now", "rows"}


def test_healthz_jobs_serve_the_refresher_reading(client, monkeypatch):
    now = datetime.now(timezone.utc)
    rows = {task: HeartbeatRow(now - timedelta(minutes=2), None) for task in job_health.beat_intervals()}
    monkeypatch.setattr(job_health, "_reading", Reading("ok", now - timedelta(seconds=10), rows))
    jobs = client.get("/healthz").json()["jobs"]
    assert jobs["read"] == "ok"
    assert jobs["now"].endswith("Z")
    assert [r["label"] for r in jobs["rows"]] == [
        "iCloud calendar sync", "iCloud reminders sync", "Deleted item cleanup", "Unused photo cleanup",
    ]
    assert not any(r["stale"] or r["write_error"] for r in jobs["rows"])


def test_healthz_issues_no_database_queries(client, monkeypatch):
    """The handler reads memory only (Eng review 1.2). Every database call this codebase
    makes goes through AsyncSession.execute or AsyncConnection.execute; both are replaced
    with a recorder that refuses to run."""
    calls = []

    async def refuse(self, *args, **kwargs):
        calls.append(type(self).__name__)
        raise AssertionError("/healthz touched the database")

    monkeypatch.setattr(AsyncSession, "execute", refuse)
    monkeypatch.setattr(AsyncConnection, "execute", refuse)
    assert client.get("/healthz").status_code == 200
    assert calls == []

    # Negative control: the refresher's own read goes through the patched method.
    with pytest.raises(AssertionError):
        asyncio.run(job_health.read_heartbeats(AsyncSession()))
    assert calls == ["AsyncSession"]


def test_healthz_answers_within_the_probe_budget_while_the_store_hangs(monkeypatch):
    """The real lifespan runs (TestClient as a context manager) with the refresher's read
    stubbed to hang. /healthz still answers at once, from the last good reading, and reports
    it as stale once the 1-second read timeout (shortened here) has passed."""
    started = []

    async def hanging():
        started.append(True)
        await asyncio.Event().wait()

    last_good = datetime.now(timezone.utc) - timedelta(seconds=40)
    rows = {task: HeartbeatRow(last_good, None) for task in job_health.beat_intervals()}
    monkeypatch.setattr(job_health, "_reading", Reading("ok", last_good, rows))
    monkeypatch.setattr(job_health, "_started_at", job_health.started_at())
    monkeypatch.setattr(job_health, "read_with_app_session", hanging)
    monkeypatch.setattr(job_health, "READ_TIMEOUT_S", 0.05)

    with TestClient(app) as client:
        deadline = time.monotonic() + 5
        while job_health.current_reading().read != "stale" and time.monotonic() < deadline:
            time.sleep(0.01)
        began = time.monotonic()
        response = client.get("/healthz")
        elapsed = time.monotonic() - began

    assert started, "the lifespan never started the refresher"
    assert response.status_code == 200
    assert elapsed < PROBE_BUDGET_S
    jobs = response.json()["jobs"]
    assert jobs["read"] == "stale"
    assert jobs["read_at"] == job_health.iso_z(last_good)
    assert len(jobs["rows"]) == 4
