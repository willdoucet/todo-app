"""Unit tests for ``app.services.ai_client``.

The Anthropic SDK is fully mocked — no network calls are made. We patch the
``Anthropic`` class itself so ``client.messages.create`` returns canned
responses. SDK exception classes are also patched in the ai_client module so
the mock can raise them without needing the SDK's real constructor signatures.
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, Field

from app.services import ai_client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _DemoSchema(BaseModel):
    name: str = Field(..., min_length=1)
    count: int = Field(..., ge=0)


def _fake_anthropic_response(text: str, *, stop_reason: str = "end_turn"):
    """Build an object shaped like the Anthropic SDK message response.

    We only need ``content`` (a list of blocks with ``type`` and ``text``),
    ``stop_reason``, and ``usage`` (with ``input_tokens`` / ``output_tokens``).
    """
    block = SimpleNamespace(type="text", text=text)
    usage = SimpleNamespace(input_tokens=10, output_tokens=20)
    return SimpleNamespace(content=[block], stop_reason=stop_reason, usage=usage)


def _patch_client_with_responses(monkeypatch, responses: list):
    """Replace ai_client._client() with a MagicMock whose
    messages.create returns/raises the supplied side_effect list."""
    fake_client = MagicMock()
    fake_client.messages.create.side_effect = responses
    monkeypatch.setattr(ai_client, "_client", lambda: fake_client)
    return fake_client


# ---------------------------------------------------------------------------
# Happy path + retry
# ---------------------------------------------------------------------------


class TestExtractStructuredHappyPath:
    def test_well_formed_json_response_returns_validated_schema(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        payload = json.dumps({"name": "alpha", "count": 3})
        _patch_client_with_responses(monkeypatch, [_fake_anthropic_response(payload)])

        result = ai_client.extract_structured(
            system_prompt="sys",
            user_prompt="usr",
            schema=_DemoSchema,
        )
        assert isinstance(result, _DemoSchema)
        assert result.name == "alpha"
        assert result.count == 3

    def test_strips_json_code_fence(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        fenced = "```json\n" + json.dumps({"name": "fenced", "count": 1}) + "\n```"
        _patch_client_with_responses(monkeypatch, [_fake_anthropic_response(fenced)])

        result = ai_client.extract_structured(
            system_prompt="sys",
            user_prompt="usr",
            schema=_DemoSchema,
        )
        assert result.name == "fenced"
        assert result.count == 1

    def test_validation_error_triggers_retry_then_succeeds(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        bad = json.dumps({"name": "", "count": -5})  # both fields invalid
        good = json.dumps({"name": "ok", "count": 7})
        fake = _patch_client_with_responses(
            monkeypatch,
            [_fake_anthropic_response(bad), _fake_anthropic_response(good)],
        )
        result = ai_client.extract_structured(
            system_prompt="sys",
            user_prompt="usr",
            schema=_DemoSchema,
        )
        assert result.name == "ok"
        assert result.count == 7
        assert fake.messages.create.call_count == 2

    def test_two_consecutive_validation_failures_raise_ai_output_invalid(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        bad1 = json.dumps({"name": "", "count": -1})
        bad2 = json.dumps({"name": "", "count": -2})
        _patch_client_with_responses(
            monkeypatch,
            [_fake_anthropic_response(bad1), _fake_anthropic_response(bad2)],
        )
        with pytest.raises(ai_client.AIOutputInvalid):
            ai_client.extract_structured(
                system_prompt="sys",
                user_prompt="usr",
                schema=_DemoSchema,
            )


# ---------------------------------------------------------------------------
# SDK error mapping
# ---------------------------------------------------------------------------


class _FakeAuthErr(Exception):
    pass


class _FakeConnErr(Exception):
    pass


class _FakeRateErr(Exception):
    pass


class TestSdkErrorMapping:
    def test_authentication_error_becomes_ai_auth_error(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        # Patch the SDK exception classes used in ai_client's `except` clauses.
        monkeypatch.setattr(ai_client, "AuthenticationError", _FakeAuthErr)
        fake_client = MagicMock()
        fake_client.messages.create.side_effect = _FakeAuthErr("bad key")
        monkeypatch.setattr(ai_client, "_client", lambda: fake_client)

        with pytest.raises(ai_client.AIAuthError):
            ai_client.extract_structured(
                system_prompt="sys",
                user_prompt="usr",
                schema=_DemoSchema,
            )

    def test_api_connection_error_becomes_ai_connection_error(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.setattr(ai_client, "APIConnectionError", _FakeConnErr)
        fake_client = MagicMock()
        fake_client.messages.create.side_effect = _FakeConnErr("dns down")
        monkeypatch.setattr(ai_client, "_client", lambda: fake_client)

        with pytest.raises(ai_client.AIConnectionError):
            ai_client.extract_structured(
                system_prompt="sys",
                user_prompt="usr",
                schema=_DemoSchema,
            )

    def test_rate_limit_error_becomes_ai_rate_limited(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.setattr(ai_client, "RateLimitError", _FakeRateErr)
        fake_client = MagicMock()
        fake_client.messages.create.side_effect = _FakeRateErr("429")
        monkeypatch.setattr(ai_client, "_client", lambda: fake_client)

        with pytest.raises(ai_client.AIRateLimited):
            ai_client.extract_structured(
                system_prompt="sys",
                user_prompt="usr",
                schema=_DemoSchema,
            )

    def test_refusal_stop_reason_becomes_ai_refused(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        _patch_client_with_responses(
            monkeypatch,
            [_fake_anthropic_response('{"name":"x","count":1}', stop_reason="refusal")],
        )
        with pytest.raises(ai_client.AIRefused):
            ai_client.extract_structured(
                system_prompt="sys",
                user_prompt="usr",
                schema=_DemoSchema,
            )


# ---------------------------------------------------------------------------
# call_text
# ---------------------------------------------------------------------------


class TestCallText:
    def test_returns_first_text_block_stripped(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        _patch_client_with_responses(monkeypatch, [_fake_anthropic_response("  🍌  ")])
        out = ai_client.call_text(system_prompt="sys", user_prompt="usr")
        assert out == "🍌"


# ---------------------------------------------------------------------------
# Missing API key
# ---------------------------------------------------------------------------


class TestMissingApiKey:
    def test_missing_key_raises_ai_auth_error_at_init(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(ai_client.AIAuthError):
            ai_client.extract_structured(
                system_prompt="sys",
                user_prompt="usr",
                schema=_DemoSchema,
            )
