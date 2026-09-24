#!/usr/bin/env python3
"""Release smoke checks for the mealy production deployment (M8).

Runs on the operator's host, never in a container: it shells out to `fly` and
`curl` with the operator's own credentials (development-commands.md lists
`infra/` as a host-side exception). Standard library only; Python 3.11+ for
`tomllib`.

    python3 infra/release-smoke.py --release-commit=$(git rev-parse HEAD)
    python3 infra/release-smoke.py --only=liveness,recoverability,edge    # the cron subset
    python3 infra/release-smoke.py --self-test                            # prove the exit plumbing

Exit codes. A broken deployment and broken tooling never share a number:

    0  every selected check passed (skipped assertions are listed as `skipped`)
    1  a check failed: production is broken, or could not be verified by a check
       that must never pass unverified (a 429, a worker round-trip timeout)
    2  a precondition failed: flyctl missing, token rejected, no network, a
       Cloudflare challenge page where JSON was expected, a usage error

Check groups x exit classes x --skip. This table is the one place the matrix is
written; RUNBOOK.md and ops-check.yml name groups, never individual checks.

    group           check                    fails (exit 1) when                     skip key
    release         2 groups-started         a machine in a process group not started
                    3 scale-reconciled       counts != infra/fly-scale.json, or its
                                             keys != fly.toml [processes]
                    4 worker-roundtrip       health_check result not back in 30 s
                    8 commit-frontend        <meta build-commit>'s frontend/ is not
                                             the release's frontend/
                    8 commit-backend         /healthz version's backend/ is not        healthz_version
                                             the release's backend/
    liveness        1 healthz                /healthz not 200 by both paths
                    1 version-reported       /healthz `version` missing, empty,        healthz_version
                                             "unknown", or not a commit SHA
                      jobs-fresh             a /healthz.jobs row stale, or the         healthz_jobs
                                             reading unusable (the contract, item 15)
    recoverability  9 restore-point          no snapshot or WAL point under 48 h
    edge            5 origin-lock            direct != 421, or Cloudflare != 401
                      break-glass-off        /healthz.gate_break_glass not false       healthz_gate_break_glass
                    7 vercel-cache-headers   index / SPA route / asset Cache-Control
                    6 private-media-headers  the no-cookie 401's Cache-Control was
                                             rewritten, or the edge cached it

Any check ends in exit 2 instead when its tooling fails, and so does an error the
script did not anticipate (Python's own crash exit is 1). A skipped assertion
prints `skipped`, never `pass`; without --skip a missing /healthz key is exit 1,
because a PR1b field that has gone missing after PR1b shipped is a broken deploy.

A deliberate pause (infra/paused.json; `{}` means nothing is paused) is declared, not
skipped. Only `worker` and `beat` can be declared, each with `since`, `review_by` and
`reason`; both dates are UTC dates, compared with the UTC date of the run and of each job's
last success. While one is:

    2 groups-started    the paused group must be STOPPED; one that is running fails
    4 worker-roundtrip  PAUSED when the worker is declared (never run, never `pass`)
      jobs-fresh        PAUSED when worker or beat is declared, after the reading itself
                        passed the unusable-reading rule (the cron's only sign that the
                        web cannot read the database stays live). FAILS when a job
                        succeeded on a later day than the worker's `since` (or beat's,
                        when only beat is declared): the group was resumed and the file
                        was not emptied (check 2 is not in the cron's groups, so this is
                        the daily check's only sign of it)
    after review_by     those three FAIL (exit 1) on every run, until the pause is
                        extended or removed in a pull request

The summary line counts paused checks and names the declared groups. A malformed file, a
declared group other than worker or beat, or a `review_by` more than 31 days after the run
(a pause is reviewed at least monthly) is exit 2. --self-test ignores the file.

The script prints no secret and passes none as an argument. Remote error text is
reduced to one line with any `scheme://user:pass@` credential masked.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11; reported as exit 2 in main()
    tomllib = None

REPO_ROOT = Path(__file__).resolve().parent.parent
SCALE_FILE = REPO_ROOT / "infra" / "fly-scale.json"
PAUSE_FILE = REPO_ROOT / "infra" / "paused.json"
FLY_TOML = REPO_ROOT / "backend" / "fly.toml"
DIAGNOSTICS = "infra/incident-diagnostics.md"

FLY_APP = "mealy-app-prod"
FLY_DB_APP = "mealy-app-prod-db"
API_HOST = "api.mealy.dev"
FLY_HOST = f"{FLY_APP}.fly.dev"
FRONTEND_ORIGIN = "https://mealy.dev"
# Any route on the `protected` router: 401 through Cloudflare, 421 around it.
# Never an /auth/ path: the WAF rule (5 requests / 10 s / IP) would turn a
# re-run or a concurrent login into a 429 on the most alarming check here.
PROTECTED_PATH = "/tasks/"
# The media route's cookie dependency answers before the key is looked up, so
# this key does not need to exist.
PRIVATE_MEDIA_PATH = "/uploads/stock_icons/release-smoke.png"
SPA_ROUTE = "/mealboard"

RESTORE_POINT_MAX_AGE = timedelta(hours=48)
JOBS_READ_MAX_AGE = timedelta(seconds=120)
WORKER_TIMEOUT_S = 30

GROUPS = ("release", "liveness", "recoverability", "edge")
# web serves the app and /healthz: pausing it is an outage, not a pause.
PAUSABLE_GROUPS = ("worker", "beat")
PAUSE_REVIEW_MAX_DAYS = 31
SKIP_KEYS = ("healthz_jobs", "healthz_version", "healthz_gate_break_glass")


class CheckFailed(Exception):
    """Exit 1: production is broken, or a check could not be verified and must not pass."""


class Tooling(Exception):
    """Exit 2: the check could not run. Says nothing about production."""


class Paused(Exception):
    """Not verified because infra/paused.json declares the group it needs paused. Never a
    pass; never exit 1 while the pause is inside its review date."""


class Unreachable(Tooling):
    """curl could not complete the request (refused, timed out, empty reply). Tooling on
    its own; check 1 reads it as production when the other path answered in the same run."""


# --- process runner (the one seam tests replace) ---------------------------


@dataclass
class Completed:
    returncode: int
    stdout: str
    stderr: str


class Runner:
    def run(self, argv: list[str], timeout: float) -> Completed:
        try:
            proc = subprocess.run(
                argv, capture_output=True, text=True, errors="replace", timeout=timeout
            )
        except FileNotFoundError:
            raise Tooling(f"`{argv[0]}` is not on PATH")
        except subprocess.TimeoutExpired:
            raise Tooling(f"`{' '.join(argv[:3])}` timed out after {timeout:g} s")
        return Completed(proc.returncode, proc.stdout, proc.stderr)


_CREDENTIAL_IN_URL = re.compile(r"(\w+://)[^@\s/]+@")


def first_line(text: str) -> str:
    """One line of remote output, safe to print: credentials in URLs masked."""
    for line in text.splitlines():
        line = line.strip()
        if line:
            return _CREDENTIAL_IN_URL.sub(r"\1***@", line)[:200]
    return "(no output)"


# --- HTTP over curl --------------------------------------------------------


@dataclass
class Response:
    status: int
    headers: dict[str, str]  # lower-cased names; a repeated header is joined with ", "
    body: str


def _split_head(text: str) -> tuple[str, str]:
    for sep in ("\r\n\r\n", "\n\n"):
        i = text.find(sep)
        if i != -1:
            return text[:i], text[i + len(sep):]
    return text, ""


def parse_curl_include(stdout: str) -> Response:
    """Parse `curl -i` output, skipping 1xx and proxy CONNECT header blocks."""
    rest = stdout
    while True:
        head, body = _split_head(rest)
        lines = head.splitlines()
        match = re.match(r"HTTP/[\d.]+\s+(\d{3})", lines[0]) if lines else None
        if not match:
            raise Tooling("curl returned no HTTP status line")
        status = int(match.group(1))
        if 100 <= status < 200 or "connection established" in lines[0].lower():
            rest = body
            continue
        headers: dict[str, str] = {}
        for line in lines[1:]:
            name, colon, value = line.partition(":")
            if colon:
                key = name.strip().lower()
                headers[key] = f"{headers[key]}, {value.strip()}" if key in headers else value.strip()
        return Response(status, headers, body)


def is_challenge(resp: Response) -> bool:
    """A Cloudflare interstitial (Bot Fight Mode, a managed challenge), not the origin."""
    if resp.headers.get("cf-mitigated", "").lower() == "challenge":
        return True
    return resp.status in (403, 503) and any(
        marker in resp.body for marker in ("Just a moment", "challenge-platform", "cf-chl")
    )


def cache_directives(value: str) -> set[str]:
    return {part.strip().split("=")[0].lower() for part in value.split(",") if part.strip()}


def parse_time(value: object) -> datetime | None:
    """ISO-8601 to an aware UTC datetime; a naive value is UTC. None if it does not parse."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def human_age(delta: timedelta) -> str:
    seconds = int(delta.total_seconds())
    if seconds < 3600:
        return f"{max(seconds, 0) // 60} min"
    if seconds < 172800:
        return f"{seconds // 3600} h"
    return f"{seconds // 86400} days"


