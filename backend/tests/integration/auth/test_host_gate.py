"""Integration tests for the production host gate.

When ``APP_ENV=production`` the middleware in ``app.main`` rejects every
non-/healthz request that did not come through Cloudflare. Two checks, both
required:

- ``Host`` must equal ``PUBLIC_API_HOST`` (Adversarial review run 2). This
  turns away casual ``*.fly.dev`` traffic, but the client writes the Host
  header, so on its own it proves nothing: on 2026-09-11 a request sent
  straight to the Fly IP with ``Host: api.mealy.dev`` passed it.
- ``X-Origin-Verify`` must equal ``ORIGIN_VERIFY_SECRET``. A Cloudflare
  Transform Rule sets it on every request for the API host
  (``infra/cloudflare-state.md``); a caller that skips Cloudflare cannot
  know it.

Every failure returns the same 421 body, so a caller cannot tell which check
it failed. The operator can (M8 item 5): each rejection logs one ``app.gate``
WARNING whose ``reason`` names one of six branches (``app.gate_logging``). The
gate is a no-op outside production so dev/test can use any Host header.

The fixture: ``production_gate`` sets the three env vars the gate reads, and a
test that needs a different branch overrides one of them with ``monkeypatch``
(``PUBLIC_API_HOST`` unset → ``public_api_host_unconfigured``, an empty
``ORIGIN_VERIFY_SECRET`` → ``origin_verify_secret_empty``). The Host and origin
header on each request pick the other four.
"""

from __future__ import annotations

import json
import logging

import pytest

from app import gate_logging
from tests.integration.auth.test_log_hygiene import _record_strings

# Test-only value. The production secret exists only as a Fly secret and in the
# Cloudflare Transform Rule.
SECRET = "test-origin-verify-secret-0123456789"
VIA_CLOUDFLARE = {"Host": "api.mealy.dev", "X-Origin-Verify": SECRET}
REJECTED = {"detail": "host_not_allowed"}
REJECTED_BYTES = b'{"detail":"host_not_allowed"}'


@pytest.fixture
def production_gate(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("PUBLIC_API_HOST", "api.mealy.dev")
    monkeypatch.setenv("ORIGIN_VERIFY_SECRET", SECRET)
    monkeypatch.delenv("GATE_BREAK_GLASS", raising=False)


@pytest.fixture
def gate_log(caplog):
    caplog.set_level(logging.WARNING, logger="app.gate")
    return caplog


def gate_records(caplog) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.name == "app.gate"]


def assert_one_rejection(caplog, reason: str) -> logging.LogRecord:
    records = gate_records(caplog)
    assert [r.reason for r in records] == [reason]
    record = records[0]
    assert record.levelno == logging.WARNING
    assert record.event == "host_gate"
    assert record.outcome == "rejected"
    return record


