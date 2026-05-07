"""Behavioral 401 gate for the M5 wrapping `protected` APIRouter pattern.

The unit-level enumeration test (`tests/unit/test_protected_router_propagation.py`)
verifies STRUCTURAL presence of `get_current_user` on every protected
route's dependency tree. This file verifies BEHAVIORAL invocation —
that the dep actually fires at request time and returns 401 when the
Authorization header is missing or malformed. The two together pin the
gate from both ends.

Failure modes this catches that the structural test does NOT:
- a future test override of `get_current_user` accidentally left
  permanent in `app.dependency_overrides`
- an unforeseen middleware short-circuit that bypasses the dep
- a regression in FastAPI's dep machinery itself
"""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_protected_route_without_auth_returns_401(unauth_client):
    response = await unauth_client.get("/tasks/")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_with_malformed_bearer_returns_401(unauth_client):
    response = await unauth_client.get("/tasks/", headers={"Authorization": "Basic abc123"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_public_route_without_auth_returns_200(unauth_client):
    """Positive control: the public sanity route must NOT be inadvertently
    pulled into the protected wrapper."""
    response = await unauth_client.get("/")
    assert response.status_code == 200