# --- production reads, memoized per run ------------------------------------


@dataclass(frozen=True)
class Pause:
    group: str
    since: date
    review_by: date
    reason: str

    def note(self) -> str:
        return f"{self.group} paused since {self.since.isoformat()} ({self.reason}; infra/paused.json)"


def _pause_date(group: str, field: str, value: object) -> date:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise Tooling(f"infra/paused.json: {group}.{field} must be a YYYY-MM-DD date")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise Tooling(f"infra/paused.json: {group}.{field} is not a real date") from None


def read_pauses(path: Path) -> dict[str, Pause]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise Tooling(f"infra/paused.json does not parse: {type(exc).__name__}") from None
    if not isinstance(data, dict):
        raise Tooling("infra/paused.json must be a JSON object ({} when nothing is paused)")
    pauses = {}
    for group, entry in data.items():
        if group not in PAUSABLE_GROUPS:
            raise Tooling(f"infra/paused.json declares {group!r}; only {', '.join(PAUSABLE_GROUPS)} can be paused")
        if not isinstance(entry, dict) or set(entry) != {"since", "review_by", "reason"}:
            raise Tooling(f"infra/paused.json: {group} needs exactly since, review_by and reason")
        reason = entry["reason"]
        if not isinstance(reason, str) or not reason.strip():
            raise Tooling(f"infra/paused.json: {group}.reason must say why")
        since = _pause_date(group, "since", entry["since"])
        review_by = _pause_date(group, "review_by", entry["review_by"])
        if review_by < since:
            raise Tooling(f"infra/paused.json: {group}.review_by is before since")
        pauses[group] = Pause(group, since, review_by, reason.strip())
    return pauses


def review_within_limit(pauses: dict[str, Pause], today: date) -> dict[str, Pause]:
    """A pause is reviewed at least monthly: a `review_by` further out than that is exit 2 on
    every run, or one far date would let the daily check print PAUSE for years (final review,
    M8 PR1b). Measured from the run, not from `since`, so an extension is always one more
    month."""
    limit = today + timedelta(days=PAUSE_REVIEW_MAX_DAYS)
    for p in pauses.values():
        if p.review_by > limit:
            raise Tooling(
                f"infra/paused.json: {p.group}.review_by {p.review_by.isoformat()} is more than "
                f"{PAUSE_REVIEW_MAX_DAYS} days out; a pause is reviewed at least monthly"
            )
    return pauses


def pause_verdict(ctx: "Context", groups: tuple[str, ...], what: str) -> None:
    """Raise Paused, or CheckFailed once a declared pause is past its review date, when any
    of `groups` is declared paused. Return quietly when none is."""
    declared = [ctx.pauses()[g] for g in groups if g in ctx.pauses()]
    if not declared:
        return
    overdue = [p for p in declared if ctx.now.date() > p.review_by]
    if overdue:
        raise CheckFailed(
            "; ".join(
                f"{p.group} pause is past its review date ({p.review_by.isoformat()}): resume it "
                "(TODOS.md P1), or extend review_by in infra/paused.json in a pull request"
                for p in overdue
            )
        )
    raise Paused(f"{what} not verified: " + "; ".join(p.note() for p in declared))


