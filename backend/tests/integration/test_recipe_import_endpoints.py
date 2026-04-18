"""Endpoint tests for the recipe-import flow.

Targets:
    POST /items/import-from-url
    GET  /items/import-status/{task_id}

Celery (.apply_async) and Redis are mocked end-to-end. SSRF, broker-down, and
status-resolution branches are covered. The Celery task itself is patched at
``app.tasks.extract_recipe_from_url`` because ``items.py`` locally imports it
inside the route to avoid circular init.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.constants import import_errors as codes


# ---------------------------------------------------------------------------
# Local async client — does NOT need the postgres container fixture because
# none of the endpoints under test depend on the DB session.
# ---------------------------------------------------------------------------


@pytest.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Shared mocks
# ---------------------------------------------------------------------------


def _make_redis_mock():
    """Mock used in place of the module-cached Redis singleton."""
    m = MagicMock()
    m.setex.return_value = True
    m.exists.return_value = 1
    m.delete.return_value = 1
    return m


@pytest.fixture(autouse=True)
def _reset_redis_singleton():
    """The route module caches its Redis client. Reset between tests so each
    test starts with a fresh singleton and its own patch can take effect."""
    import app.routes.items as items_module
    items_module._redis_singleton = None
    yield
    items_module._redis_singleton = None


# ---------------------------------------------------------------------------
# POST /items/import-from-url
# ---------------------------------------------------------------------------


class TestImportFromUrl:
    async def test_valid_public_url_returns_task_id(self, async_client, monkeypatch):
        # Patch SSRF to a no-op so a public-looking URL passes without DNS.
        monkeypatch.setattr(
            "app.routes.items.validate_url_for_fetch", lambda url: None
        )
        apply_async_mock = MagicMock()
        with patch("app.tasks.extract_recipe_from_url.apply_async", apply_async_mock), \
             patch("app.routes.items._redis_client", return_value=_make_redis_mock()):
            resp = await async_client.post(
                "/items/import-from-url",
                json={"url": "https://example.com/recipe"},
            )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        # task_id is now a pre-allocated UUID, so assert shape not equality.
        assert isinstance(body["task_id"], str)
        assert len(body["task_id"]) > 0
        apply_async_mock.assert_called_once()
        kwargs = apply_async_mock.call_args.kwargs
        assert kwargs["args"] == ["https://example.com/recipe"]
        assert kwargs["task_id"] == body["task_id"]

    async def test_ssrf_blocked_returns_400(self, async_client, monkeypatch):
        # Pydantic accepts http://localhost as a valid HttpUrl shape — the SSRF
        # gate is what rejects it. Let the real validator fire.
        # Patch redis just in case (it shouldn't be reached).
        with patch("app.routes.items._redis_client", return_value=_make_redis_mock()):
            resp = await async_client.post(
                "/items/import-from-url",
                json={"url": "http://localhost/recipe"},
            )
        assert resp.status_code == 400
        body = resp.json()
        assert body["detail"]["error_code"] == codes.SSRF_BLOCKED

    async def test_invalid_url_shape_returns_422(self, async_client):
        resp = await async_client.post(
            "/items/import-from-url",
            json={"url": "not-a-url"},
        )
        assert resp.status_code == 422

    async def test_broker_unavailable_returns_503(self, async_client, monkeypatch):
        monkeypatch.setattr(
            "app.routes.items.validate_url_for_fetch", lambda url: None
        )

        def _boom(*a, **kw):
            raise ConnectionError("broker down")

        with patch("app.tasks.extract_recipe_from_url.apply_async", side_effect=_boom), \
             patch("app.routes.items._redis_client", return_value=_make_redis_mock()):
            resp = await async_client.post(
                "/items/import-from-url",
                json={"url": "https://example.com/recipe"},
            )
        assert resp.status_code == 503
        body = resp.json()
        assert body["detail"]["error_code"] == codes.BROKER_UNAVAILABLE

    async def test_redis_down_on_marker_write_returns_503(self, async_client, monkeypatch):
        """Regression for the marker-before-delay reorder: if Redis is down
        BEFORE we queue the task, we must fail loudly (the task wouldn't be
        trackable) rather than silently queue a ghost task."""
        monkeypatch.setattr(
            "app.routes.items.validate_url_for_fetch", lambda url: None
        )
        redis_mock = _make_redis_mock()
        redis_mock.setex.side_effect = ConnectionError("redis down")
        apply_async_mock = MagicMock()
        with patch("app.tasks.extract_recipe_from_url.apply_async", apply_async_mock), \
             patch("app.routes.items._redis_client", return_value=redis_mock):
            resp = await async_client.post(
                "/items/import-from-url",
                json={"url": "https://example.com/recipe"},
            )
        assert resp.status_code == 503
        assert resp.json()["detail"]["error_code"] == codes.BROKER_UNAVAILABLE
        # Task MUST NOT have been queued — marker failed first, so no ghost task.
        apply_async_mock.assert_not_called()


# ---------------------------------------------------------------------------
# GET /items/import-status/{task_id}
# ---------------------------------------------------------------------------


class TestImportStatus:
    async def test_no_marker_returns_not_found(self, async_client):
        redis_mock = _make_redis_mock()
        redis_mock.exists.return_value = 0
        with patch("app.routes.items._redis_client", return_value=redis_mock):
            resp = await async_client.get("/items/import-status/missing-task")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "not_found"
        assert body["error_code"] == codes.UNKNOWN_OR_EXPIRED_TASK

    async def test_marker_with_pending_state(self, async_client):
        redis_mock = _make_redis_mock()
        async_result = MagicMock()
        async_result.state = "PENDING"
        async_result.info = None
        with patch("app.routes.items._redis_client", return_value=redis_mock), \
             patch("app.routes.items.celery_app.AsyncResult", return_value=async_result):
            resp = await async_client.get("/items/import-status/t1")
        body = resp.json()
        assert body["status"] == "pending"
        assert body["step"] == "queued"

    async def test_marker_with_progress_state_returns_step(self, async_client):
        redis_mock = _make_redis_mock()
        async_result = MagicMock()
        async_result.state = "PROGRESS"
        async_result.info = {"step": "extracting_recipe"}
        with patch("app.routes.items._redis_client", return_value=redis_mock), \
             patch("app.routes.items.celery_app.AsyncResult", return_value=async_result):
            resp = await async_client.get("/items/import-status/t2")
        body = resp.json()
        assert body["status"] == "progress"
        assert body["step"] == "extracting_recipe"

    async def test_marker_with_success_complete_returns_recipe(self, async_client):
        redis_mock = _make_redis_mock()
        recipe_payload = {
            "name": "Honey Garlic Chicken",
            "tags": ["chicken"],
            "source_url": "https://example.com/r",
            "recipe_detail": {"description": "yum", "ingredients": []},
        }
        async_result = MagicMock()
        async_result.state = "SUCCESS"
        async_result.result = {"status": "complete", "recipe": recipe_payload}
        with patch("app.routes.items._redis_client", return_value=redis_mock), \
             patch("app.routes.items.celery_app.AsyncResult", return_value=async_result):
            resp = await async_client.get("/items/import-status/t3")
        body = resp.json()
        assert body["status"] == "complete"
        assert body["recipe"]["name"] == "Honey Garlic Chicken"

    async def test_marker_with_success_failed_returns_error_code(self, async_client):
        redis_mock = _make_redis_mock()
        async_result = MagicMock()
        async_result.state = "SUCCESS"
        async_result.result = {"status": "failed", "error_code": codes.NOT_RECIPE}
        with patch("app.routes.items._redis_client", return_value=redis_mock), \
             patch("app.routes.items.celery_app.AsyncResult", return_value=async_result):
            resp = await async_client.get("/items/import-status/t4")
        body = resp.json()
        assert body["status"] == "failed"
        assert body["error_code"] == codes.NOT_RECIPE
