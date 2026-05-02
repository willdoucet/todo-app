"""Unit tests for app.auth.errors — single source for byte-identical responses.

Each helper must produce the exact same status_code + detail every call;
multiple paired-failure cases that share a helper must produce
indistinguishable responses.
"""

from __future__ import annotations

from app.auth import errors


def _shape(exc) -> tuple[int, object]:
    return (exc.status_code, exc.detail)


def test_registration_unavailable_is_stable_across_calls():
    a = errors.registration_unavailable()
    b = errors.registration_unavailable()
    assert _shape(a) == _shape(b)
    assert a.status_code == 401
    assert a.detail == "registration_unavailable"


def test_invalid_credentials_is_stable_across_calls():
    a = errors.invalid_credentials()
    b = errors.invalid_credentials()
    assert _shape(a) == _shape(b)
    assert a.status_code == 401
    assert a.detail == "invalid_credentials"


def test_refresh_failed_is_stable_across_calls():
    a = errors.refresh_failed()
    b = errors.refresh_failed()
    assert _shape(a) == _shape(b)
    assert a.status_code == 401
    assert a.detail == "refresh_failed"


def test_unauthorized_is_stable_across_calls():
    a = errors.unauthorized()
    b = errors.unauthorized()
    assert _shape(a) == _shape(b)
    assert a.status_code == 401
    assert a.detail == "unauthorized"


def test_helpers_have_distinct_detail_strings():
    """The four helpers must produce different bodies — they're paired
    differently. Mixing them up would defeat enumeration defense."""
    details = {
        errors.registration_unavailable().detail,
        errors.invalid_credentials().detail,
        errors.refresh_failed().detail,
        errors.unauthorized().detail,
    }
    assert len(details) == 4