class Context:
    """Every production read, memoized, so checks sharing /healthz or the machine list
    ask once. A failed read is memoized too: every check that needed it reports it."""

    def __init__(
        self,
        runner: Runner,
        *,
        release_commit: str | None = None,
        now: datetime | None = None,
        scale_file: Path = SCALE_FILE,
        fly_toml: Path = FLY_TOML,
        pause_file: Path | None = None,
    ):
        self.runner = runner
        self.release_commit = release_commit
        self.now = now or datetime.now(timezone.utc)
        self.scale_file = scale_file
        self.fly_toml = fly_toml
        # Looked up at construction so a test can point the module at another file.
        self.pause_file = pause_file or PAUSE_FILE
        self._memo: dict[str, tuple[bool, object]] = {}

    def once(self, key: str, fetch: Callable[[], object]):
        if key not in self._memo:
            try:
                self._memo[key] = (True, fetch())
            except (CheckFailed, Tooling) as exc:
                self._memo[key] = (False, exc)
        ok, value = self._memo[key]
        if ok:
            return value
        raise value

    # local files

    def pauses(self) -> dict[str, "Pause"]:
        """infra/paused.json, validated. A missing file declares nothing, which is the strict
        reading: every check then expects every group running."""
        return self.once("pauses", lambda: review_within_limit(read_pauses(self.pause_file), self.now.date()))

    def processes(self) -> dict:
        return tomllib.loads(self.fly_toml.read_text())["processes"]

    def scale(self) -> dict[str, int]:
        """infra/fly-scale.json, after asserting its keys equal fly.toml [processes],
        so a typo cannot silently drop a process group from the diff."""
        try:
            expected = json.loads(self.scale_file.read_text())
        except ValueError as exc:
            raise CheckFailed(f"infra/fly-scale.json is not JSON: {exc}")
        processes = self.processes()
        if not isinstance(expected, dict) or set(expected) != set(processes):
            keys = sorted(expected) if isinstance(expected, dict) else expected
            raise CheckFailed(
                f"infra/fly-scale.json keys {keys} != fly.toml [processes] keys "
                f"{sorted(processes)}; fix the file before trusting the diff"
            )
        for group, count in expected.items():
            if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                raise CheckFailed(f"infra/fly-scale.json: {group} = {count!r} is not a count")
        return expected

    # fly

    def fly(self, *args: str, timeout: float = 60) -> Completed:
        completed = self.runner.run(["fly", *args], timeout)
        if completed.returncode != 0:
            raise Tooling(
                f"`fly {' '.join(args[:3])}` exited {completed.returncode}: "
                f"{first_line(completed.stderr or completed.stdout)}"
            )
        return completed

    def fly_json(self, *args: str):
        completed = self.fly(*args)
        try:
            return json.loads(completed.stdout)
        except ValueError:
            raise Tooling(f"`fly {' '.join(args[:3])}` did not print JSON (flyctl output shape changed?)")

    def machines(self) -> list[dict]:
        def fetch():
            data = self.fly_json("machines", "list", "--json", "-a", FLY_APP)
            if not isinstance(data, list) or not all(isinstance(m, dict) for m in data):
                raise Tooling("`fly machines list --json` is not a list of machines (shape changed?)")
            return [
                m for m in data
                if m.get("state") not in ("destroying", "destroyed")
                and machine_group(m) != "fly_app_release_command"
            ]
        return self.once("machines", fetch)

    def fly_ip(self) -> str:
        def fetch():
            data = self.fly_json("ips", "list", "--json", "-a", FLY_APP)
            v6 = None
            for entry in data if isinstance(data, list) else []:
                if not isinstance(entry, dict):
                    continue
                kind = str(entry.get("Type") or entry.get("type") or "").lower()
                address = entry.get("Address") or entry.get("address")
                if address and kind in ("v4", "shared_v4"):
                    return address
                if address and kind == "v6" and v6 is None:
                    v6 = address
            if v6:
                return v6
            raise Tooling("`fly ips list --json` returned no public address (shape changed?)")
        return self.once("fly_ip", fetch)

    def volume_snapshots(self) -> list[tuple[str, list[datetime]]]:
        """(volume id, snapshot times) for every live volume of the database app."""
        def fetch():
            volumes = self.fly_json("volumes", "list", "--json", "-a", FLY_DB_APP)
            if not isinstance(volumes, list):
                raise Tooling("`fly volumes list --json` is not a list (shape changed?)")
            live = [
                v for v in volumes
                if isinstance(v, dict)
                and v.get("state") not in ("destroying", "destroyed", "pending_destroy")
            ]
            if not live:
                raise CheckFailed(f"{FLY_DB_APP} has no live volume")
            found = []
            for volume in live:
                volume_id = volume.get("id")
                if not isinstance(volume_id, str):
                    raise Tooling("`fly volumes list --json`: a volume has no id (shape changed?)")
                # The volume id comes from the listing at run time: a host migration
                # changes it (LESSONS: a Fly host migration resets snapshot history).
                # -a is mandatory: without it flyctl infers the app from the cwd's
                # fly.toml and fails with "volume does not belong to app".
                completed = self.fly("volumes", "snapshots", "list", volume_id, "-a", FLY_DB_APP, "--json")
                text = completed.stdout.strip()
                if not text or text == "null" or text.lower().startswith("no snapshots"):
                    snapshots = []
                else:
                    try:
                        snapshots = json.loads(text)
                    except ValueError:
                        raise Tooling("`fly volumes snapshots list --json` did not print JSON (shape changed?)")
                if not isinstance(snapshots, list):
                    raise Tooling("`fly volumes snapshots list --json` is not a list (shape changed?)")
                times = []
                for snapshot in snapshots:
                    if not isinstance(snapshot, dict):
                        continue
                    if str(snapshot.get("status", "")).lower() in ("failed", "error"):
                        continue
                    created = parse_time(snapshot.get("created_at") or snapshot.get("CreatedAt"))
                    if created:
                        times.append(created)
                found.append((volume_id, times))
            return found
        return self.once("volume_snapshots", fetch)

    def wal_backups(self) -> tuple[str, list[datetime]]:
        """("ok", times) or ("disabled", []). `fly pg backup list` has no --json in
        flyctl v0.4.102, so this reads timestamps out of its table rather than
        columns; any other failure is exit 2."""
        def fetch():
            completed = self.runner.run(["fly", "pg", "backup", "list", "-a", FLY_DB_APP], 90)
            text = f"{completed.stdout}\n{completed.stderr}"
            if completed.returncode != 0:
                lowered = text.lower()
                if "not enabled" in lowered or "backup enable" in lowered or "backups are disabled" in lowered:
                    return ("disabled", [])
                raise Tooling(
                    f"`fly pg backup list` exited {completed.returncode}: "
                    f"{first_line(completed.stderr or completed.stdout)}"
                )
            return ("ok", parse_backup_times(completed.stdout))
        return self.once("wal_backups", fetch)

    # http

    def http_get(self, url: str, *, resolve_ip: str | None = None, timeout: int = 20) -> Response:
        argv = ["curl", "-sS", "-i", "--max-time", str(timeout), "--proto", "=https"]
        if resolve_ip:
            host = url.split("/")[2]
            address = f"[{resolve_ip}]" if ":" in resolve_ip else resolve_ip
            argv += ["--resolve", f"{host}:443:{address}"]
        argv.append(url)
        completed = self.runner.run(argv, timeout + 5)
        if completed.returncode != 0:
            raise Unreachable(f"curl {url}: exit {completed.returncode}: {first_line(completed.stderr)}")
        return parse_curl_include(completed.stdout)

    def healthz_body(self) -> dict:
        """/healthz through Cloudflare: the body the jobs, break-glass and version
        assertions read."""
        def fetch():
            return healthz_json(self.http_get(f"https://{API_HOST}/healthz"), "through Cloudflare")
        return self.once("healthz_cf", fetch)

    def healthz_fly_body(self) -> dict:
        def fetch():
            return healthz_json(self.http_get(f"https://{FLY_HOST}/healthz"), f"via {FLY_HOST}")
        return self.once("healthz_fly", fetch)

    def frontend_index(self) -> Response:
        return self.once("frontend_index", lambda: self.http_get(f"{FRONTEND_ORIGIN}/index.html"))


def machine_group(machine: dict) -> str:
    metadata = (machine.get("config") or {}).get("metadata") or {}
    return str(metadata.get("fly_process_group") or metadata.get("process_group") or "")