@pytest.mark.asyncio
async def test_gate_disabled_when_app_env_not_production(client, monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    r = await client.get(
        "/auth/status",
        headers={"Host": "mealy-app-prod.fly.dev"},
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_gate_allows_request_through_cloudflare(client, production_gate, gate_log):
    r = await client.get("/auth/status", headers=VIA_CLOUDFLARE)
    assert r.status_code == 200
    assert gate_records(gate_log) == []


@pytest.mark.asyncio
async def test_gate_with_port_in_host_header_still_matches(client, production_gate):
    """Browsers may send Host: api.mealy.dev:443 — our middleware strips
    the port before comparing."""
    r = await client.get(
        "/auth/status", headers={**VIA_CLOUDFLARE, "Host": "api.mealy.dev:443"}
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_gate_allows_healthz_unconditionally(client, production_gate, gate_log):
    """Fly health checks carry neither the public Host nor the origin header."""
    r = await client.get("/healthz", headers={"Host": "mealy-app-prod.fly.dev"})
    assert r.status_code == 200
    assert gate_records(gate_log) == []


@pytest.mark.asyncio
async def test_gate_blocks_direct_fly_origin_for_auth_routes(
    client, production_gate, gate_log
):
    """Wrong Host with a valid origin header: the Host check alone rejects."""
    r = await client.get(
        "/auth/status",
        headers={**VIA_CLOUDFLARE, "Host": "mealy-app-prod.fly.dev"},
    )
    assert r.status_code == 421
    assert r.json() == REJECTED
    assert_one_rejection(gate_log, gate_logging.HOST_MISMATCH)


@pytest.mark.asyncio
async def test_gate_blocks_existing_business_routes_too(
    client, production_gate, gate_log
):
    """Not just /auth/* — every backend path except /healthz."""
    r = await client.get(
        "/family-members/",
        headers={**VIA_CLOUDFLARE, "Host": "mealy-app-prod.fly.dev"},
    )
    assert r.status_code == 421
    assert_one_rejection(gate_log, gate_logging.HOST_MISMATCH)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/auth/status"),
        ("POST", "/auth/login"),
        ("GET", "/family-members/"),
        ("GET", "/uploads/item-icons/any-key.png"),
    ],
)
async def test_gate_blocks_public_host_without_origin_header(
    client, production_gate, gate_log, method, path
):
    """The 2026-09-11 bypass: `curl --resolve api.mealy.dev:443:<fly-ip>`
    reaches Fly with the right Host and never passes Cloudflare, so it skips
    the /auth/* rate limit. With no origin header it must stop here, before
    any route runs (POST /auth/login would otherwise spend argon2 time)."""
    body = {"email": "a@example.com", "password": "guess"} if method == "POST" else None
    r = await client.request(
        method, path, headers={"Host": "api.mealy.dev"}, json=body
    )
    assert r.status_code == 421
    assert r.json() == REJECTED
    assert_one_rejection(gate_log, gate_logging.ORIGIN_VERIFY_ABSENT)


@pytest.mark.asyncio
async def test_gate_blocks_wrong_origin_header(client, production_gate, gate_log):
    r = await client.get(
        "/auth/status", headers={**VIA_CLOUDFLARE, "X-Origin-Verify": SECRET[:-1]}
    )
    assert r.status_code == 421
    assert r.json() == REJECTED
    assert_one_rejection(gate_log, gate_logging.ORIGIN_VERIFY_MISMATCH)


@pytest.mark.asyncio
async def test_gate_rejects_non_ascii_origin_header_without_crashing(
    client, production_gate, gate_log
):
    """hmac.compare_digest raises TypeError for non-ASCII str arguments. A
    forged header must be a 421, never an unhandled 500."""
    r = await client.get(
        "/auth/status",
        headers={"Host": "api.mealy.dev", "X-Origin-Verify": "sécret".encode("latin-1")},
    )
    assert r.status_code == 421
    assert r.json() == REJECTED
    assert_one_rejection(gate_log, gate_logging.ORIGIN_VERIFY_MISMATCH)


@pytest.mark.asyncio
async def test_gate_fails_closed_when_origin_secret_missing(
    client, production_gate, gate_log, monkeypatch
):
    """An empty secret must never match an empty header — comparing "" with
    "" would open the gate to everyone. Production also refuses to boot
    without the secret; this is the request-time backstop."""
    monkeypatch.setenv("ORIGIN_VERIFY_SECRET", "")
    for headers in (
        {"Host": "api.mealy.dev"},
        {"Host": "api.mealy.dev", "X-Origin-Verify": ""},
    ):
        gate_log.clear()
        r = await client.get("/auth/status", headers=headers)
        assert r.status_code == 421
        assert_one_rejection(gate_log, gate_logging.ORIGIN_VERIFY_SECRET_EMPTY)

    monkeypatch.delenv("ORIGIN_VERIFY_SECRET")
    gate_log.clear()
    r = await client.get("/auth/status", headers={"Host": "api.mealy.dev"})
    assert r.status_code == 421
    assert_one_rejection(gate_log, gate_logging.ORIGIN_VERIFY_SECRET_EMPTY)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "spoof_host",
    ["api.mealy.dev/healthz?", "api.mealy.dev/healthz#", "evil/healthz"],
)
async def test_gate_healthz_exemption_cannot_be_spoofed_via_host(
    client, production_gate, gate_log, spoof_host
):
    """A Host header that makes `request.url.path` parse as "/healthz" must not
    exempt a request the router still dispatches to a real route. The gate
    matches on scope["path"], so /auth/status stays gated (421) here."""
    r = await client.get("/auth/status", headers={"Host": spoof_host})
    assert r.status_code == 421
    assert r.json() == REJECTED
    assert_one_rejection(gate_log, gate_logging.HOST_MISMATCH)


