"""Cookie-attribute and read-path drift guard for /plumbing-test.

The Slice 5 browser matrix catches BEHAVIOR drift (SameSite, third-party
cookie blocking) the moment a real browser refuses to round-trip. This
test catches ATTRIBUTE drift (missing Secure, accidental Domain=, wrong
Cache-Control) before the deploy hits the matrix — much cheaper feedback.

PROBE_SAMESITE is imported from the route module, so a Slice-5 flip
"Lax" → "None" is a one-line edit and this test auto-follows.

Deleted in M5 PR #2 alongside the route file."""

from fastapi.testclient import TestClient

from app.main import app
from app.routes.plumbing_test import COOKIE_NAME, PROBE_SAMESITE


def test_post_sets_cookie_with_required_attributes():
    client = TestClient(app)
    response = client.post("/plumbing-test")

    assert response.status_code == 200

    body = response.json()
    assert body["set"] is True
    assert isinstance(body["probe"], str)
    assert len(body["probe"]) > 0

    set_cookie = response.headers.get("set-cookie", "")
    assert f"{COOKIE_NAME}=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie
    assert "Path=/" in set_cookie
    # __Host- prefix forbids the Domain attribute — browsers reject the
    # cookie outright if it appears.
    assert "Domain=" not in set_cookie
    assert f"SameSite={PROBE_SAMESITE}" in set_cookie

    assert response.headers.get("cache-control") == "no-store"


def test_post_returns_a_fresh_probe_each_call():
    client = TestClient(app)
    first = client.post("/plumbing-test").json()["probe"]
    second = client.post("/plumbing-test").json()["probe"]
    assert first != second


def test_read_returns_null_when_no_cookie_present():
    client = TestClient(app)
    response = client.get("/plumbing-test/read")
    assert response.status_code == 200
    assert response.json() == {"value": None}
    assert response.headers.get("cache-control") == "no-store"


def test_read_echoes_cookie_value_when_present():
    client = TestClient(app)
    client.cookies.set(COOKIE_NAME, "test-probe-value-abc123")
    response = client.get("/plumbing-test/read")
    assert response.status_code == 200
    assert response.json() == {"value": "test-probe-value-abc123"}