def is_standby(machine: dict) -> bool:
    """A Fly standby: stopped by design, started by the platform only if its primary's host
    fails. Never "should be started": starting a beat standby by hand would run two beats
    and double-fire the iCloud sync."""
    return bool((machine.get("config") or {}).get("standbys"))


def is_counted(machine: dict) -> bool:
    """A standby counts toward its group only once it runs: a started beat standby beside its
    primary is a second beat, the invariant check 3 exists for (/final-review, M8 PR1a)."""
    return not is_standby(machine) or machine.get("state") == "started"


def healthz_json(resp: Response, path_label: str) -> dict:
    if is_challenge(resp):
        raise Tooling(f"/healthz {path_label}: Cloudflare challenge page instead of JSON (Bot Fight Mode?)")
    if resp.status != 200:
        raise CheckFailed(f"/healthz {path_label} answered {resp.status}, expected 200")
    try:
        body = json.loads(resp.body)
    except ValueError:
        raise Tooling(f"/healthz {path_label}: 200 with a non-JSON body")
    if not isinstance(body, dict):
        raise CheckFailed(f"/healthz {path_label}: body is not a JSON object")
    return body


_BACKUP_TIME = re.compile(
    r"(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2})(?:\.\d+)?\s*(Z|UTC|[+-]\d{2}:?\d{2})?"
)
_BARMAN_ID = re.compile(r"\b(\d{8})T(\d{6})\b")


_FAILED_ROW = re.compile(r"fail|error", re.I)


def parse_backup_times(text: str) -> list[datetime]:
    """Every timestamp in `fly pg backup list` output, as UTC. Reads times, not
    columns, so a reordered or renamed column cannot turn into a wrong answer. A row
    that says it failed is not a restore point, whatever column says so (the snapshot
    path skips failed snapshots the same way)."""
    times = []
    for line in text.splitlines():
        if _FAILED_ROW.search(line):
            continue
        for date, clock, zone in _BACKUP_TIME.findall(line):
            suffix = "+00:00" if zone in ("", "Z", "UTC") else zone
            if len(suffix) == 5:  # +0000
                suffix = f"{suffix[:3]}:{suffix[3:]}"
            parsed = parse_time(f"{date}T{clock}{suffix}")
            if parsed:
                times.append(parsed)
        for date, clock in _BARMAN_ID.findall(line):
            try:
                times.append(datetime.strptime(date + clock, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc))
            except ValueError:
                pass
    return times


# --- the /healthz.jobs contract (plan item 15) ------------------------------


def jobs_verdict(jobs: object, paused: Callable[[], None] | None = None) -> str:
    """Apply the /healthz.jobs contract. Returns a pass detail or raises CheckFailed.

    The unusable-reading rule is checked first, the same order Settings uses: a
    reading that is unavailable, too old, or malformed reports that alone, never
    the stale rows of a reading it has just called unusable. The script derives
    no threshold of its own; it reads each row's server-computed `stale`."""
    cannot_read = "Background jobs: web cannot read job_heartbeats"
    malformed = "Background jobs: malformed jobs"
    if not isinstance(jobs, dict):
        raise CheckFailed(f"{malformed} (not an object)")
    read = jobs.get("read")
    if read not in ("ok", "stale", "unavailable"):
        raise CheckFailed(f"{malformed} (read is {read!r})")
    now = parse_time(jobs.get("now"))
    if now is None:
        raise CheckFailed(f"{malformed} (now does not parse)")
    if read == "unavailable":
        raise CheckFailed(f"{cannot_read} (read is unavailable)")
    read_at = parse_time(jobs.get("read_at"))
    if read_at is None:
        raise CheckFailed(f"{malformed} (read_at is missing while read is {read!r})")
    rows = jobs.get("rows")
    if not isinstance(rows, list):
        raise CheckFailed(f"{malformed} (rows is not a list)")
    if not rows:
        raise CheckFailed(f"{malformed} (no rows while read is {read!r})")
    for row in rows:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("task"), str)
            or not isinstance(row.get("label"), str)
            or "interval_s" not in row
            or not isinstance(row.get("stale"), bool)
            or not isinstance(row.get("write_error"), bool)
        ):
            raise CheckFailed(f"{malformed} (a row lacks task, label, interval_s, or a boolean stale / write_error)")
    if now - read_at > JOBS_READ_MAX_AGE:
        raise CheckFailed(f"{cannot_read} (last good read {human_age(now - read_at)} before serve time)")
    if paused is not None:
        paused()  # raises Paused (or CheckFailed past review_by) when worker or beat is declared
    stale = [row for row in rows if row["stale"]]
    if stale:
        names = [
            f"{row['label']} (can't record runs)" if row["write_error"] else row["label"]
            for row in stale
        ]
        raise CheckFailed(f"Background jobs behind schedule: {', '.join(names)}")
    waiting = sum(1 for row in rows if row.get("last_success_at") is None)
    detail = f"{len(rows)} background jobs fresh"
    return f"{detail} ({waiting} not yet run, inside the post-start grace)" if waiting else detail


# --- checks ----------------------------------------------------------------


def _standby_note(machines: list[dict]) -> str:
    standbys = Counter(machine_group(m) for m in machines if not is_counted(m))
    if not standbys:
        return ""
    return " (standby, not counted: " + ", ".join(f"{g}={n}" for g, n in sorted(standbys.items())) + ")"


def check_groups_started(ctx: Context) -> str:
    machines = ctx.machines()
    pauses = ctx.pauses()
    stopped, running_paused, counts = [], [], []
    for group in sorted(ctx.processes()):
        members = [m for m in machines if machine_group(m) == group and not is_standby(m)]
        counts.append(f"{group}={len(members)}" + (" paused" if group in pauses else ""))
        if not members:
            stopped.append(f"{group}: no machine")
        for machine in members:
            state = machine.get("state", "?")
            if group in pauses:
                # Declared paused: running is the failure. A started worker spends the broker
                # allowance the pause exists to protect, or means someone resumed it and forgot
                # the file.
                if state == "started":
                    running_paused.append(f"{group} {machine.get('id', '?')}")
            elif state != "started":
                stopped.append(f"{group} {machine.get('id', '?')} is {state}")
    if stopped or running_paused:
        parts = []
        if stopped:
            parts.append(
                "not every process group is started: " + "; ".join(stopped)
                + ". A deploy leaves a stopped machine stopped: `fly machine start <id> -a mealy-app-prod`"
                + " (never a standby)"
            )
        if running_paused:
            parts.append(
                "declared paused in infra/paused.json but running: " + "; ".join(running_paused)
                + ". Stop it again (`fly machine stop <id> -a mealy-app-prod`), or remove the pause"
                + " in a pull request if the resume is deliberate"
            )
        raise CheckFailed(". ".join(parts) + _standby_note(machines))
    overdue = [p for p in pauses.values() if ctx.now.date() > p.review_by]
    if overdue:
        pause_verdict(ctx, tuple(p.group for p in overdue), "groups-started")
    if pauses:
        return (
            "every process group as declared: " + ", ".join(counts) + " ("
            + "; ".join(p.note() for p in pauses.values()) + ")" + _standby_note(machines)
        )
    return "every process group started: " + ", ".join(counts) + _standby_note(machines)


