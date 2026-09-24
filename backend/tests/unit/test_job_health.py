"""Unit tests for ``app.job_health`` — the ``/healthz.jobs`` contract (M8 item 15).

Pure where it can be: ``build_jobs_payload(reading, now, started_at, intervals)`` takes every
input as an argument, so boundaries are tested to the second without a clock or a store.
The refresher is driven one cycle at a time with fake readers.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from celery.schedules import crontab

from app import job_health
from app.job_health import (
    UNAVAILABLE,
    HeartbeatRow,
    JobsReading,
    Reading,
    beat_intervals,
    build_jobs_payload,
    iso_z,
    refresh_once,
)

CAL = "app.tasks.sync_all_icloud_integrations"
REM = "app.tasks.sync_all_reminders"
DEL = "app.tasks.hard_delete_expired_soft_deletes"
SWEEP = "app.tasks.sweep_abandoned_uploads"
INTERVALS = {CAL: 600.0, REM: 600.0, DEL: 3600.0, SWEEP: 3600.0}

NOW = datetime(2026, 9, 21, 17, 2, 40, tzinfo=timezone.utc)
LONG_AGO = NOW - timedelta(days=2)  # a web process that started well before NOW


@pytest.fixture(autouse=True)
def isolated_state(monkeypatch):
    """The module keeps the refresher's reading in globals; every test starts from
    'nothing read yet' and monkeypatch restores the real values afterwards."""
    monkeypatch.setattr(job_health, "_reading", UNAVAILABLE)
    monkeypatch.setattr(job_health, "_intervals", None)


def ok(rows: dict, read_at: datetime = NOW - timedelta(seconds=20)) -> Reading:
    return Reading(read="ok", read_at=read_at, rows=rows)


def hb(success=None, error=None) -> HeartbeatRow:
    return HeartbeatRow(last_success_at=success, last_error_at=error)


def rows_by_task(payload: dict) -> dict[str, dict]:
    return {row["task"]: row for row in payload["rows"]}


def build(rows: dict, *, now=NOW, started=LONG_AGO, reading=None, intervals=INTERVALS) -> dict:
    return build_jobs_payload(reading or ok(rows), now, started, intervals)


# --- beat_intervals -----------------------------------------------------------


def test_structural_every_real_beat_entry_has_an_interval():
    """Runs over the real ``celery_app.conf.beat_schedule``: a future ``crontab()`` entry
    fails here, in CI, rather than being dropped from the card or raising on the probe."""
    assert beat_intervals() == INTERVALS
    assert list(beat_intervals()) == [CAL, REM, DEL, SWEEP]


def test_beat_intervals_accepts_timedelta():
    schedule = {"a": {"task": "app.tasks.a", "schedule": timedelta(minutes=5)}}
    assert beat_intervals(schedule) == {"app.tasks.a": 300.0}


@pytest.mark.parametrize("bad", [crontab(minute=0), "600", True, None])
def test_beat_intervals_raises_on_a_schedule_with_no_interval(bad):
    with pytest.raises(TypeError):
        beat_intervals({"x": {"task": "app.tasks.x", "schedule": bad}})


@pytest.mark.parametrize("bad", [0, -60, timedelta(0)])
def test_beat_intervals_raises_on_a_non_positive_interval(bad):
    with pytest.raises(ValueError):
        beat_intervals({"x": {"task": "app.tasks.x", "schedule": bad}})


def test_beat_intervals_raises_on_a_task_scheduled_twice():
    schedule = {
        "a": {"task": "app.tasks.x", "schedule": 60.0},
        "b": {"task": "app.tasks.x", "schedule": 120.0},
    }
    with pytest.raises(ValueError):
        beat_intervals(schedule)


# --- the payload ----------------------------------------------------------------


def test_unavailable_reading_has_no_rows_and_no_read_at():
    payload = build_jobs_payload(UNAVAILABLE, NOW, LONG_AGO, INTERVALS)
    assert payload == {"read": "unavailable", "read_at": None, "now": "2026-09-21T17:02:40Z", "rows": []}


def test_an_empty_table_still_lists_every_beat_task_in_schedule_order():
    payload = build({}, started=NOW - timedelta(minutes=5))
    assert [r["task"] for r in payload["rows"]] == [CAL, REM, DEL, SWEEP]
    assert all(r["last_success_at"] is None for r in payload["rows"])
    assert all(r["stale"] is False for r in payload["rows"])
    assert payload["read"] == "ok"


def test_labels_and_cadence_come_from_the_server():
    rows = rows_by_task(build({}))
    assert [rows[t]["label"] for t in (CAL, REM, DEL, SWEEP)] == [
        "iCloud calendar sync",
        "iCloud reminders sync",
        "Deleted item cleanup",
        "Unused photo cleanup",
    ]
    assert rows[CAL]["interval_s"] == 600 and isinstance(rows[CAL]["interval_s"], int)
    assert rows[SWEEP]["interval_s"] == 3600


def test_an_unmapped_beat_task_gets_its_humanized_name():
    payload = build({}, intervals={"app.tasks.rollup_nightly_totals": 3600.0})
    assert payload["rows"][0]["label"] == "Rollup nightly totals"


def test_rows_outside_beat_schedule_are_ignored():
    """A leftover non-beat row (``health_check`` from before the writer's filter, or a hand
    insert) never reaches the card, and cannot make "every row stale" lie."""
    fresh = NOW - timedelta(minutes=1)
    rows = {t: hb(fresh) for t in INTERVALS} | {"app.tasks.health_check": hb(LONG_AGO)}
    payload = build(rows)
    assert [r["task"] for r in payload["rows"]] == [CAL, REM, DEL, SWEEP]
    assert not any(r["stale"] for r in payload["rows"])


@pytest.mark.parametrize(
    ("task", "age_s", "stale"),
    [(CAL, 1800, False), (CAL, 1801, True), (SWEEP, 10800, False), (SWEEP, 10801, True)],
)
def test_a_timestamped_row_is_stale_only_past_three_intervals(task, age_s, stale):
    payload = build({task: hb(NOW - timedelta(seconds=age_s))})
    assert rows_by_task(payload)[task]["stale"] is stale


@pytest.mark.parametrize(
    ("task", "since_start_s", "stale"),
    [(CAL, 1800, False), (CAL, 1801, True), (SWEEP, 10800, False), (SWEEP, 10801, True)],
)
def test_a_never_run_row_is_stale_three_intervals_after_the_web_started(task, since_start_s, stale):
    """Eng review 4, 1A: "no data yet" expires. Equal is not stale; one second over is."""
    payload = build({}, started=NOW - timedelta(seconds=since_start_s))
    assert rows_by_task(payload)[task]["stale"] is stale


def test_last_success_serializes_utc_with_a_z():
    success = datetime(2026, 9, 21, 9, 58, 3, 123456, tzinfo=timezone(timedelta(hours=-7)))
    row = rows_by_task(build({CAL: hb(success)}))[CAL]
    assert row["last_success_at"] == "2026-09-21T16:58:03Z"


@pytest.mark.parametrize(
    ("success_age_s", "error_age_s", "flag"),
    [
        (3600, 60, True),      # newer than the success, inside 3 × 600 s
        (3600, 1800, True),    # exactly 3 × the interval is still inside the window
        (3600, 1801, False),   # aged out: the row reads behind/stopped, not "can't record"
        (60, 3000, False),     # older than the latest success: the recorder recovered
        (None, 60, True),      # no recorded success yet: the flag still means a run happened
        (None, 1801, False),   # ...until it ages out of the window
    ],
)
def test_write_error_window(success_age_s, error_age_s, flag):
    success = NOW - timedelta(seconds=success_age_s) if success_age_s is not None else None
    row = rows_by_task(build({CAL: hb(success, NOW - timedelta(seconds=error_age_s))}))[CAL]
    assert row["write_error"] is flag


def test_an_error_stamped_at_the_same_instant_as_the_success_is_no_write_error():
    """The writer stamps both writes with one `now`, so an upsert whose commit raised after
    the server had committed it leaves last_error_at == last_success_at: the run *was*
    recorded, and "newer than the success" is strict."""
    stamp = NOW - timedelta(minutes=2)
    row = rows_by_task(build({CAL: hb(stamp, stamp)}))[CAL]
    assert row["write_error"] is False


def test_write_error_on_a_fresh_row_does_not_make_it_stale():
    row = rows_by_task(build({CAL: hb(NOW - timedelta(minutes=5), NOW - timedelta(minutes=1))}))[CAL]
    assert row == row | {"stale": False, "write_error": True}


def test_staleness_is_computed_at_serve_time_not_at_the_last_read():
    """A reading kept by a hung store still ages: 31 min after a fresh read of a 10-minute
    task, the same stored row is stale."""
    reading = Reading(read="stale", read_at=NOW - timedelta(minutes=31), rows={CAL: hb(NOW - timedelta(minutes=31))})
    payload = build({}, reading=reading)
    assert payload["read"] == "stale"
    assert payload["read_at"] == iso_z(NOW - timedelta(minutes=31))
    assert rows_by_task(payload)[CAL]["stale"] is True


def test_payload_matches_the_contract_model():
    rows = {CAL: hb(NOW - timedelta(minutes=4)), SWEEP: hb(NOW - timedelta(hours=4), NOW - timedelta(minutes=1))}
    model = JobsReading.model_validate(build(rows))
    assert model.read == "ok" and len(model.rows) == 4


# --- serve_jobs: the probe path never raises -----------------------------------------


def test_serve_jobs_returns_the_unusable_reading_for_a_shape_break(monkeypatch):
    """A naive timestamp in the snapshot (a bug, or a column type drifting) must not serve a
    green body and must not raise on Fly's probe path."""
    monkeypatch.setattr(job_health, "_intervals", INTERVALS)
    monkeypatch.setattr(job_health, "_reading", ok({CAL: hb(datetime(2026, 9, 21, 17, 0))}))
    assert job_health.serve_jobs(NOW) == {"read": "unavailable", "read_at": None, "now": "2026-09-21T17:02:40Z", "rows": []}


