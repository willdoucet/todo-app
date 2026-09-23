#!/usr/bin/env python3
"""Read-only drift check: live Cloudflare config vs infra/cloudflare-state.md (M8 item 9).

Runs on the operator's host with a read-only token in the shell, never in CI
(v1 keeps the token local; scheduling it is a v1.1 item):

    export CLOUDFLARE_API_TOKEN=...   # read-only; see RUNBOOK.md for the scopes
    python3 infra/cloudflare-drift.py

What it compares, each against the field cloudflare-state.md records:

    waf-rate-limit      the /auth/* rule: expression, requests / period / IP, action,
                        block duration, enabled
    origin-lock         the Transform Rule: present, enabled, expression, and that it
                        SETS the X-Origin-Verify header. Presence only: the header's
                        value is dropped the moment the response is parsed, so it can
                        reach no output, diff, or error message (structural, not a
                        discipline; a test feeds a dummy value and greps for it)
    browser-cache-ttl   "Respect Existing Headers" (API value 0); private media relies on it
    access-apps         as many Access applications on the zone as the file lists (0 today).
                        Counts only: names are not compared, so an app swapped for another
                        reads as recorded. Unreachable while the file expects none; compare
                        names once the first app is recorded (/review-implementation, M8).
                        The API lists the whole account, so an app whose hostnames are all
                        on another zone is left out; one with no readable hostname counts
                        (/final-review, M8)
    bot-fight-mode      reported; drift only once the file records an intent

Exit: 0 no drift · 1 drift (named) · 2 tooling (token unset or rejected, network,
an API permission missing, cloudflare-state.md unreadable or missing a field this
reads, or an error the script did not anticipate: Python's own crash exit is 1).
The token is read from the environment and never printed, logged or passed as an
argument. Standard library only.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

STATE_FILE = Path(__file__).resolve().parent / "cloudflare-state.md"
API = "https://api.cloudflare.com/client/v4"
TOKEN_VAR = "CLOUDFLARE_API_TOKEN"


class Drift(Exception):
    """Exit 1: live config differs from the recorded intent."""


class Tooling(Exception):
    """Exit 2: the comparison could not be made."""


# --- intent: cloudflare-state.md -------------------------------------------


@dataclass(frozen=True)
class Intent:
    account_id: str
    zone_id: str
    zone_name: str
    waf_name: str
    waf_expression: str
    waf_requests: int
    waf_period: int
    waf_action: str
    waf_timeout: int
    waf_enabled: bool
    lock_name: str
    lock_expression: str
    lock_header: str
    lock_enabled: bool
    cache_ttl: int  # seconds; 0 = Respect Existing Headers
    access_apps: tuple[str, ...]  # applications the file does not mark REMOVED
    bot_fight_mode: bool | None  # None = not yet recorded


def _sections(text: str) -> dict[str, str]:
    sections, heading, lines = {}, "", []
    for line in text.splitlines():
        if line.startswith("## "):
            sections[heading] = "\n".join(lines)
            heading, lines = line[3:].strip(), []
        else:
            lines.append(line)
    sections[heading] = "\n".join(lines)
    return sections


def _section(sections: dict[str, str], prefix: str) -> str:
    for heading, body in sections.items():
        if heading.startswith(prefix):
            return body
    raise Tooling(f"cloudflare-state.md has no section starting '## {prefix}'")


def _field(body: str, pattern: str, what: str) -> re.Match:
    match = re.search(pattern, body, re.M)
    if not match:
        raise Tooling(f"cloudflare-state.md: cannot find {what}; the file's shape changed")
    return match


_TTL_UNITS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}


def parse_intent(text: str) -> Intent:
    sections = _sections(text)
    head = sections[""]
    waf = _section(sections, "WAF")
    lock = _section(sections, "Transform Rules")
    cache = _section(sections, "Caching")
    threshold = _field(waf, r"^Threshold: \*\*(\d+) requests / (\d+) seconds / IP\*\*", "the WAF threshold")
    ttl_text = " ".join(_field(cache, r"Browser Cache TTL\)?: \*\*([^*]+)\*\*", "the Browser Cache TTL").group(1).split())
    if ttl_text.lower() == "respect existing headers":
        cache_ttl = 0
    else:
        ttl = re.fullmatch(r"(\d+) (second|minute|hour|day)s?", ttl_text.lower())
        if not ttl:
            raise Tooling(f"cloudflare-state.md: Browser Cache TTL {ttl_text!r} is not a duration")
        cache_ttl = int(ttl.group(1)) * _TTL_UNITS[ttl.group(2)]
    apps = tuple(
        heading for heading in sections
        if heading.startswith("Access — Application") and "REMOVED" not in heading
    )
    bot = None
    for heading, body in sections.items():
        if heading.startswith("Security — Bot Fight Mode"):
            value = _field(body, r"^Setting[^:\n]*: \*\*([^*]+)\*\*", "the Bot Fight Mode setting").group(1).strip().lower()
            bot = {"on": True, "off": False}.get(value)  # "not yet recorded" → None
    return Intent(
        account_id=_field(head, r"Cloudflare account ID: ([0-9a-f]{32})", "the account ID").group(1),
        zone_id=_field(head, r"zone ID: ([0-9a-f]{32})", "the zone ID").group(1),
        zone_name=_field(head, r"Zone: ([a-z0-9.-]+) \(zone ID", "the zone name").group(1),
        waf_name=_field(waf, r"^Rule name: (.+?)\s*$", "the WAF rule name").group(1),
        waf_expression=_field(waf, r"^Match: `(.+)`\s*$", "the WAF match expression").group(1),
        waf_requests=int(threshold.group(1)),
        waf_period=int(threshold.group(2)),
        waf_action=_field(waf, r"^Action: (\w+)", "the WAF action").group(1).lower(),
        waf_timeout=int(_field(waf, r"^Duration: (\d+) seconds", "the WAF block duration").group(1)),
        waf_enabled=_field(waf, r"^Status: (\w+)", "the WAF status").group(1).lower() == "active",
        lock_name=_field(lock, r"^Rule name: (.+?)\s*$", "the Transform Rule name").group(1),
        lock_expression=_field(lock, r"`(\(http\.host [^`]*\))`", "the Transform Rule expression").group(1),
        lock_header=_field(lock, r"Header name: `([^`]+)`", "the Transform Rule header name").group(1),
        lock_enabled=_field(lock, r"^Status: \*\*(\w+)", "the Transform Rule status").group(1).lower() == "active",
        cache_ttl=cache_ttl,
        access_apps=apps,
        bot_fight_mode=bot,
    )


# --- live: the Cloudflare API ----------------------------------------------

Fetch = Callable[[str, str], tuple[int, str]]  # (url, token) -> (status, body)


def urllib_fetch(url: str, token: str) -> tuple[int, str]:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise Tooling(f"cannot reach the Cloudflare API: {getattr(exc, 'reason', exc)}")


class Api:
    def __init__(self, fetch: Fetch, token: str):
        self._fetch = fetch
        self._token = token

    def get(self, path: str, scope: str, *, missing_ok: bool = False):
        """The `result` of a v4 GET. Never raises with the body in the message: an
        error prints Cloudflare's error codes, not the response."""
        status, body = self._fetch(f"{API}{path}", self._token)
        if status in (401, 403):
            raise Tooling(
                f"{path}: HTTP {status}. {TOKEN_VAR} was rejected or lacks '{scope}' (value not shown)"
            )
        if status == 404 and missing_ok:
            return None
        try:
            payload = json.loads(body)
        except ValueError:
            raise Tooling(f"{path}: HTTP {status} with a non-JSON body")
        if status != 200 or not isinstance(payload, dict) or not payload.get("success"):
            codes = [e.get("code") for e in (payload.get("errors") or []) if isinstance(e, dict)] if isinstance(payload, dict) else []
            raise Tooling(f"{path}: HTTP {status}, Cloudflare error codes {codes}")
        return payload.get("result")