def check_scale(ctx: Context) -> str:
    expected = ctx.scale()  # key-set assertion first, before any fly call
    counts = Counter(machine_group(m) for m in ctx.machines() if is_counted(m))
    problems = [
        f"{group}: expected {count}, found {counts.get(group, 0)}"
        for group, count in sorted(expected.items())
        if counts.get(group, 0) != count
    ]
    problems += [
        f"{group}: {counts[group]} machine(s) in a group infra/fly-scale.json does not list"
        for group in sorted(set(counts) - set(expected))
    ]
    running_standbys = sorted({machine_group(m) for m in ctx.machines() if is_standby(m) and is_counted(m)})
    if running_standbys:
        problems.append(
            f"a started standby in {', '.join(running_standbys)} is counted: if its primary also runs, that is two"
        )
    if problems:
        raise CheckFailed(
            "; ".join(problems) + ". Counts are set out-of-band: `fly scale count <group>=<n> -a mealy-app-prod`"
        )
    return (", ".join(f"{g}={n}" for g, n in sorted(expected.items())) + " (matches infra/fly-scale.json)"
            + _standby_note(ctx.machines()))


# One line so flyctl's argument splitting keeps it one argument; single quotes
# only, inside the double-quoted -c. The interpreter is spelled absolutely: the
# prod image's PATH entry `.venv/bin` is relative to the cwd.
_WORKER_PROBE = (
    "import json, sys; sys.path.insert(0, '/app'); "
    "from app.tasks import health_check; "
    f"print('SMOKE_ROUNDTRIP ' + json.dumps(health_check.delay().get(timeout={WORKER_TIMEOUT_S})))"
)


def check_worker(ctx: Context) -> str:
    pause_verdict(ctx, ("worker",), "worker round-trip")
    completed = ctx.runner.run(
        ["fly", "ssh", "console", "-a", FLY_APP, "-g", "web",
         "-C", f'/app/.venv/bin/python -c "{_WORKER_PROBE}"'],
        WORKER_TIMEOUT_S + 90,
    )
    match = re.search(r"^SMOKE_ROUNDTRIP (.+)$", completed.stdout, re.M)
    if match:
        try:
            result = json.loads(match.group(1))
        except ValueError:
            result = None
        if result == {"status": "ok"}:
            return "health_check enqueued from a web machine, run by the worker, result read back"
        raise CheckFailed(f"health_check returned {match.group(1)[:80]!r}, expected {{\"status\": \"ok\"}}")
    if "TimeoutError" in completed.stdout + completed.stderr:
        raise CheckFailed(
            f"worker round-trip unverified: no result within {WORKER_TIMEOUT_S} s. Inspect queue depth and "
            "the worker log before declaring the worker dead; if the Postgres primary was waking, wait and "
            "retry once"
        )
    output = f"{completed.stdout}\n{completed.stderr}"
    if "Traceback (most recent call last)" in output:
        # The probe ran in the app's environment and raised there (broker down, a
        # broken import): evidence about production, not about the laptop.
        last = [line.strip() for line in output.splitlines() if line.strip()][-1]
        raise CheckFailed(f"worker round-trip failed on the machine: {first_line(last)}")
    raise Tooling(
        f"`fly ssh console` exited {completed.returncode}: {first_line(completed.stderr or completed.stdout)}"
    )


_SHA = re.compile(r"[0-9a-f]{7,40}\Z")
# The directory each tier is built from: Vercel builds frontend/, fly deploy builds backend/.
TIER_DIRS = {"frontend": "frontend/", "backend": "backend/"}
# Vercel's buildCommand sets VITE_GIT_COMMIT from VERCEL_GIT_COMMIT_SHA; when that is not
# exposed the variable is set but empty, and Vite writes "" (not the placeholder).
_VERCEL_SHA_HINT = "is 'Automatically expose System Environment Variables' on in Vercel?"


def assert_deployed_matches(ctx: Context, tier: str, sha: str | None) -> str:
    """The deployed build has the release's code for its tier.

    Compared by content, not ancestry (/review-implementation, M8 PR1a): the previous
    release is always an ancestor, so an ancestor test passes a forgotten promote; and a
    squash merge never makes the pull request's head an ancestor of `master`, so it fails
    RUNBOOK §4's deploy-before-merge path. `git diff --quiet <deployed> <release> -- <dir>`
    passes an identical tree however the two commits are related, and a release that did
    not touch a tier passes on the previous build of it."""
    release = ctx.release_commit or ""
    if sha is None:
        raise CheckFailed(f"{tier}: no commit reported")
    if sha == "":
        hint = f" ({_VERCEL_SHA_HINT})" if tier == "frontend" else ""
        raise CheckFailed(f"{tier}: the reported commit is empty{hint}")
    if "%VITE_GIT_COMMIT%" in sha:
        raise CheckFailed(f"{tier}: the build-commit placeholder was never substituted ({_VERCEL_SHA_HINT})")
    if sha == "unknown":
        raise CheckFailed(
            f"{tier}: version unknown, the build was not given its commit "
            "(backend: --build-arg GIT_COMMIT; frontend: VERCEL_GIT_COMMIT_SHA)"
        )
    if not _SHA.match(sha):
        raise CheckFailed(f"{tier}: {sha[:60]!r} is not a commit sha")
    directory = TIER_DIRS[tier]
    completed = ctx.runner.run(
        ["git", "-C", str(REPO_ROOT), "diff", "--quiet", sha, release, "--", directory], 30
    )
    if completed.returncode == 0:
        return f"{tier} {sha[:12]} has the release's {directory} ({release[:12]})"
    if completed.returncode == 1:
        raise CheckFailed(
            f"{tier}: the deployed build {sha[:12]} differs from release {release[:12]} in {directory} "
            + ("(promote the staged deployment whose SHA is the release)" if tier == "frontend"
               else "(deploy the release commit)")
        )
    error = completed.stderr.lower()
    if any(marker in error for marker in ("not a valid", "bad object", "unknown revision", "not a commit", "bad revision")):
        raise CheckFailed(
            f"{tier}: {sha[:12]} is not in local history, so its {directory} cannot be compared with "
            f"{release[:12]} (git fetch, then re-run if you expected it)"
        )
    raise Tooling(f"git diff exited {completed.returncode}: {first_line(completed.stderr)}")


_META_TAG = re.compile(r"<meta\b[^>]*\bname\s*=\s*[\"']build-commit[\"'][^>]*>", re.I)
_CONTENT = re.compile(r"\bcontent\s*=\s*[\"']([^\"']*)[\"']", re.I)


