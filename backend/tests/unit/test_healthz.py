"""Pin /healthz to exact body shape {"status": "ok"}.

The endpoint is shallow-by-design — adding hostname, version, env, or
db-status would change the contract. Future drift fails this test instead
of silently shipping more health metadata than intended."""

from fastapi.testclient import TestClient

from app.main import app


def test_healthz_returns_exact_status_ok():
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
