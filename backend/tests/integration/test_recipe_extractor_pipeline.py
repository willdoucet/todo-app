"""End-to-end tests for ``app.services.recipe_extractor.extract_recipe``.

We mock both the HTTP layer (``httpx.Client``) and the LLM layer
(``ai_client.extract_structured``) so the pipeline runs without touching the
network. Each test exercises a single failure-mode branch — happy path,
SSRF, fetch error, redirect-to-private, non-HTML, and the semantic guard —
plus the progress callback ordering.
"""
from __future__ import annotations

import socket
from typing import Iterator
from unittest.mock import MagicMock

import httpx
import pytest

from app.services import recipe_extractor as re


@pytest.fixture(autouse=True)
def _stub_dns(monkeypatch):
    """Resolve any non-localhost hostname to a public IP so the SSRF gate
    passes without real DNS. Tests that need the gate to REJECT a hostname
    use a literal blocked name (``localhost``) which short-circuits before DNS.
    """

    def _fake(host, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", _fake)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_response(
    *,
    status: int = 200,
    body: bytes = b"<html><body>x</body></html>",
    headers: dict | None = None,
    is_redirect: bool = False,
    url: str = "https://example.com/recipe",
    encoding: str = "utf-8",
):
    """Build a duck-typed httpx.Response with the fields recipe_extractor reads."""
    h = {"content-type": "text/html; charset=utf-8"}
    if headers:
        h.update(headers)
    resp = MagicMock()
    resp.status_code = status
    resp.is_redirect = is_redirect
    resp.headers = h
    resp.content = body
    resp.url = url
    resp.encoding = encoding
    return resp


def _patch_httpx_client(monkeypatch, responses: list):
    """Patch ``httpx.Client`` so ``client.get(...)`` returns the given queued
    responses in order."""
    response_iter: Iterator = iter(responses)

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, url, *args, **kwargs):
            try:
                nxt = next(response_iter)
            except StopIteration:
                raise AssertionError(f"Unexpected extra GET to {url}")
            if isinstance(nxt, Exception):
                raise nxt
            return nxt

    monkeypatch.setattr(httpx, "Client", _FakeClient)


def _good_llm_recipe() -> re._LlmRecipe:
    return re._LlmRecipe(
        name="Honey Garlic Chicken",
        description="A weeknight win.",
        ingredients=[
            re._LlmIngredient(name="chicken breast", quantity=2, unit="lb", category="Protein"),
            re._LlmIngredient(name="honey", quantity=0.25, unit="cup", category="Pantry"),
        ],
        instructions=(
            "1. Season chicken. 2. Cook in skillet. 3. Add honey-garlic sauce. "
            "4. Reduce and serve over rice."
        ),
        prep_time_minutes=10,
        cook_time_minutes=20,
        servings=4,
        tags=["chicken", "weeknight", "quick"],
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestHappyPath:
    def test_full_pipeline_returns_recipe_extraction(self, monkeypatch):
        body = (
            b"<html><body><article>"
            b"<h1>Honey Garlic Chicken</h1>"
            b"<p>Season chicken, cook in pan, add sauce.</p>"
            b"</article></body></html>"
        )
        _patch_httpx_client(monkeypatch, [_fake_response(body=body)])
        monkeypatch.setattr(
            "app.services.recipe_extractor.ai_client.extract_structured",
            lambda *a, **kw: _good_llm_recipe(),
        )
        result = re.extract_recipe("https://example.com/recipe")
        assert result.name == "Honey Garlic Chicken"
        assert "chicken" in result.tags
        assert len(result.recipe_detail.ingredients) == 2
        assert result.source_url.startswith("https://example.com/")


# ---------------------------------------------------------------------------
# Fetch-stage failures
# ---------------------------------------------------------------------------


class TestFetchFailures:
    def test_ssrf_pre_gate_blocks_localhost(self, monkeypatch):
        with pytest.raises(re.SsrfError):
            re.extract_recipe("http://localhost/recipe")

    def test_timeout_raises_fetch_timeout(self, monkeypatch):
        _patch_httpx_client(
            monkeypatch, [httpx.TimeoutException("connect timeout")]
        )
        with pytest.raises(re.FetchTimeout):
            re.extract_recipe("https://example.com/recipe")

    def test_404_raises_fetch_not_found(self, monkeypatch):
        _patch_httpx_client(monkeypatch, [_fake_response(status=404)])
        with pytest.raises(re.FetchNotFound):
            re.extract_recipe("https://example.com/recipe")

    def test_403_raises_fetch_blocked(self, monkeypatch):
        _patch_httpx_client(monkeypatch, [_fake_response(status=403)])
        with pytest.raises(re.FetchBlocked):
            re.extract_recipe("https://example.com/recipe")

    def test_redirect_to_private_ip_raises_ssrf(self, monkeypatch):
        # First hop: 302 to http://127.0.0.1/evil
        redirect = _fake_response(
            status=302,
            is_redirect=True,
            headers={"location": "http://127.0.0.1/evil"},
        )
        _patch_httpx_client(monkeypatch, [redirect])
        with pytest.raises(re.SsrfError):
            re.extract_recipe("https://example.com/recipe")

    def test_non_html_content_type_raises_not_html(self, monkeypatch):
        _patch_httpx_client(
            monkeypatch,
            [_fake_response(headers={"content-type": "application/pdf"})],
        )
        with pytest.raises(re.NotHtml):
            re.extract_recipe("https://example.com/recipe.pdf")


# ---------------------------------------------------------------------------
# Semantic guard
# ---------------------------------------------------------------------------


class TestSemanticGuard:
    def test_one_ingredient_raises_not_recipe(self, monkeypatch):
        body = b"<html><body><article>some content</article></body></html>"
        _patch_httpx_client(monkeypatch, [_fake_response(body=body)])
        bad_llm = re._LlmRecipe(
            name="Sad Recipe",
            ingredients=[
                re._LlmIngredient(name="salt", quantity=1, unit="tsp", category="Pantry")
            ],
            instructions="cook it for a long time and then serve.",
        )
        monkeypatch.setattr(
            "app.services.recipe_extractor.ai_client.extract_structured",
            lambda *a, **kw: bad_llm,
        )
        with pytest.raises(re.NotRecipe):
            re.extract_recipe("https://example.com/recipe")


# ---------------------------------------------------------------------------
# Progress callback ordering
# ---------------------------------------------------------------------------


class TestProgressCallback:
    def test_progress_steps_called_in_order(self, monkeypatch):
        body = (
            b"<html><body><article>"
            b"<h1>Honey Garlic Chicken</h1>"
            b"<p>Season chicken, cook in pan, add sauce, reduce, serve.</p>"
            b"</article></body></html>"
        )
        _patch_httpx_client(monkeypatch, [_fake_response(body=body)])
        monkeypatch.setattr(
            "app.services.recipe_extractor.ai_client.extract_structured",
            lambda *a, **kw: _good_llm_recipe(),
        )

        steps: list[str] = []
        re.extract_recipe(
            "https://example.com/recipe",
            on_progress=steps.append,
        )
        assert steps == [
            "fetching_page",
            "cleaning_html",
            "extracting_recipe",
            "parsing_ingredients",
        ]
