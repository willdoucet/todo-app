"""Shared Anthropic / Claude client for all AI features.

Centralizes:
- Client init (reads ANTHROPIC_API_KEY and AI_MODEL_NAME)
- Structured extraction with Pydantic schema validation
- One automatic retry on ValidationError, passing the errors back to the model
- Structured logs per call (input_tokens, output_tokens, model, duration_ms,
  cost_estimate). Never logs prompt bodies or response bodies.

All consumers (recipe_extractor, suggest-icon endpoint, future AI features)
import from here. Keep this module thin — feature-specific prompt assembly
lives in the feature module.

Sync-only by design: Celery tasks in this project run synchronously via the
``run_async`` bridge, and the suggest-icon endpoint is called inline. The
Anthropic SDK's sync client is the right shape for both.
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Type, TypeVar

from anthropic import (
    Anthropic,
    APIConnectionError,
    APIError,
    APIStatusError,
    AuthenticationError,
    RateLimitError,
)
from pydantic import BaseModel, ValidationError


log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


# Pricing in USD per 1M tokens (Claude Haiku 4.5 as of 2026-04; update when rates change).
# This is a coarse estimate for observability — actual invoice is authoritative.
_MODEL_PRICING = {
    "claude-haiku-4-5-20251001": {"input_per_mtok": 1.00, "output_per_mtok": 5.00},
    "claude-sonnet-4-6": {"input_per_mtok": 3.00, "output_per_mtok": 15.00},
}


class AIError(Exception):
    """Base for AI-client errors that callers may want to map to user-facing codes."""


class AIAuthError(AIError):
    """Bad or missing API key. Maps to ``llm_auth``."""


class AIConnectionError(AIError):
    """Network failure reaching Anthropic. Maps to ``llm_unavailable``."""


class AIRateLimited(AIError):
    """Anthropic 429. Maps to ``llm_rate_limited``."""


class AIRefused(AIError):
    """Model refused to answer. Maps to ``llm_refused``."""


class AIOutputInvalid(AIError):
    """LLM output failed Pydantic validation twice. Maps to ``not_recipe``
    for the recipe pipeline; other callers interpret how they wish."""


def _client() -> Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise AIAuthError("ANTHROPIC_API_KEY is not set")
    # Anthropic SDK picks up the key from the env var, but pass it explicitly
    # so the failure mode is obvious in tests that use monkeypatch.setenv.
    return Anthropic(api_key=api_key)


def _model_name() -> str:
    return os.getenv("AI_MODEL_NAME", "claude-haiku-4-5-20251001")


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    pricing = _MODEL_PRICING.get(model)
    if not pricing:
        return 0.0
    return (
        (input_tokens / 1_000_000.0) * pricing["input_per_mtok"]
        + (output_tokens / 1_000_000.0) * pricing["output_per_mtok"]
    )


def _extract_json_from_response(response) -> dict:
    """Pull the first JSON object out of a Claude messages response.

    Anthropic's messages API returns a list of content blocks. We ask the
    model to return a JSON object as a single text block, so the first
    ``text`` block is what we want. The model sometimes wraps the JSON in a
    ```json fenced code block — strip that if present.
    """
    for block in response.content:
        if getattr(block, "type", None) != "text":
            continue
        text = block.text.strip()
        if text.startswith("```"):
            # Strip ```json or ``` fence
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        return json.loads(text)
    raise AIOutputInvalid("no text block in LLM response")