def check_commit_frontend(ctx: Context) -> str:
    resp = ctx.frontend_index()
    if is_challenge(resp):
        raise Tooling("mealy.dev/index.html: Cloudflare challenge page")
    if resp.status != 200:
        raise CheckFailed(f"frontend: {FRONTEND_ORIGIN}/index.html answered {resp.status}")
    sha = None
    tag = _META_TAG.search(resp.body)
    if tag:
        content = _CONTENT.search(tag.group(0))
        sha = content.group(1).strip() if content else ""
    return assert_deployed_matches(ctx, "frontend", sha)


def check_commit_backend(ctx: Context) -> str:
    body = ctx.healthz_body()
    if "version" not in body:
        raise CheckFailed("/healthz has no `version` key (a PR1b field: --skip=healthz_version only before PR1b is live)")
    version = body["version"]
    return assert_deployed_matches(ctx, "backend", version if isinstance(version, str) else repr(version))


def check_healthz(ctx: Context) -> str:
    failures, tooling, unreachable, answered = [], [], [], False
    for fetch in (ctx.healthz_body, ctx.healthz_fly_body):
        try:
            body = fetch()
            answered = True
            if body.get("status") != "ok":
                failures.append(f"/healthz status is {body.get('status')!r}, expected 'ok'")
        except CheckFailed as exc:
            answered = True
            failures.append(str(exc))
        except Unreachable as exc:
            unreachable.append(str(exc))
        except Tooling as exc:
            tooling.append(str(exc))
    if answered and unreachable:
        # The other path answered this laptop in this same run, so the network is fine and
        # the unreachable path is a production fault (incident-diagnostics: fails only
        # through Cloudflare = the edge). Alone, an unreachable path stays exit 2.
        failures += [f"unreachable while the other path answered: {m}" for m in unreachable]
    else:
        tooling += unreachable
    if failures:
        raise CheckFailed("; ".join(failures + tooling))
    if tooling:
        raise Tooling("; ".join(tooling))
    return f"/healthz 200 status ok through Cloudflare and via {FLY_HOST}"


def check_jobs_fresh(ctx: Context) -> str:
    body = ctx.healthz_body()
    if "jobs" not in body:
        raise CheckFailed("/healthz has no `jobs` key (a PR1b field: --skip=healthz_jobs only before PR1b is live)")
    jobs = body["jobs"]

    def paused() -> None:
        # Called by jobs_verdict only after the rows passed the contract's shape rules.
        ran_after_the_pause(ctx, jobs["rows"])
        stale = sum(1 for row in jobs["rows"] if row["stale"])
        pause_verdict(ctx, PAUSABLE_GROUPS, f"background jobs ({stale} of {len(jobs['rows'])} stale, expected while paused)")

    return jobs_verdict(jobs, paused=paused)


def ran_after_the_pause(ctx: Context, rows: list[dict]) -> None:
    """A job that succeeded on a later day than a declared pause means that group was resumed
    and infra/paused.json was not emptied. Without this the daily cron would print PAUSE until
    review_by while the group runs, and could not notice it dying again: check 2, which catches
    a running paused group, is in the release group the cron never runs (found by
    /review-implementation's adversarial pass, M8 PR1b). The pause's own day is excluded,
    because the jobs ran that day before the stop.

    Whose pause the evidence speaks to: the four scheduled jobs start only when beat enqueues
    them (nothing else sends them by name) and run only on the worker. With the worker
    declared, a later success proves the worker ran, but not beat: a resumed worker also
    drains jobs queued before the pause. With only beat declared, the worker is expected to
    run and its queue drained on the pause day, so a later success proves beat ran (final
    review, M8 PR1b)."""
    pauses = ctx.pauses()
    pause = pauses.get("worker") or pauses.get("beat")
    if pause is None:
        return
    after = []
    for row in rows:
        ran = parse_time(row.get("last_success_at"))
        if ran is not None and ran.date() > pause.since:
            after.append(f"{row['label']} ({ran.date().isoformat()})")
    if after:
        raise CheckFailed(
            f"the {pause.group} ran after it was declared paused on {pause.since.isoformat()}: "
            + ", ".join(after)
            + f". If the resume is deliberate, empty infra/paused.json in a pull request; if not, stop the {pause.group}"
        )


def check_version_reported(ctx: Context) -> str:
    """Item 13: the cron asserts /healthz reports the deployed commit. Check 8 compares it with
    the release; this only needs it to be a real commit, so it runs between releases too."""
    body = ctx.healthz_body()
    if "version" not in body:
        raise CheckFailed("/healthz has no `version` key (a PR1b field: --skip=healthz_version only before PR1b is live)")
    version = body["version"]
    if version == "unknown":
        raise CheckFailed(
            "/healthz version is 'unknown': the image was built without `--build-arg GIT_COMMIT` (RUNBOOK §2 step 2)"
        )
    if not isinstance(version, str) or not _SHA.match(version):
        raise CheckFailed(f"/healthz version {str(version)[:40]!r} is not a commit SHA")
    return f"/healthz reports version {version[:12]}"


def check_restore_point(ctx: Context) -> str:
    notes, recent, tooling = [], [], []
    try:
        volumes = ctx.volume_snapshots()
        newest = max((t for _, times in volumes for t in times), default=None)
        ids = ", ".join(volume_id for volume_id, _ in volumes)
        if newest is None:
            notes.append(f"no volume snapshot ({ids})")
        else:
            notes.append(f"newest volume snapshot {human_age(ctx.now - newest)} old ({ids})")
            recent.append(ctx.now - newest <= RESTORE_POINT_MAX_AGE)
    except Tooling as exc:
        tooling.append(str(exc))
    try:
        state, times = ctx.wal_backups()
        if state == "disabled":
            notes.append("WAL backups disabled")
        elif not times:
            notes.append("no WAL backup listed")
        else:
            newest_wal = max(times)
            notes.append(f"newest WAL backup {human_age(ctx.now - newest_wal)} old")
            recent.append(ctx.now - newest_wal <= RESTORE_POINT_MAX_AGE)
    except Tooling as exc:
        tooling.append(str(exc))
    detail = "; ".join(notes)
    if any(recent):
        return detail + (f"; also: {'; '.join(tooling)}" if tooling else "")
    if tooling:
        raise Tooling(f"restore point unverified: {'; '.join(tooling)}" + (f" ({detail})" if detail else ""))
    raise CheckFailed(f"no restore point newer than 48 h: {detail}")