def _rules(ruleset) -> list[dict]:
    if ruleset is None:
        return []
    rules = ruleset.get("rules") if isinstance(ruleset, dict) else None
    return [r for r in rules or [] if isinstance(r, dict)]


def _norm(expression: object) -> str:
    return " ".join(str(expression or "").split())


def sanitize_transform_rule(rule: dict) -> dict:
    """Keep what the diff needs, drop everything else. Header *values* never survive
    this function, whatever shape the API returns them in."""
    headers = ((rule.get("action_parameters") or {}).get("headers") or {})
    return {
        "description": rule.get("description"),
        "enabled": rule.get("enabled"),
        "expression": rule.get("expression"),
        "action": rule.get("action"),
        "headers": {
            str(name).lower(): (spec.get("operation") if isinstance(spec, dict) else None)
            for name, spec in headers.items()
        },
    }


# --- comparisons -----------------------------------------------------------


def compare_waf(intent: Intent, api: Api) -> str:
    ruleset = api.get(f"/zones/{intent.zone_id}/rulesets/phases/http_ratelimit/entrypoint",
                      "Zone WAF: Read", missing_ok=True)
    rule = next((r for r in _rules(ruleset) if r.get("description") == intent.waf_name), None)
    if rule is None:
        raise Drift(f"rate-limit rule '{intent.waf_name}' is missing from the zone")
    limit = rule.get("ratelimit") or {}
    problems = []
    if _norm(rule.get("expression")) != _norm(intent.waf_expression):
        problems.append(f"expression is {rule.get('expression')!r}, intent {intent.waf_expression!r}")
    if (limit.get("requests_per_period"), limit.get("period")) != (intent.waf_requests, intent.waf_period):
        problems.append(
            f"threshold is {limit.get('requests_per_period')} / {limit.get('period')} s, "
            f"intent {intent.waf_requests} / {intent.waf_period} s"
        )
    if "ip.src" not in (limit.get("characteristics") or []):
        problems.append("the limit is not counted per IP (no ip.src characteristic)")
    if str(rule.get("action", "")).lower() != intent.waf_action:
        problems.append(f"action is {rule.get('action')!r}, intent {intent.waf_action!r}")
    if limit.get("mitigation_timeout") != intent.waf_timeout:
        problems.append(f"block duration is {limit.get('mitigation_timeout')} s, intent {intent.waf_timeout} s")
    if bool(rule.get("enabled")) != intent.waf_enabled:
        problems.append(f"enabled is {rule.get('enabled')}, intent {intent.waf_enabled}")
    if problems:
        raise Drift(f"'{intent.waf_name}': " + "; ".join(problems))
    return (f"'{intent.waf_name}' {intent.waf_requests} requests / {intent.waf_period} s / IP, "
            f"{intent.waf_action} {intent.waf_timeout} s, {'active' if intent.waf_enabled else 'inactive'}")