@pytest.mark.asyncio
async def test_gate_blocks_when_public_api_host_not_set(
    client, production_gate, gate_log, monkeypatch
):
    """Production mode but PUBLIC_API_HOST unset → reject everything (fail closed)."""
    monkeypatch.delenv("PUBLIC_API_HOST", raising=False)
    r = await client.get("/auth/status", headers=VIA_CLOUDFLARE)
    assert r.status_code == 421
    assert_one_rejection(gate_log, gate_logging.PUBLIC_API_HOST_UNCONFIGURED)


@pytest.mark.asyncio
async def test_gate_rejects_a_host_that_is_only_a_port(client, production_gate, gate_log):
    """``Host: :443`` strips to "" — the empty-Host branch. A request with no
    Host at all cannot be sent through h11 (it answers 400 before the app) or
    this test client, so the missing-header case is pinned in
    ``tests/unit/test_gate_reason.py`` instead."""
    r = await client.get("/auth/status", headers={**VIA_CLOUDFLARE, "Host": ":443"})
    assert r.status_code == 421
    assert r.json() == REJECTED
    assert_one_rejection(gate_log, gate_logging.HOST_ABSENT)


def _one_request_per_reason():
    """(env overrides, headers) that reach each of the six reasons."""
    return {
        gate_logging.PUBLIC_API_HOST_UNCONFIGURED: ({"PUBLIC_API_HOST": None}, VIA_CLOUDFLARE),
        gate_logging.HOST_ABSENT: ({}, {**VIA_CLOUDFLARE, "Host": ":443"}),
        gate_logging.HOST_MISMATCH: ({}, {**VIA_CLOUDFLARE, "Host": "mealy-app-prod.fly.dev"}),
        gate_logging.ORIGIN_VERIFY_SECRET_EMPTY: ({"ORIGIN_VERIFY_SECRET": ""}, VIA_CLOUDFLARE),
        gate_logging.ORIGIN_VERIFY_ABSENT: ({}, {"Host": "api.mealy.dev"}),
        gate_logging.ORIGIN_VERIFY_MISMATCH: ({}, {**VIA_CLOUDFLARE, "X-Origin-Verify": "wrong"}),
    }


@pytest.mark.asyncio
async def test_every_rejection_reason_returns_a_byte_identical_body(
    client, production_gate, gate_log, monkeypatch
):
    """REVIEW_CHECKLIST → pytest: byte-identical failure responses compare
    bodies across every failure reason. The reason goes to the log, never to
    the caller."""
    cases = _one_request_per_reason()
    assert set(cases) == set(gate_logging.REASONS)
    bodies = {}
    for reason, (env, headers) in cases.items():
        with monkeypatch.context() as m:
            for name, value in env.items():
                if value is None:
                    m.delenv(name, raising=False)
                else:
                    m.setenv(name, value)
            gate_log.clear()
            r = await client.get("/auth/status", headers=headers)
        assert r.status_code == 421, reason
        assert_one_rejection(gate_log, reason)
        bodies[reason] = (r.content, r.headers.get("content-type"))
    assert set(bodies.values()) == {(REJECTED_BYTES, "application/json")}


@pytest.mark.asyncio
async def test_gate_logging_failure_does_not_change_response(
    client, production_gate, monkeypatch
):
    """CEO review 2A: an observability bug must not take down the auth boundary.
    ``app.main`` looks the emitter up on ``app.gate_logging`` at call time, so
    that is where it is patched; the call list is the negative control proving
    the patch took effect."""
    calls = []

    def raising_emitter(request, reason):
        calls.append(reason)
        raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "hostile header")

    monkeypatch.setattr(gate_logging, "emit_gate_rejection", raising_emitter)
    r = await client.get("/auth/status", headers={"Host": "api.mealy.dev"})
    assert calls == [gate_logging.ORIGIN_VERIFY_ABSENT]
    assert r.status_code == 421
    assert r.content == REJECTED_BYTES


