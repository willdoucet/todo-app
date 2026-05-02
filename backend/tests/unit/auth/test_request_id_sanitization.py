"""Unit tests for X-Request-Id sanitization (Adversarial review run 2).

Oversized, control-character, or unsafe-character request IDs are
replaced with a generated UUID4 so attacker-controlled values never
land in structured log records.
"""

from __future__ import annotations

import re
from unittest.mock import MagicMock

from app.auth.logging_utils import resolve_request_id


def _request_with_id(value: str | None):
    req = MagicMock()
    req.headers = {"X-Request-Id": value} if value is not None else {}
    return req


_UUID_HEX = re.compile(r"^[0-9a-f]{32}\Z")


# =============================================================================
# Valid bounded request IDs are passed through
# =============================================================================

def test_valid_alnum_request_id_passed_through():
    req = _request_with_id("abc123ABCxyz")
    assert resolve_request_id(req) == "abc123ABCxyz"


def test_valid_request_id_with_safe_punctuation_passed_through():
    req = _request_with_id("trace-123_456.789:server-1")
    assert resolve_request_id(req) == "trace-123_456.789:server-1"


def test_request_id_at_max_length_passed_through():
    rid = "a" * 128
    req = _request_with_id(rid)
    assert resolve_request_id(req) == rid


# =============================================================================
# Unsafe values fall back to generated UUID
# =============================================================================

def test_missing_header_uses_generated_uuid():
    req = _request_with_id(None)
    val = resolve_request_id(req)
    assert _UUID_HEX.match(val), f"Expected hex UUID, got {val!r}"


def test_empty_string_uses_generated_uuid():
    req = _request_with_id("")
    assert _UUID_HEX.match(resolve_request_id(req))


def test_oversized_request_id_uses_generated_uuid():
    """129+ chars → fallback. Attacker can't shovel a giant value into the log."""
    rid = "a" * 129
    req = _request_with_id(rid)
    val = resolve_request_id(req)
    assert val != rid
    assert _UUID_HEX.match(val)


def test_control_character_request_id_uses_generated_uuid():
    """CR/LF/null injections must NOT propagate to logs (log-injection defense)."""
    for bad in ("trace\nbroken", "trace\rbroken", "trace\x00broken", "trace\tbroken"):
        req = _request_with_id(bad)
        val = resolve_request_id(req)
        assert val != bad
        assert _UUID_HEX.match(val)


def test_unsafe_punctuation_uses_generated_uuid():
    """Anything outside [A-Za-z0-9._:-] → fallback."""
    for bad in ("trace/path", "trace?query", "trace<tag>", "trace space"):
        req = _request_with_id(bad)
        val = resolve_request_id(req)
        assert val != bad
        assert _UUID_HEX.match(val)


def test_two_missing_request_ids_yield_distinct_uuids():
    a = resolve_request_id(_request_with_id(None))
    b = resolve_request_id(_request_with_id(None))
    assert a != b  # UUIDs are virtually never equal