def compare_origin_lock(intent: Intent, api: Api) -> str:
    ruleset = api.get(f"/zones/{intent.zone_id}/rulesets/phases/http_request_late_transform/entrypoint",
                      "Transform Rules: Read", missing_ok=True)
    rules = [sanitize_transform_rule(r) for r in _rules(ruleset)]
    del ruleset  # the unsanitized response, header value included, goes no further
    rule = next((r for r in rules if r["description"] == intent.lock_name), None)
    if rule is None:
        raise Drift(f"Transform Rule '{intent.lock_name}' is missing: every request will 421")
    problems = []
    if bool(rule["enabled"]) != intent.lock_enabled:
        problems.append(f"enabled is {rule['enabled']}, intent {intent.lock_enabled}")
    if _norm(rule["expression"]) != _norm(intent.lock_expression):
        problems.append(f"expression is {rule['expression']!r}, intent {intent.lock_expression!r}")
    operation = rule["headers"].get(intent.lock_header.lower())
    if operation is None:
        problems.append(f"does not set {intent.lock_header}")
    elif operation != "set":
        problems.append(f"{intent.lock_header} operation is {operation!r}, intent 'set' (Set static)")
    if problems:
        raise Drift(f"'{intent.lock_name}': " + "; ".join(problems))
    return f"'{intent.lock_name}' present, enabled, sets {intent.lock_header} (value not read)"


def compare_cache_ttl(intent: Intent, api: Api) -> str:
    setting = api.get(f"/zones/{intent.zone_id}/settings/browser_cache_ttl", "Zone Settings: Read")
    value = setting.get("value") if isinstance(setting, dict) else None
    shown = lambda v: "Respect Existing Headers" if v == 0 else f"{v} s"
    if value != intent.cache_ttl:
        raise Drift(f"Browser Cache TTL is {shown(value)}, intent {shown(intent.cache_ttl)}; private media relies on it")
    return shown(value)


def _app_hosts(app: dict) -> set[str]:
    """Every hostname an Access application names, across the fields the v4 API has used
    for it: `domain`, `self_hosted_domains`, `destinations[].uri`."""
    values = [app.get("domain")]
    for key in ("self_hosted_domains", "destinations"):
        entries = app.get(key)
        if isinstance(entries, list):
            values += [e.get("uri") or e.get("hostname") if isinstance(e, dict) else e for e in entries]
    hosts = set()
    for value in values:
        if isinstance(value, str) and value.strip():
            host = value.strip().lower().split("://")[-1].split("/")[0].split(":")[0]
            hosts.add(host.removeprefix("*."))
    return hosts


