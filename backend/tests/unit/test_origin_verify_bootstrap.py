"""Tests for the production origin-lock bootstrap in app.main.

The host gate rejects any production request whose `X-Origin-Verify` header
does not match `ORIGIN_VERIFY_SECRET`. With the secret missing, the gate fails
closed at request time: `/healthz` stays green, Fly keeps the machine, and
every real request 421s — invisible at the edge, total at the app layer.

REVIEW_CHECKLIST → FastAPI → Secrets & config requires failing at boot
instead, so the deploy fails and Fly keeps the previous image serving.
"""

import pytest

from app.main import _initialize_origin_verify


def test_noop_outside_production(monkeypatch):
    """The gate is off in dev and test; the secret is not required there."""
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ORIGIN_VERIFY_SECRET", raising=False)
    _initialize_origin_verify()  # must not raise


@pytest.mark.parametrize("value", [None, "", "   ", "too-short-secret"])
def test_production_refuses_to_boot_without_a_real_secret(monkeypatch, value):
    monkeypatch.setenv("APP_ENV", "production")
    if value is None:
        monkeypatch.delenv("ORIGIN_VERIFY_SECRET", raising=False)
    else:
        monkeypatch.setenv("ORIGIN_VERIFY_SECRET", value)

    with pytest.raises(RuntimeError, match="ORIGIN_VERIFY_SECRET") as exc:
        _initialize_origin_verify()

    # A too-short value is still a real credential; it must not reach the log.
    if value and value.strip():
        assert value not in str(exc.value)


def test_production_boots_with_a_32_char_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ORIGIN_VERIFY_SECRET", "x" * 32)
    _initialize_origin_verify()
