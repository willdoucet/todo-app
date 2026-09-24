"""Background-job health, published on ``/healthz`` as ``jobs`` (M8 item 15).

The contract is pinned once, in the M8 plan's item 15 ("The /healthz.jobs contract"), and
three readers consume it: the Settings card, ``infra/release-smoke.py``'s jobs-fresh check,
and ``ops-check.yml`` through that script. None of them re-derives a threshold; they read
each row's ``stale`` and ``write_error``.

``/healthz`` is on Fly's health-check path, so the handler never touches the database. A
refresher started in the lifespan does the reading::

    lifespan: started_at = now (memory)
        refresher, every 30 s:  wait_for(read job_heartbeats, 1.0 s)
            ok            ─▶ snapshot = rows, read_at = now, read = "ok"
            timeout/error ─▶ keep rows and read_at; read = "stale"
                             ("unavailable" if nothing was ever read)
    GET /healthz ─▶ build_jobs_payload(reading, now, started_at) — memory only

Per request, for each beat_schedule task, in schedule order (rows = [] iff unavailable):

    stale        = now − last_success_at > 3 × interval     if it has succeeded
                 = now − started_at     > 3 × interval     if it never has (NULL expires)
    write_error  = last_error_at set, newer than last_success_at (or no success yet),
                   and now − last_error_at ≤ 3 × interval

``started_at`` is this process's memory. A web restart (a deploy, a crash, an operator kick)
re-arms the grace for rows that are still NULL; timestamped rows are unaffected. A table that
comes back empty *without* a restart gives NULL rows under an old ``started_at``, so they are
stale on the next request. Neither ``stale`` nor ``write_error`` is ever frozen at the last
read: both are computed when the request is served, so a reading kept by a hung store still
ages. And ``write_error`` is only ever stamped by a SUCCESS whose upsert failed, so a row
that carries it ran inside its window.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable, Literal, Mapping, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

REFRESH_INTERVAL_S = 30
READ_TIMEOUT_S = 1.0
STALE_AFTER_INTERVALS = 3

# One name everywhere (Design review 4A; Eng review 4, 3A): the Settings card, the top
# alert, the smoke script's failure line and incident-diagnostics.md all print these.
JOB_LABELS = {
    "app.tasks.sync_all_icloud_integrations": "iCloud calendar sync",
    "app.tasks.sync_all_reminders": "iCloud reminders sync",
    "app.tasks.hard_delete_expired_soft_deletes": "Deleted item cleanup",
    "app.tasks.sweep_abandoned_uploads": "Unused photo cleanup",
}


def humanize(task_name: str) -> str:
    """``app.tasks.sweep_abandoned_uploads`` → ``Sweep abandoned uploads``: a beat task with
    no label still gets a row, because a missing row hides a stale job."""
    words = task_name.rsplit(".", 1)[-1].replace("_", " ").strip()
    return words[:1].upper() + words[1:] if words else task_name


def beat_intervals(schedule: Optional[Mapping] = None) -> dict[str, float]:
    """``{celery task name: seconds}`` in ``beat_schedule`` order — the one definition of
    "which tasks, how often", shared by the worker's heartbeat filter and this payload.

    Raises on any schedule that is not a number or a ``timedelta``: a future ``crontab()``
    has no interval, and skipping it silently would hide a job. A structural test runs
    this over the real schedule, so such an entry fails CI rather than a probe.
    """
    if schedule is None:
        from app.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule
    intervals: dict[str, float] = {}
    for key, entry in schedule.items():
        task, raw = entry["task"], entry["schedule"]
        if isinstance(raw, timedelta):
            seconds = raw.total_seconds()
        elif isinstance(raw, (int, float)) and not isinstance(raw, bool):
            seconds = float(raw)
        else:
            raise TypeError(
                f"beat_schedule[{key!r}] has a {type(raw).__name__} schedule; "
                "job health needs a number of seconds or a timedelta"
            )
        if seconds <= 0:
            raise ValueError(f"beat_schedule[{key!r}] has a non-positive interval")
        if task in intervals:
            raise ValueError(f"beat_schedule schedules {task!r} twice")
        intervals[task] = seconds
    return intervals


_intervals: Optional[dict[str, float]] = None


def scheduled_intervals() -> dict[str, float]:
    """``beat_intervals()`` of the real schedule, derived once per process."""
    global _intervals
    if _intervals is None:
        _intervals = beat_intervals()
    return _intervals


# --- the reading the refresher keeps -----------------------------------------


@dataclass(frozen=True)
class HeartbeatRow:
    last_success_at: Optional[datetime]
    last_error_at: Optional[datetime]


@dataclass(frozen=True)
class Reading:
    """What the refresher last saw. Replaced wholesale, never mutated, so a request that is
    reading one cannot see half of the next."""

    read: Literal["ok", "stale", "unavailable"]
    read_at: Optional[datetime]
    rows: Optional[Mapping[str, HeartbeatRow]] = field(default=None)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


UNAVAILABLE = Reading(read="unavailable", read_at=None, rows=None)

_reading: Reading = UNAVAILABLE
# Overwritten in the lifespan; the import-time value only serves a process whose lifespan
# never ran (the unit tests' TestClient).
_started_at: datetime = utcnow()


def current_reading() -> Reading:
    return _reading


def started_at() -> datetime:
    return _started_at


def mark_started(now: Optional[datetime] = None) -> None:
    global _started_at
    _started_at = now or utcnow()


# --- the contract --------------------------------------------------------------

# Pydantic compiles `pattern=` with Rust's regex engine: `\z` is its end-of-text anchor
# (it has no `\Z`). Python's `$` would admit a trailing newline (LESSONS.md), Rust's would not.
_UTC_Z = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\z"


def iso_z(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    if value.tzinfo is None:
        raise ValueError("job health timestamps must be timezone-aware")
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class JobRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task: str = Field(min_length=1)
    label: str = Field(min_length=1)
    interval_s: Union[int, float] = Field(gt=0)
    last_success_at: Optional[str] = Field(default=None, pattern=_UTC_Z)
    stale: bool
    write_error: bool


class JobsReading(BaseModel):
    """``/healthz.jobs``. Validated before it is served; a body that fails validation is
    replaced by the unusable reading rather than served green (or raising on the probe)."""

    model_config = ConfigDict(extra="forbid")

    read: Literal["ok", "stale", "unavailable"]
    read_at: Optional[str] = Field(pattern=_UTC_Z)
    now: str = Field(pattern=_UTC_Z)
    rows: list[JobRow]

    @model_validator(mode="after")
    def _unavailable_iff_empty(self) -> "JobsReading":
        if (self.read == "unavailable") != (self.read_at is None):
            raise ValueError("read_at is null if and only if read is 'unavailable'")
        if (self.read == "unavailable") != (not self.rows):
            raise ValueError("rows is empty if and only if read is 'unavailable'")
        return self


def _seconds(value: float) -> Union[int, float]:
    return int(value) if float(value).is_integer() else value


def build_jobs_payload(
    reading: Reading,
    now: datetime,
    started_at: datetime,
    intervals: Optional[Mapping[str, float]] = None,
) -> dict:
    """The ``jobs`` object for ``now``. Pure: no clock, no store, no module state."""
    intervals = scheduled_intervals() if intervals is None else intervals
    if reading.read == "unavailable" or reading.rows is None:
        # The server never invents NULL rows it did not read.
        return {"read": "unavailable", "read_at": None, "now": iso_z(now), "rows": []}

    rows = []
    for task, interval in intervals.items():
        heartbeat = reading.rows.get(task)
        last_success = heartbeat.last_success_at if heartbeat else None
        last_error = heartbeat.last_error_at if heartbeat else None
        window = STALE_AFTER_INTERVALS * interval
        since = now - (last_success or started_at)
        stale = since.total_seconds() > window
        write_error = (
            last_error is not None
            and (last_success is None or last_error > last_success)
            and (now - last_error).total_seconds() <= window
        )
        rows.append(
            {
                "task": task,
                "label": JOB_LABELS.get(task) or humanize(task),
                "interval_s": _seconds(interval),
                "last_success_at": iso_z(last_success),
                "stale": stale,
                "write_error": write_error,
            }
        )
    return {"read": reading.read, "read_at": iso_z(reading.read_at), "now": iso_z(now), "rows": rows}


def serve_jobs(now: Optional[datetime] = None) -> dict:
    """What ``/healthz`` returns under ``jobs``. Never raises: ``/healthz`` is on Fly's
    probe path, where an exception is a killed machine."""
    now = now or utcnow()
    try:
        payload = build_jobs_payload(current_reading(), now, started_at())
        return JobsReading.model_validate(payload).model_dump(mode="json")
    except Exception as exc:
        logger.warning("job health payload unusable: %s", type(exc).__name__)
        return {"read": "unavailable", "read_at": None, "now": iso_z(now), "rows": []}


# --- the store: the worker's two writes, the web's one read ---------------------------

ERROR_NAME_MAX_LENGTH = 200


async def upsert_heartbeat_success(db: AsyncSession, task_name: str, now: datetime) -> None:
    """A beat task succeeded. Idempotent under redelivery (``ON CONFLICT``), and it clears
    any recorded write error: without that, one blip would paint "can't record job runs"
    forever after writes recover."""
    from sqlalchemy.dialects.postgresql import insert

    from app.models import JobHeartbeat

    cleared = {"last_success_at": now, "error_count": 0, "last_error": None, "last_error_at": None}
    stmt = insert(JobHeartbeat).values(task_name=task_name, **cleared)
    await db.execute(stmt.on_conflict_do_update(index_elements=[JobHeartbeat.task_name], set_=cleared))


async def record_heartbeat_error(db: AsyncSession, task_name: str, error: str, now: datetime) -> None:
    """The success upsert failed. Stamps the error class (never its message: it can quote
    data) and time, leaves ``last_success_at`` alone, and counts attempts."""
    from sqlalchemy.dialects.postgresql import insert

    from app.models import JobHeartbeat

    error = error[:ERROR_NAME_MAX_LENGTH]
    stmt = insert(JobHeartbeat).values(task_name=task_name, last_error=error, last_error_at=now, error_count=1)
    await db.execute(
        stmt.on_conflict_do_update(
            index_elements=[JobHeartbeat.task_name],
            set_={"last_error": error, "last_error_at": now, "error_count": JobHeartbeat.error_count + 1},
        )
    )


# --- the refresher ---------------------------------------------------------------

Reader = Callable[[], Awaitable[Mapping[str, HeartbeatRow]]]


async def read_heartbeats(session: AsyncSession) -> dict[str, HeartbeatRow]:
    """Every ``job_heartbeats`` row. Names outside ``beat_schedule`` are ignored later by
    ``build_jobs_payload``, never here, so the reader stays a plain read."""
    from app.models import JobHeartbeat

    result = await session.execute(
        select(JobHeartbeat.task_name, JobHeartbeat.last_success_at, JobHeartbeat.last_error_at)
    )
    return {name: HeartbeatRow(success, error) for name, success, error in result.all()}


async def read_with_app_session() -> dict[str, HeartbeatRow]:
    from app.database import AsyncSessionLocal

    if AsyncSessionLocal is None:
        raise RuntimeError("DATABASE_URL is not set")
    async with AsyncSessionLocal() as session:
        return await read_heartbeats(session)


async def refresh_once(
    reader: Reader,
    *,
    timeout: float = READ_TIMEOUT_S,
    clock: Callable[[], datetime] = utcnow,
) -> Reading:
    """One refresher cycle. A read that hangs, raises, or finds the table missing keeps the
    previous rows and ``read_at`` and reports ``stale`` (``unavailable`` if nothing was ever
    read); it never produces NULL rows. A good read replaces the snapshot wholesale, so no
    timestamp from an earlier reading survives it."""
    global _reading
    try:
        rows = await asyncio.wait_for(reader(), timeout)
    except Exception as exc:
        prior = _reading
        _reading = Reading(
            read="stale" if prior.rows is not None else "unavailable",
            read_at=prior.read_at,
            rows=prior.rows,
        )
        logger.warning("job health read failed: %s", type(exc).__name__)
    else:
        _reading = Reading(read="ok", read_at=clock(), rows=dict(rows))
    return _reading


async def refresh_forever(
    reader: Optional[Reader] = None,
    *,
    interval: Optional[float] = None,
    timeout: Optional[float] = None,
) -> None:
    """Runs until the lifespan cancels it. Any unexpected error is logged and the loop
    continues; ``CancelledError`` is not an ``Exception`` and ends the task. Defaults are
    looked up per cycle, not bound at definition, so a test can swap the module's reader."""
    while True:
        try:
            await refresh_once(
                reader or read_with_app_session,
                timeout=READ_TIMEOUT_S if timeout is None else timeout,
            )
        except Exception as exc:  # refresh_once already catches the reader's own errors
            logger.warning("job health refresher error: %s", type(exc).__name__)
        await asyncio.sleep(REFRESH_INTERVAL_S if interval is None else interval)

