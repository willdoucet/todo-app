"""Integration tests for ``GET /auth/status``."""

from __future__ import annotations

import logging

import pytest


@pytest.mark.asyncio
async def test_status_false_on_empty_db(client, caplog):
    caplog.set_level(logging.INFO, logger="app.auth")
    r = await client.get("/auth/status")
    assert r.status_code == 200
    assert r.json() == {"account_exists": False}

    records = [r for r in caplog.records if r.name == "app.auth"]
    assert len(records) == 1
    assert records[0].event == "auth.status"
    assert records[0].outcome == "success"


@pytest.mark.asyncio
async def test_status_true_after_register(client, register_user, caplog):
    await register_user()
    caplog.set_level(logging.INFO, logger="app.auth")
    caplog.clear()

    r = await client.get("/auth/status")
    assert r.status_code == 200
    assert r.json() == {"account_exists": True}

    records = [r for r in caplog.records if r.name == "app.auth"]
    assert len(records) == 1
    assert records[0].event == "auth.status"
    assert records[0].outcome == "success"


@pytest.mark.asyncio
async def test_status_response_is_minimal(client):
    """No version / hostname / config leakage — JSON has exactly the one key."""
    r = await client.get("/auth/status")
    body = r.json()
    assert set(body.keys()) == {"account_exists"}