@pytest.mark.asyncio
async def test_gate_line_carries_no_secret_no_header_value_and_the_proxy_hop(
    client, production_gate, gate_log
):
    """The IP is the hop Fly's proxy saw, the LAST ``X-Forwarded-For`` entry — never
    ``CF-Connecting-IP`` or the first ``X-Forwarded-For`` entry, which are
    attacker-controlled on a request that went around the edge. Headers are logged by
    presence and length only; the path is truncated."""
    presented = "attacker-presented-origin-value"
    long_path = "/auth/" + "x" * 300
    r = await client.get(
        long_path,
        headers={
            "Host": "api.mealy.dev",
            "X-Origin-Verify": presented,
            "CF-Connecting-IP": "203.0.113.66",
            "X-Forwarded-For": "198.51.100.77, 10.0.0.1",
        },
    )
    assert r.status_code == 421
    record = assert_one_rejection(gate_log, gate_logging.ORIGIN_VERIFY_MISMATCH)
    assert record.ip == "10.0.0.1"  # the last hop, the one Fly's proxy writes
    assert record.host_present is True
    assert record.host_length == len("api.mealy.dev")
    assert record.origin_verify_present is True
    assert record.origin_verify_length == len(presented)
    assert record.path == long_path[: gate_logging.PATH_MAX_LENGTH]
    assert record.request_id
    logged = " ".join(_record_strings(record))
    for forbidden in (SECRET, presented, "203.0.113.66", "198.51.100.77"):
        assert forbidden not in logged


@pytest.mark.asyncio
async def test_gate_ip_without_a_forwarded_header_is_the_socket_peer(client, production_gate, gate_log):
    await client.get("/auth/status", headers={"Host": "api.mealy.dev"})
    assert assert_one_rejection(gate_log, gate_logging.ORIGIN_VERIFY_ABSENT).ip == "127.0.0.1"


@pytest.mark.asyncio
async def test_gate_ip_is_not_forgeable_under_uvicorns_proxy_headers(production_gate, gate_log):
    """Production runs uvicorn with ``--proxy-headers --forwarded-allow-ips=*``, which puts the
    FIRST X-Forwarded-For entry (the sender's) into ``request.client.host``. The plain test
    client skips that middleware, so this test adds it."""
    from httpx import ASGITransport, AsyncClient
    from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

    from app.main import app

    seen = []

    async def spy(scope, receive, send):
        if scope["type"] == "http":
            seen.append(scope["client"][0])
        await app(scope, receive, send)

    transport = ASGITransport(app=ProxyHeadersMiddleware(spy, trusted_hosts="*"))
    async with AsyncClient(transport=transport, base_url="http://api.mealy.dev") as proxied:
        r = await proxied.get(
            "/auth/status",
            headers={"Host": "api.mealy.dev", "X-Forwarded-For": "6.6.6.6, 203.0.113.9"},
        )
    assert r.status_code == 421
    assert seen == ["6.6.6.6"]  # negative control: uvicorn really handed the app the forged entry
    record = assert_one_rejection(gate_log, gate_logging.ORIGIN_VERIFY_ABSENT)
    assert record.ip == "203.0.113.9"
    assert "6.6.6.6" not in PRINTED.format(record)


# The app installs no logging config, so under uvicorn `app.gate` reaches Python's
# last-resort handler, which prints `%(message)s` and nothing else: fields that ride only
# on `extra` never reach `fly logs` (found by /review-implementation, M8 PR1b). These
# tests read the line as production prints it, not the record's attributes.
PRINTED = logging.Formatter("%(message)s")