def test_serve_jobs_with_no_beat_tasks_is_unusable(monkeypatch):
    """``read: ok`` with ``rows: []`` breaks the contract; the model refuses it."""
    monkeypatch.setattr(job_health, "_intervals", {})
    monkeypatch.setattr(job_health, "_reading", ok({}))
    assert job_health.serve_jobs(NOW)["read"] == "unavailable"


def test_serve_jobs_survives_an_uncomputable_schedule(monkeypatch):
    def broken():
        raise TypeError("crontab has no interval")

    monkeypatch.setattr(job_health, "scheduled_intervals", broken)
    monkeypatch.setattr(job_health, "_reading", ok({}))
    assert job_health.serve_jobs(NOW)["rows"] == []


def test_serve_jobs_healthy(monkeypatch):
    monkeypatch.setattr(job_health, "_intervals", INTERVALS)
    monkeypatch.setattr(job_health, "_started_at", LONG_AGO)
    monkeypatch.setattr(job_health, "_reading", ok({t: hb(NOW - timedelta(minutes=2)) for t in INTERVALS}))
    served = job_health.serve_jobs(NOW)
    assert served["read"] == "ok" and served["now"] == "2026-09-21T17:02:40Z"
    assert [r["stale"] for r in served["rows"]] == [False] * 4


