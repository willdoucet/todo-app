"""Unit tests for IP resolution + sanitization (Eng review 2)."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.auth.logging_utils import IP_MAX_LENGTH, resolve_client_ip


def _make_request(headers: dict[str, str], client_host: str | None = None):
    """Build a minimal Request-like mock with just headers + .client.host."""
    req = MagicMock()
    req.headers = headers
    if client_host is not None:
        req.client = MagicMock()
        req.client.host = client_host
    else:
        req.client = None
    return req


# =============================================================================
# Rule 1 — CF-Connecting-IP precedence
# =============================================================================

def test_cf_connecting_ip_wins_over_xff():
    req = _make_request({
        "CF-Connecting-IP": "203.0.113.7",
        "X-Forwarded-For": "198.51.100.1, 10.0.0.2",
    })
    assert resolve_client_ip(req) == "203.0.113.7"


def test_cf_connecting_ip_wins_over_xff_and_socket():
    req = _make_request(
        {"CF-Connecting-IP": "203.0.113.7", "X-Forwarded-For": "198.51.100.1"},
        client_host="127.0.0.1",
    )
    assert resolve_client_ip(req) == "203.0.113.7"


# =============================================================================
# Rule 2 — XFF first-comma-entry parsing
# =============================================================================

def test_xff_first_entry_is_used():
    req = _make_request({"X-Forwarded-For": "203.0.113.7, 198.51.100.1, 10.0.0.1"})
    assert resolve_client_ip(req) == "203.0.113.7"


def test_xff_first_entry_strips_whitespace():
    req = _make_request({"X-Forwarded-For": "  203.0.113.7  ,198.51.100.1"})
    assert resolve_client_ip(req) == "203.0.113.7"


def test_xff_single_entry_used_directly():
    req = _make_request({"X-Forwarded-For": "203.0.113.7"})
    assert resolve_client_ip(req) == "203.0.113.7"


# =============================================================================
# Rule 3 — 128-char truncation against bloated headers
# =============================================================================

def test_xff_blob_truncated_to_max_length():
    """Attacker-bloated XFF (no commas, 64KB) → resolved IP ≤ 128 chars."""
    huge = "X" * 64_000
    req = _make_request({"X-Forwarded-For": huge})
    resolved = resolve_client_ip(req)
    assert len(resolved) <= IP_MAX_LENGTH
    assert resolved == "X" * IP_MAX_LENGTH


def test_cf_connecting_ip_truncated_to_max_length():
    huge = "Y" * 1_000
    req = _make_request({"CF-Connecting-IP": huge})
    resolved = resolve_client_ip(req)
    assert len(resolved) <= IP_MAX_LENGTH


# =============================================================================
# Fallbacks
# =============================================================================

def test_socket_peer_fallback_when_no_proxy_headers():
    req = _make_request({}, client_host="192.0.2.5")
    assert resolve_client_ip(req) == "192.0.2.5"


def test_unknown_when_no_headers_no_client():
    req = _make_request({}, client_host=None)
    assert resolve_client_ip(req) == "unknown"