def check_origin_lock(ctx: Context) -> str:
    url = f"https://{API_HOST}{PROTECTED_PATH}"
    direct = ctx.http_get(url, resolve_ip=ctx.fly_ip())
    edge = ctx.http_get(url)
    for resp in (direct, edge):
        if is_challenge(resp):
            raise Tooling(f"{url}: Cloudflare challenge page instead of the app")
    problems = []
    if direct.status == 429 or edge.status == 429:
        problems.append("429 rate-limited, unverified: retry after the 10 s window")
    if direct.status not in (421, 429):
        problems.append(
            f"origin lock OPEN: straight to the Fly IP answered {direct.status}, expected 421 "
            "(break-glass left on, or the gate regressed)"
        )
    if edge.status == 421:
        problems.append(
            "through Cloudflare answered 421: the Transform Rule is not applied or ORIGIN_VERIFY_SECRET "
            "drifted; read the app.gate reason in `fly logs`"
        )
    elif edge.status not in (401, 429):
        problems.append(f"through Cloudflare answered {edge.status}, expected 401")
    if problems:
        raise CheckFailed("; ".join(problems))
    return f"{PROTECTED_PATH} straight to the Fly IP 421, through Cloudflare 401"


def check_break_glass(ctx: Context) -> str:
    body = ctx.healthz_body()
    if "gate_break_glass" not in body:
        raise CheckFailed(
            "/healthz has no `gate_break_glass` key (a PR1b field: --skip=healthz_gate_break_glass only "
            "before PR1b is live)"
        )
    value = body["gate_break_glass"]
    if value is False:
        return "gate_break_glass is false"
    if value is True:
        raise CheckFailed(
            "GATE_BREAK_GLASS is ON: the origin gate is bypassed; clear it by redeploying the running image "
            "from its release tag's checkout, without -e"
        )
    raise CheckFailed(f"gate_break_glass is {value!r}, not a boolean")


def check_vercel_headers(ctx: Context) -> str:
    index = ctx.frontend_index()
    route = ctx.http_get(f"{FRONTEND_ORIGIN}{SPA_ROUTE}")
    problems = []
    for label, resp in (("/index.html", index), (SPA_ROUTE, route)):
        if is_challenge(resp):
            raise Tooling(f"mealy.dev{label}: Cloudflare challenge page")
        control = resp.headers.get("cache-control", "")
        if resp.status != 200:
            problems.append(f"{label} answered {resp.status}")
        elif not ("max-age=0" in control and "must-revalidate" in control):
            problems.append(f"{label} cache-control is {control!r}, expected max-age=0, must-revalidate")
    asset_ref = re.search(r"[\"'](/assets/[^\"'?#]+\.js)[\"']", index.body)
    if not asset_ref:
        problems.append("/index.html references no /assets/*.js")
    else:
        asset = ctx.http_get(f"{FRONTEND_ORIGIN}{asset_ref.group(1)}")
        control = asset.headers.get("cache-control", "")
        if asset.status != 200:
            problems.append(f"{asset_ref.group(1)} answered {asset.status}")
        elif not ("immutable" in control and "max-age=31536000" in control):
            problems.append(f"{asset_ref.group(1)} cache-control is {control!r}, expected immutable")
    if problems:
        raise CheckFailed("; ".join(problems))
    return f"/index.html and {SPA_ROUTE} revalidate; /assets/* immutable"


def check_private_media(ctx: Context) -> str:
    """The credential-free half of the M7 private-media check. The logged-in
    `private, no-cache` on a 200 stays a manual DevTools step in RUNBOOK.md."""
    resp = ctx.http_get(f"https://{API_HOST}{PRIVATE_MEDIA_PATH}")
    if is_challenge(resp):
        raise Tooling(f"{PRIVATE_MEDIA_PATH}: Cloudflare challenge page")
    if resp.status != 401:
        raise CheckFailed(f"no-cookie private media answered {resp.status}, expected 401")
    control = resp.headers.get("cache-control", "")
    directives = cache_directives(control)
    edge_cache = resp.headers.get("cf-cache-status", "").upper()
    problems = []
    if not {"private", "no-store"} <= directives:
        problems.append(f"cache-control is {control!r}, expected 'private, no-store' unmodified")
    if directives & {"max-age", "s-maxage"}:
        problems.append("a max-age means Cloudflare's Browser Cache TTL rewrote the header")
    if edge_cache == "HIT":
        problems.append("cf-cache-status HIT: the edge cached a private-media response")
    if problems:
        raise CheckFailed("; ".join(problems))
    return f"no-cookie 401 carries cache-control {control!r} unmodified, cf-cache-status {edge_cache or 'absent'}"


# --- registry --------------------------------------------------------------


@dataclass(frozen=True)
class Check:
    number: str
    name: str
    group: str
    run: Callable[[Context], str]
    diagnostics: str  # anchor in infra/incident-diagnostics.md
    skip_key: str | None = None

    @property
    def label(self) -> str:
        return f"[{self.number}] {self.name}"


CHECKS = (
    Check("2", "groups-started", "release", check_groups_started, "web-or-a-process-group-is-down"),
    Check("3", "scale-reconciled", "release", check_scale, "machine-counts-drifted"),
    Check("4", "worker-roundtrip", "release", check_worker, "background-jobs-dead-worker-or-beat"),
    Check("8", "commit-frontend", "release", check_commit_frontend, "deployed-commit-does-not-match-the-release"),
    Check("8", "commit-backend", "release", check_commit_backend,
          "deployed-commit-does-not-match-the-release", "healthz_version"),
    Check("1", "healthz", "liveness", check_healthz, "web-or-a-process-group-is-down"),
    Check("1", "version-reported", "liveness", check_version_reported,
          "deployed-commit-does-not-match-the-release", "healthz_version"),
    Check("jobs", "jobs-fresh", "liveness", check_jobs_fresh, "background-jobs-dead-worker-or-beat", "healthz_jobs"),
    Check("9", "restore-point", "recoverability", check_restore_point, "no-recent-restore-point"),
    Check("5", "origin-lock", "edge", check_origin_lock, "421-from-the-origin-gate"),
    Check("glass", "break-glass-off", "edge", check_break_glass,
          "break-glass-the-origin-gate-during-a-cloudflare-outage", "healthz_gate_break_glass"),
    Check("7", "vercel-cache-headers", "edge", check_vercel_headers, "cache-headers-changed"),
    Check("6", "private-media-headers", "edge", check_private_media, "cache-headers-changed"),
)

TOOLING_DIAGNOSTICS = "tooling-failures-exit-2"


@dataclass
class Result:
    check: Check
    outcome: str  # pass | fail | skipped | paused | tooling
    detail: str


def run_check(check: Check, ctx: Context, skip: set[str]) -> Result:
    if check.skip_key and check.skip_key in skip:
        return Result(check, "skipped", f"skipped (--skip={check.skip_key}), not verified")
    try:
        return Result(check, "pass", check.run(ctx))
    except Paused as exc:
        return Result(check, "paused", str(exc))
    except CheckFailed as exc:
        return Result(check, "fail", str(exc))
    except Tooling as exc:
        return Result(check, "tooling", str(exc))
    except Exception as exc:
        # Python's own crash exit is 1, which here means "production is broken". An error
        # no check anticipated says nothing about production: report it as tooling and let
        # the remaining checks run.
        return Result(check, "tooling", f"unexpected {type(exc).__name__} in the check: {first_line(str(exc))}")