# --- the refresher --------------------------------------------------------------------


def reader_of(rows):
    async def read():
        return rows

    return read


async def hang():
    await asyncio.Event().wait()


async def boom():
    raise RuntimeError('relation "job_heartbeats" does not exist')


async def test_a_good_read_replaces_the_snapshot_and_stamps_read_at():
    reading = await refresh_once(reader_of({CAL: hb(NOW)}), clock=lambda: NOW)
    assert reading == Reading(read="ok", read_at=NOW, rows={CAL: hb(NOW)})


async def test_a_hung_read_keeps_the_last_rows_and_read_at():
    await refresh_once(reader_of({CAL: hb(NOW)}), clock=lambda: NOW)
    reading = await refresh_once(hang, timeout=0.05, clock=lambda: NOW + timedelta(minutes=1))
    assert reading == Reading(read="stale", read_at=NOW, rows={CAL: hb(NOW)})


async def test_a_read_that_raises_before_any_good_read_is_unavailable():
    assert await refresh_once(boom) == UNAVAILABLE


async def test_a_missing_table_after_a_good_read_is_stale_and_never_null_rows():
    """Eng review 5: while the table is missing the read raises. That is an unusable
    reading once it ages, never a set of NULL rows that would read as 'waiting'."""
    await refresh_once(reader_of({CAL: hb(NOW)}), clock=lambda: NOW)
    reading = await refresh_once(boom)
    assert reading.read == "stale"
    assert reading.rows == {CAL: hb(NOW)}


async def test_restore_without_a_restart_makes_every_row_stale():
    """Eng review 5: a timestamped snapshot, then the table comes back empty under a web
    process that started long ago. Nothing from the earlier reading survives."""
    await refresh_once(reader_of({t: hb(NOW - timedelta(minutes=1)) for t in INTERVALS}), clock=lambda: NOW)
    reading = await refresh_once(reader_of({}), clock=lambda: NOW)
    payload = build_jobs_payload(reading, NOW, LONG_AGO, INTERVALS)
    assert [(r["last_success_at"], r["stale"]) for r in payload["rows"]] == [(None, True)] * 4


async def test_the_refresher_keeps_looping_after_a_read_error():
    calls = []
    done = asyncio.Event()

    async def flaky():
        calls.append(len(calls))
        if len(calls) == 1:
            raise ConnectionError("db restarting")
        done.set()
        return {CAL: hb(NOW)}

    task = asyncio.create_task(job_health.refresh_forever(flaky, interval=0, timeout=1))
    await asyncio.wait_for(done.wait(), 2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert len(calls) >= 2
    assert job_health.current_reading().read == "ok"


def test_iso_z_refuses_a_naive_timestamp():
    with pytest.raises(ValueError):
        iso_z(datetime(2026, 9, 21, 17, 0))