def extract_structured(
    *,
    system_prompt: str,
    user_prompt: str,
    schema: Type[T],
    max_tokens: int = 2048,
) -> T:
    """Call Claude with a system + user prompt and validate the response
    against a Pydantic schema. One automatic retry on ValidationError.

    The model is instructed to return ONLY a JSON object matching the schema;
    retry messages include the validation errors so the model can self-correct.

    Never logs prompt bodies or response bodies — only metrics.
    """
    client = _client()
    model = _model_name()

    def _call(messages: list[dict]) -> tuple[T, dict]:
        t0 = time.monotonic()
        try:
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=messages,
            )
        except AuthenticationError as exc:
            raise AIAuthError(str(exc)) from exc
        except APIConnectionError as exc:
            raise AIConnectionError(str(exc)) from exc
        except RateLimitError as exc:
            raise AIRateLimited(str(exc)) from exc
        except APIStatusError as exc:
            # 5xx / other status errors from Anthropic
            raise AIConnectionError(f"status_{exc.status_code}") from exc
        except APIError as exc:
            # Catch-all for Anthropic SDK errors (PermissionDeniedError,
            # BadRequestError, etc.) that aren't subclasses of the above.
            raise AIConnectionError(f"anthropic_api_error:{type(exc).__name__}") from exc

        duration_ms = int((time.monotonic() - t0) * 1000)

        # Anthropic can return stop_reason="refusal" for policy violations.
        if getattr(response, "stop_reason", None) == "refusal":
            raise AIRefused("model stop_reason=refusal")

        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "input_tokens", 0) if usage else 0
        output_tokens = getattr(usage, "output_tokens", 0) if usage else 0
        cost_estimate = _estimate_cost(model, input_tokens, output_tokens)

        metrics = {
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "duration_ms": duration_ms,
            "cost_estimate": round(cost_estimate, 6),
        }
        log.info("ai_client.call", extra=metrics)

        try:
            raw = _extract_json_from_response(response)
        except (json.JSONDecodeError, AIOutputInvalid) as exc:
            raise AIOutputInvalid(f"malformed_json: {exc!s}") from exc

        try:
            validated = schema.model_validate(raw)
        except ValidationError as exc:
            raise AIOutputInvalid(exc.errors()) from exc

        return validated, metrics

    # First attempt
    messages = [{"role": "user", "content": user_prompt}]
    first_err_str: str | None = None
    try:
        result, _ = _call(messages)
        return result
    except AIOutputInvalid as first_err:
        first_err_str = str(first_err)
        log.warning("ai_client.validation_retry", extra={"first_error": first_err_str[:500]})

    # Retry once, feeding the validation errors back to the model.
    retry_user_prompt = (
        user_prompt
        + "\n\nYour previous response failed validation with these errors:\n"
        + (first_err_str or "")[:1500]
        + "\n\nReturn a corrected JSON object matching the requested schema."
    )
    messages = [{"role": "user", "content": retry_user_prompt}]
    result, _ = _call(messages)
    return result


def call_text(
    *,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 256,
) -> str:
    """Simple text-in / text-out helper for things like emoji suggestion.

    Same error mapping as ``extract_structured`` but no schema validation and
    no retry loop. Returns the first text block of the response (trimmed).
    """
    client = _client()
    model = _model_name()
    t0 = time.monotonic()
    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except AuthenticationError as exc:
        raise AIAuthError(str(exc)) from exc
    except APIConnectionError as exc:
        raise AIConnectionError(str(exc)) from exc
    except RateLimitError as exc:
        raise AIRateLimited(str(exc)) from exc
    except APIStatusError as exc:
        raise AIConnectionError(f"status_{exc.status_code}") from exc
    except APIError as exc:
        raise AIConnectionError(f"anthropic_api_error:{type(exc).__name__}") from exc

    duration_ms = int((time.monotonic() - t0) * 1000)

    if getattr(response, "stop_reason", None) == "refusal":
        raise AIRefused("model stop_reason=refusal")

    usage = getattr(response, "usage", None)
    input_tokens = getattr(usage, "input_tokens", 0) if usage else 0
    output_tokens = getattr(usage, "output_tokens", 0) if usage else 0
    log.info(
        "ai_client.call_text",
        extra={
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "duration_ms": duration_ms,
            "cost_estimate": round(_estimate_cost(model, input_tokens, output_tokens), 6),
        },
    )

    for block in response.content:
        if getattr(block, "type", None) == "text":
            return block.text.strip()
    raise AIOutputInvalid("no text block in LLM response")