# --- self-test -------------------------------------------------------------


class NoProductionRunner(Runner):
    def run(self, argv: list[str], timeout: float) -> Completed:
        raise Tooling(f"self-test tried to contact production ({argv[0]}); this is a bug in the script")


def _self_test_case(group: str) -> tuple[Check, Context]:
    """One check from `group`, fed a known-bad fixture instead of production."""
    ctx = Context(NoProductionRunner(), now=datetime(2026, 9, 21, 17, 0, tzinfo=timezone.utc))
    ctx._memo["pauses"] = (True, {})  # the forced failure must fail whatever infra/paused.json says
    by_name = {c.name: c for c in CHECKS}
    if group == "release":
        # One more machine than the file pins, so no future pin can turn this green.
        try:
            counts = dict(ctx.scale())
        except CheckFailed:
            counts = {}  # check_scale raises the same failure, naming the file's problem
        extra = "web" if "web" in counts else next(iter(sorted(counts)), "web")
        counts[extra] = counts.get(extra, 0) + 1
        ctx._memo["machines"] = (True, [
            {"id": f"self-{g}{i}", "state": "started", "config": {"metadata": {"fly_process_group": g}}}
            for g, n in sorted(counts.items()) for i in range(n)
        ])
        return by_name["scale-reconciled"], ctx
    if group == "liveness":
        row = {"task": "app.tasks.sweep_abandoned_uploads", "label": "Unused photo cleanup",
               "interval_s": 3600, "last_success_at": "2026-09-21T10:00:00Z", "stale": True, "write_error": False}
        jobs = {"read": "ok", "read_at": "2026-09-21T16:59:50Z", "now": "2026-09-21T17:00:00Z", "rows": [row]}
        ctx._memo["healthz_cf"] = (True, {"status": "ok", "jobs": jobs})
        return by_name["jobs-fresh"], ctx
    if group == "recoverability":
        old = datetime(2026, 9, 18, 17, 0, tzinfo=timezone.utc)
        ctx._memo["volume_snapshots"] = (True, [("vol_selftest", [old])])
        ctx._memo["wal_backups"] = (True, ("disabled", []))
        return by_name["restore-point"], ctx
    ctx._memo["healthz_cf"] = (True, {"status": "ok", "gate_break_glass": True})
    return by_name["break-glass-off"], ctx


# --- main ------------------------------------------------------------------

_MARK = {"pass": "PASS ", "fail": "FAIL ", "skipped": "SKIP ", "paused": "PAUSE", "tooling": "ERROR"}


def report(results: list[Result], out, *, self_test: bool = False, paused_groups: tuple[str, ...] = ()) -> int:
    for r in results:
        line = f"{_MARK[r.outcome]} {r.check.label}: {r.detail}"
        if r.outcome == "fail":
            line += f"  → {DIAGNOSTICS}#{r.check.diagnostics}"
        elif r.outcome == "tooling":
            line += f"  → {DIAGNOSTICS}#{TOOLING_DIAGNOSTICS}"
        print(line, file=out)
    failed = [r for r in results if r.outcome == "fail"]
    tooling = [r for r in results if r.outcome == "tooling"]
    note = " (self-test: forced failure against a built-in fixture)" if self_test else ""
    if failed:
        print(f"exit 1 production: {', '.join(r.check.label for r in failed)}{note}", file=out)
        return 1
    if tooling:
        print(f"exit 2 tooling: {', '.join(r.check.label for r in tooling)}", file=out)
        return 2
    passed = sum(1 for r in results if r.outcome == "pass")
    skipped = sum(1 for r in results if r.outcome == "skipped")
    paused = sum(1 for r in results if r.outcome == "paused")
    summary = f"exit 0: {passed} passed, {skipped} skipped"
    if paused:
        declared = ", ".join(paused_groups) or "see infra/paused.json"
        summary += f", {paused} paused ({declared} declared in infra/paused.json)"
    print(summary, file=out)
    return 0


def _usage_error(message: str, out) -> int:
    print(f"exit 2 tooling: {message}", file=out)
    return 2


def _split(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def main(argv: list[str] | None = None, *, runner: Runner | None = None,
         now: datetime | None = None, out=None) -> int:
    out = out or sys.stdout
    parser = argparse.ArgumentParser(
        prog="release-smoke.py",
        description="M8 release smoke checks. Exit 0 pass, 1 production, 2 tooling.",
    )
    parser.add_argument("--only", default=",".join(GROUPS),
                        help=f"comma-separated groups (default: all of {', '.join(GROUPS)})")
    parser.add_argument("--skip", default="",
                        help=f"comma-separated PR1b-only assertions to skip: {', '.join(SKIP_KEYS)}")
    parser.add_argument("--release-commit",
                        help="the commit being released; required when the release group runs")
    parser.add_argument("--self-test", action="store_true",
                        help="fail one check in the selected groups against a fixture; contacts nothing")
    args = parser.parse_args(argv)

    if tomllib is None:
        return _usage_error("Python 3.11+ is required (tomllib)", out)
    groups = _split(args.only)
    unknown = sorted(set(groups) - set(GROUPS))
    if unknown or not groups:
        return _usage_error(f"unknown group(s) {unknown or groups}; choose from {', '.join(GROUPS)}", out)
    skip = set(_split(args.skip))
    if skip - set(SKIP_KEYS):
        return _usage_error(f"unknown --skip key(s) {sorted(skip - set(SKIP_KEYS))}; choose from {', '.join(SKIP_KEYS)}", out)

    if args.self_test:
        group = next(g for g in GROUPS if g in groups)
        check, ctx = _self_test_case(group)
        return report([run_check(check, ctx, set())], out, self_test=True)

    runner = runner or Runner()
    release_commit = None
    if "release" in groups:
        if not args.release_commit:
            return _usage_error("--release-commit is required when the release group runs", out)
        try:
            resolved = runner.run(
                ["git", "-C", str(REPO_ROOT), "rev-parse", "--verify", "--quiet", f"{args.release_commit}^{{commit}}"], 30
            )
        except Tooling as exc:  # git missing or hung
            return _usage_error(str(exc), out)
        if resolved.returncode != 0 or not resolved.stdout.strip():
            return _usage_error(f"--release-commit {args.release_commit!r} is not a commit in this checkout", out)
        release_commit = resolved.stdout.strip()

    ctx = Context(runner, release_commit=release_commit, now=now)
    results = [run_check(check, ctx, skip) for check in CHECKS if check.group in groups]
    try:
        paused_groups = tuple(sorted(ctx.pauses()))
    except (CheckFailed, Tooling):
        paused_groups = ()  # already reported as an ERROR line by the checks that read it
    return report(results, out, paused_groups=paused_groups)


if __name__ == "__main__":
    try:
        code = main()
    except Exception as exc:  # a crash must never read as exit 1 (production)
        print(f"exit 2 tooling: unexpected {type(exc).__name__} in the script: {first_line(str(exc))}")
        code = 2
    sys.exit(code)