def _on_zone(app: dict, zone: str) -> bool:
    """Counted unless every hostname it names is on another zone. An app whose hostname
    cannot be read counts, so an API shape change is loud drift, never a hidden gate."""
    hosts = _app_hosts(app)
    return not hosts or any(host == zone or host.endswith(f".{zone}") for host in hosts)


def compare_access_apps(intent: Intent, api: Api) -> str:
    apps = api.get(f"/accounts/{intent.account_id}/access/apps", "Access: Apps and Policies: Read") or []
    if not isinstance(apps, list):
        raise Tooling("/access/apps: the result is not a list (the API's shape changed?)")
    apps = [a for a in apps if isinstance(a, dict)]
    on_zone = [a for a in apps if _on_zone(a, intent.zone_name)]
    names = sorted(str(a.get("name", "?")) for a in on_zone)
    elsewhere = len(apps) - len(on_zone)
    if len(names) != len(intent.access_apps):
        raise Drift(
            f"{len(names)} Access application(s) on {intent.zone_name} ({', '.join(names) or 'none'}), "
            f"the file lists {len(intent.access_apps)}"
        )
    return (f"{len(names)} Access application(s) on {intent.zone_name}, as recorded"
            + (f" ({elsewhere} on other zones, not compared)" if elsewhere else ""))


def compare_bot_fight_mode(intent: Intent, api: Api) -> str:
    result = api.get(f"/zones/{intent.zone_id}/bot_management", "Bot Management: Read") or {}
    live = result.get("fight_mode") if isinstance(result, dict) else None
    shown = {True: "on", False: "off"}.get(live, repr(live))
    if intent.bot_fight_mode is None:
        return f"live {shown}; not yet recorded in cloudflare-state.md (record it)"
    if live != intent.bot_fight_mode:
        raise Drift(f"Bot Fight Mode is {shown}, intent {'on' if intent.bot_fight_mode else 'off'}")
    return shown


COMPARISONS = (
    ("waf-rate-limit", compare_waf),
    ("origin-lock", compare_origin_lock),
    ("browser-cache-ttl", compare_cache_ttl),
    ("access-apps", compare_access_apps),
    ("bot-fight-mode", compare_bot_fight_mode),
)


def main(argv=None, *, fetch: Fetch = urllib_fetch, environ=None, state_file: Path = STATE_FILE,
         out=None, err=None) -> int:
    out, err = out or sys.stdout, err or sys.stderr
    environ = os.environ if environ is None else environ
    if argv:
        print("usage: cloudflare-drift.py  (no arguments; token from $CLOUDFLARE_API_TOKEN)", file=err)
        return 2
    token = environ.get(TOKEN_VAR, "").strip()
    if not token:
        print(f"exit 2 tooling: {TOKEN_VAR} is not set (a read-only token; see infra/RUNBOOK.md)", file=out)
        return 2
    try:
        intent = parse_intent(state_file.read_text())
    except Tooling as exc:
        print(f"exit 2 tooling: {exc}", file=out)
        return 2
    except OSError as exc:
        print(f"exit 2 tooling: cannot read {state_file.name}: {exc.strerror or exc}", file=out)
        return 2
    api = Api(fetch, token)
    drifted, tooling = [], []
    for name, compare in COMPARISONS:
        try:
            print(f"OK     {name}: {compare(intent, api)}", file=out)
        except Drift as exc:
            drifted.append(name)
            print(f"DRIFT  {name}: {exc}", file=out)
        except Tooling as exc:
            tooling.append(name)
            print(f"ERROR  {name}: {exc}", file=out)
        except Exception as exc:
            # An API shape nothing here anticipated. The message is the exception type
            # only: its text could quote a response value, and the Transform Rule carries
            # the origin secret.
            tooling.append(name)
            print(f"ERROR  {name}: unexpected {type(exc).__name__} (the API's shape changed?)", file=out)
    if drifted:
        print(f"exit 1 drift: {', '.join(drifted)} (fix the dashboard, or update cloudflare-state.md "
              "in the same commit that records a deliberate change)", file=out)
        return 1
    if tooling:
        print(f"exit 2 tooling: {', '.join(tooling)}", file=out)
        return 2
    print("exit 0: no drift", file=out)
    return 0


if __name__ == "__main__":
    try:
        code = main(sys.argv[1:])
    except Exception as exc:  # a crash must never read as exit 1 (drift); type only, no text
        print(f"exit 2 tooling: unexpected {type(exc).__name__} in the script")
        code = 2
    sys.exit(code)
