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

Both failures return the same 421 body, so a caller cannot tell which check
it failed. The gate is a no-op outside production so dev/test can use any
Host header.
"""

from __future__ import annotations

import pytest

# Test-only value. The production secret exists only as a Fly secret and in the
# Cloudflare Transform Rule.
SECRET = "test-origin-verify-secret-0123456789"
VIA_CLOUDFLARE = {"Host": "api.mealy.dev", "X-Origin-Verify": SECRET}
REJECTED = {"detail": "host_not_allowed"}


@pytest.fixture
def production_gate(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("PUBLIC_API_HOST", "api.mealy.dev")
    monkeypatch.setenv("ORIGIN_VERIFY_SECRET", SECRET)


@pytest.mark.asyncio
async def test_gate_disabled_when_app_env_not_production(client, monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    r = await client.get(
        "/auth/status",
        headers={"Host": "mealy-app-prod.fly.dev"},
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_gate_allows_request_through_cloudflare(client, production_gate):
    r = await client.get("/auth/status", headers=VIA_CLOUDFLARE)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_gate_with_port_in_host_header_still_matches(client, production_gate):
    """Browsers may send Host: api.mealy.dev:443 — our middleware strips
    the port before comparing."""
    r = await client.get(
        "/auth/status", headers={**VIA_CLOUDFLARE, "Host": "api.mealy.dev:443"}
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_gate_allows_healthz_unconditionally(client, production_gate):
    """Fly health checks carry neither the public Host nor the origin header."""
    r = await client.get("/healthz", headers={"Host": "mealy-app-prod.fly.dev"})
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_gate_blocks_direct_fly_origin_for_auth_routes(client, production_gate):
    """Wrong Host with a valid origin header: the Host check alone rejects."""
    r = await client.get(
        "/auth/status",
        headers={**VIA_CLOUDFLARE, "Host": "mealy-app-prod.fly.dev"},
    )
    assert r.status_code == 421
    assert r.json() == REJECTED


@pytest.mark.asyncio
async def test_gate_blocks_existing_business_routes_too(client, production_gate):
    """Not just /auth/* — every backend path except /healthz."""
    r = await client.get(
        "/family-members/",
        headers={**VIA_CLOUDFLARE, "Host": "mealy-app-prod.fly.dev"},
    )
    assert r.status_code == 421


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
    client, production_gate, method, path
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


@pytest.mark.asyncio
async def test_gate_blocks_wrong_origin_header(client, production_gate):
    r = await client.get(
        "/auth/status", headers={**VIA_CLOUDFLARE, "X-Origin-Verify": SECRET[:-1]}
    )
    assert r.status_code == 421
    assert r.json() == REJECTED


@pytest.mark.asyncio
async def test_gate_rejects_non_ascii_origin_header_without_crashing(
    client, production_gate
):
    """hmac.compare_digest raises TypeError for non-ASCII str arguments. A
    forged header must be a 421, never an unhandled 500."""
    r = await client.get(
        "/auth/status",
        headers={"Host": "api.mealy.dev", "X-Origin-Verify": "sécret".encode("latin-1")},
    )
    assert r.status_code == 421


@pytest.mark.asyncio
async def test_gate_fails_closed_when_origin_secret_missing(
    client, production_gate, monkeypatch
):
    """An empty secret must never match an empty header — comparing "" with
    "" would open the gate to everyone. Production also refuses to boot
    without the secret; this is the request-time backstop."""
    monkeypatch.setenv("ORIGIN_VERIFY_SECRET", "")
    for headers in (
        {"Host": "api.mealy.dev"},
        {"Host": "api.mealy.dev", "X-Origin-Verify": ""},
    ):
        r = await client.get("/auth/status", headers=headers)
        assert r.status_code == 421

    monkeypatch.delenv("ORIGIN_VERIFY_SECRET")
    r = await client.get("/auth/status", headers={"Host": "api.mealy.dev"})
    assert r.status_code == 421


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "spoof_host",
    ["api.mealy.dev/healthz?", "api.mealy.dev/healthz#", "evil/healthz"],
)
async def test_gate_healthz_exemption_cannot_be_spoofed_via_host(
    client, production_gate, spoof_host
):
    """A Host header that makes `request.url.path` parse as "/healthz" must not
    exempt a request the router still dispatches to a real route. The gate
    matches on scope["path"], so /auth/status stays gated (421) here."""
    r = await client.get("/auth/status", headers={"Host": spoof_host})
    assert r.status_code == 421
    assert r.json() == REJECTED


@pytest.mark.asyncio
async def test_gate_blocks_when_public_api_host_not_set(
    client, production_gate, monkeypatch
):
    """Production mode but PUBLIC_API_HOST unset → reject everything (fail closed)."""
    monkeypatch.delenv("PUBLIC_API_HOST", raising=False)
    r = await client.get("/auth/status", headers=VIA_CLOUDFLARE)
    assert r.status_code == 421
