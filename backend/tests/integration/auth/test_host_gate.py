"""Integration tests for the production host gate (Adversarial review run 2).

The middleware in ``app.main`` rejects direct Fly-hostname requests to
any non-/healthz path when ``APP_ENV=production``. Custom-domain
requests through Cloudflare reach the handler. The gate is a no-op
outside production so dev/test can use any host header.
"""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_gate_disabled_when_app_env_not_production(client, monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    r = await client.get(
        "/auth/status",
        headers={"Host": "mealy-app-prod.fly.dev"},
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_gate_blocks_direct_fly_origin_for_auth_routes(client, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("PUBLIC_API_HOST", "api.mealy.dev")
    r = await client.get(
        "/auth/status", headers={"Host": "mealy-app-prod.fly.dev"}
    )
    assert r.status_code == 421


@pytest.mark.asyncio
async def test_gate_allows_custom_domain_in_production(client, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("PUBLIC_API_HOST", "api.mealy.dev")
    r = await client.get(
        "/auth/status", headers={"Host": "api.mealy.dev"}
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_gate_allows_healthz_unconditionally(client, monkeypatch):
    """Fly health checks must keep working — /healthz is exempt."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("PUBLIC_API_HOST", "api.mealy.dev")
    r = await client.get(
        "/healthz", headers={"Host": "mealy-app-prod.fly.dev"}
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_gate_blocks_existing_business_routes_too(client, monkeypatch):
    """Not just /auth/* — every backend path except /healthz."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("PUBLIC_API_HOST", "api.mealy.dev")
    r = await client.get(
        "/family-members/", headers={"Host": "mealy-app-prod.fly.dev"}
    )
    assert r.status_code == 421


@pytest.mark.asyncio
async def test_gate_with_port_in_host_header_still_matches(client, monkeypatch):
    """Browsers may send Host: api.mealy.dev:443 — our middleware strips
    the port before comparing."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("PUBLIC_API_HOST", "api.mealy.dev")
    r = await client.get(
        "/auth/status", headers={"Host": "api.mealy.dev:443"}
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_gate_blocks_when_public_api_host_not_set(client, monkeypatch):
    """Production mode but PUBLIC_API_HOST unset → reject everything (fail closed)."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("PUBLIC_API_HOST", raising=False)
    r = await client.get("/auth/status", headers={"Host": "anything"})
    assert r.status_code == 421
