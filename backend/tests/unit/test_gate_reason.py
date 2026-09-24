"""Unit tests for ``app.main.gate_reason`` — one per branch of the gate's decision tree.

The HTTP tests (``tests/integration/auth/test_host_gate.py``) assert the body and the log
line; these pin the ordering on a hand-built request, including a request with no
``Host`` header at all, which no HTTP client used in the suite can send.
"""

from __future__ import annotations

import pytest
from starlette.requests import Request

from app import gate_logging
from app.main import gate_reason

SECRET = "unit-origin-verify-secret-0123456789"


def make_request(headers: dict[str, str]) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/auth/status",
            "headers": [(k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in headers.items()],
            "client": ("10.0.0.9", 4242),
        }
    )


@pytest.fixture(autouse=True)
def production_env(monkeypatch):
    monkeypatch.setenv("PUBLIC_API_HOST", "api.mealy.dev")
    monkeypatch.setenv("ORIGIN_VERIFY_SECRET", SECRET)
    monkeypatch.delenv("GATE_BREAK_GLASS", raising=False)


def test_admits_the_public_host_with_the_origin_header():
    assert gate_reason(make_request({"host": "api.mealy.dev", "x-origin-verify": SECRET})) is None


def test_unset_public_api_host_is_checked_first(monkeypatch):
    monkeypatch.delenv("PUBLIC_API_HOST")
    # Every later check would also fail on this request; the first one wins.
    assert gate_reason(make_request({})) == gate_logging.PUBLIC_API_HOST_UNCONFIGURED


@pytest.mark.parametrize("headers", [{}, {"host": ""}, {"host": "   "}, {"host": ":443"}])
def test_missing_or_empty_host(headers):
    assert gate_reason(make_request(headers)) == gate_logging.HOST_ABSENT


def test_wrong_host_is_rejected_before_the_origin_checks():
    request = make_request({"host": "mealy-app-prod.fly.dev", "x-origin-verify": SECRET})
    assert gate_reason(request) == gate_logging.HOST_MISMATCH


def test_host_comparison_ignores_case_and_port():
    request = make_request({"host": "API.Mealy.dev:443", "x-origin-verify": SECRET})
    assert gate_reason(request) is None


def test_empty_secret_never_matches(monkeypatch):
    monkeypatch.setenv("ORIGIN_VERIFY_SECRET", "   ")
    request = make_request({"host": "api.mealy.dev", "x-origin-verify": ""})
    assert gate_reason(request) == gate_logging.ORIGIN_VERIFY_SECRET_EMPTY


def test_origin_header_absent():
    assert gate_reason(make_request({"host": "api.mealy.dev"})) == gate_logging.ORIGIN_VERIFY_ABSENT


@pytest.mark.parametrize("presented", ["", "wrong", SECRET[:-1], SECRET + "x", "sécret"])
def test_origin_header_mismatch(presented):
    request = make_request({"host": "api.mealy.dev", "x-origin-verify": presented})
    assert gate_reason(request) == gate_logging.ORIGIN_VERIFY_MISMATCH


def test_reasons_are_listed_in_decision_tree_order():
    assert gate_logging.REASONS == (
        "public_api_host_unconfigured",
        "host_absent",
        "host_mismatch",
        "origin_verify_secret_empty",
        "origin_verify_absent",
        "origin_verify_mismatch",
    )


# --- GATE_BREAK_GLASS (open question 3, Eng review 7) ------------------------


@pytest.mark.parametrize(
    ("value", "enabled"),
    [("1", True), ("0", False), ("", False), ("true", False), ("yes", False),
     ("TRUE", False), (" 1 ", False), ("1 ", False), ("01", False)],
)
def test_break_glass_parse_is_strict(monkeypatch, value, enabled):
    from app.main import break_glass_enabled

    monkeypatch.setenv("GATE_BREAK_GLASS", value)
    assert break_glass_enabled() is enabled


def test_break_glass_unset_is_off(monkeypatch):
    from app.main import break_glass_enabled

    monkeypatch.delenv("GATE_BREAK_GLASS", raising=False)
    assert break_glass_enabled() is False


def test_break_glass_skips_every_origin_check_and_nothing_else(monkeypatch):
    monkeypatch.setenv("GATE_BREAK_GLASS", "1")
    monkeypatch.setenv("ORIGIN_VERIFY_SECRET", "")
    # Origin-verify: absent header, empty secret — all admitted.
    assert gate_reason(make_request({"host": "api.mealy.dev"})) is None
    # The Host checks still run, in order.
    assert gate_reason(make_request({"host": "mealy-app-prod.fly.dev"})) == gate_logging.HOST_MISMATCH
    assert gate_reason(make_request({})) == gate_logging.HOST_ABSENT
    monkeypatch.delenv("PUBLIC_API_HOST")
    assert gate_reason(make_request({"host": "api.mealy.dev"})) == gate_logging.PUBLIC_API_HOST_UNCONFIGURED
