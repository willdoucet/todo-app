"""Single source for byte-identical auth error responses.

Each helper returns a :class:`fastapi.HTTPException` whose status_code and
detail are FIXED for every paired failure case. The optional ``reason``
kwarg attaches a categorical log code (``log_reason``) to the exception so
the route handler can emit a meaningful structured log line WITHOUT
leaking the categorical reason in the response body. Byte-identicality
is verified by the integration suite over (status, body, headers).

Reason codes (from the plan's Observability section):
    register   → bad_access_key, account_exists, race_loser
    login      → bad_credentials, password_too_long
    refresh    → bad_refresh, bad_refresh_revoked, bad_refresh_expired,
                 bad_refresh_superseded, bad_refresh_chain
    logout/dep → unauthorized
"""

from __future__ import annotations

from fastapi import HTTPException, status


def _attach_reason(exc: HTTPException, reason: str) -> HTTPException:
    """Stash the log reason on the exception so the route handler can read
    it for the structured log line. The reason NEVER goes into the
    response body — it lives on the Python object only."""
    exc.log_reason = reason  # type: ignore[attr-defined]
    return exc


def registration_unavailable(reason: str = "registration_unavailable") -> HTTPException:
    """401 / ``registration_unavailable`` — wrong access key, account
    already exists, OR concurrent register loser. Body is identical
    across all three; only the log reason differs."""
    return _attach_reason(
        HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="registration_unavailable",
        ),
        reason,
    )


def invalid_credentials(reason: str = "bad_credentials") -> HTTPException:
    """401 / ``invalid_credentials`` — unknown email, wrong password, OR
    overlong login password. All three log ``bad_credentials`` per
    enumeration-in-logs defense."""
    return _attach_reason(
        HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_credentials",
        ),
        reason,
    )


def refresh_failed(reason: str = "bad_refresh") -> HTTPException:
    """401 / ``refresh_failed`` — cookie unknown / revoked / expired /
    superseded-past-grace / chain-corrupt. Body identical across all
    five; reason in log only."""
    return _attach_reason(
        HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="refresh_failed",
        ),
        reason,
    )


def unauthorized(reason: str = "unauthorized") -> HTTPException:
    """401 / ``unauthorized`` — every JWT / bearer-header / live-DB
    failure path inside ``get_current_user``."""
    return _attach_reason(
        HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="unauthorized",
        ),
        reason,
    )