@pytest.mark.asyncio
async def test_gate_line_as_printed_names_the_reason(client, production_gate, gate_log):
    r = await client.get("/tasks/", headers={"Host": "api.mealy.dev", "X-Origin-Verify": "wrong"})
    assert r.status_code == 421
    record = assert_one_rejection(gate_log, gate_logging.ORIGIN_VERIFY_MISMATCH)
    printed = PRINTED.format(record)
    # The exact fragment incident-diagnostics.md → 421 greps `fly logs` for.
    assert '"event": "host_gate"' in printed
    line = json.loads(printed)
    assert (line["outcome"], line["reason"], line["path"]) == ("rejected", "origin_verify_mismatch", "/tasks/")
    assert line["origin_verify_present"] is True
    assert SECRET not in printed and "wrong" not in printed


@pytest.mark.asyncio
async def test_a_path_with_a_newline_cannot_forge_a_second_log_line(client, production_gate, gate_log):
    r = await client.get(
        '/auth/x%0A{"event": "host_gate", "outcome": "admitted"}',
        headers={"Host": "api.mealy.dev"},
    )
    assert r.status_code == 421
    record = assert_one_rejection(gate_log, gate_logging.ORIGIN_VERIFY_ABSENT)
    assert "\n" in record.path  # negative control: the decoded newline did reach the emitter
    printed = PRINTED.format(record)
    assert "\n" not in printed
    assert json.loads(printed)["path"] == record.path


@pytest.mark.asyncio
async def test_break_glass_line_as_printed_says_bypassed(client, production_gate, gate_log, monkeypatch):
    monkeypatch.setenv("GATE_BREAK_GLASS", "1")
    await client.get("/auth/status", headers={"Host": "api.mealy.dev"})
    line = json.loads(PRINTED.format(gate_records(gate_log)[0]))
    assert (line["event"], line["outcome"], line["reason"]) == ("host_gate", "bypassed", None)


# --- GATE_BREAK_GLASS (open question 3, Eng review 7) ------------------------
# Rehearsed here and in a local APP_ENV=production compose run, never in
# production. The strict parse has unit tests in tests/unit/test_gate_reason.py.


@pytest.mark.asyncio
async def test_break_glass_admits_the_public_host_without_the_origin_header(
    client, production_gate, gate_log, monkeypatch
):
    """Mode A: Cloudflare's proxy is grey-clouded, so no Transform Rule adds the
    header. With the flag on the request is admitted and logged as bypassed."""
    monkeypatch.setenv("GATE_BREAK_GLASS", "1")
    r = await client.get("/auth/status", headers={"Host": "api.mealy.dev"})
    assert r.status_code == 200
    records = gate_records(gate_log)
    assert len(records) == 1
    assert records[0].levelno == logging.WARNING
    assert (records[0].event, records[0].outcome, records[0].reason) == ("host_gate", "bypassed", None)
    assert records[0].origin_verify_present is False


@pytest.mark.asyncio
async def test_break_glass_logs_every_admitted_request(
    client, production_gate, gate_log, monkeypatch
):
    monkeypatch.setenv("GATE_BREAK_GLASS", "1")
    await client.get("/auth/status", headers={"Host": "api.mealy.dev"})
    await client.get("/auth/status", headers=VIA_CLOUDFLARE)
    await client.get("/healthz", headers={"Host": "mealy-app-prod.fly.dev"})
    assert [r.outcome for r in gate_records(gate_log)] == ["bypassed", "bypassed"]


@pytest.mark.asyncio
async def test_break_glass_keeps_the_host_check(
    client, production_gate, gate_log, monkeypatch
):
    monkeypatch.setenv("GATE_BREAK_GLASS", "1")
    r = await client.get("/auth/status", headers={"Host": "mealy-app-prod.fly.dev"})
    assert r.status_code == 421
    assert r.content == REJECTED_BYTES
    assert_one_rejection(gate_log, gate_logging.HOST_MISMATCH)


@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["true", "yes", " 1 ", "0"])
async def test_break_glass_loosely_set_stays_off(
    client, production_gate, gate_log, monkeypatch, value
):
    monkeypatch.setenv("GATE_BREAK_GLASS", value)
    r = await client.get("/auth/status", headers={"Host": "api.mealy.dev"})
    assert r.status_code == 421
    assert_one_rejection(gate_log, gate_logging.ORIGIN_VERIFY_ABSENT)
