"""Pydantic models for the auth endpoints.

The schemas are intentionally minimal. Validation that COULD distinguish
paired-failure cases (e.g., "password too long" returning 422 from login)
is handled in the route/service layer instead — see ``service.login``.
Endpoint-level validation runs first, so anything that lands in 422 here
is a body-shape failure, not an auth decision.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# Argon2 hard limit on password length is 128 chars.
PASSWORD_MAX_LENGTH = 128


class RegisterIn(BaseModel):
    """``POST /auth/register`` body."""

    model_config = ConfigDict(str_strip_whitespace=False)

    email: EmailStr
    # Register enforces ≤128 chars at the schema layer (422 on overlong).
    # This is the ONE auth path where 422 is the right response — it's
    # not enumeration-prone (there's no "right" or "wrong" account yet).
    password: str = Field(..., min_length=1, max_length=PASSWORD_MAX_LENGTH)
    access_key: str = Field(..., min_length=1)


class LoginIn(BaseModel):
    """``POST /auth/login`` body.

    NOTE: no ``max_length`` on ``password``. Login intentionally accepts
    any length string and collapses to the byte-identical 401 in the
    handler — a 422 on overlong login would be a length oracle. The
    handler short-circuits on ``len(password) > PASSWORD_MAX_LENGTH``
    with ``invalid_credentials`` BEFORE invoking argon2.
    """

    email: EmailStr
    password: str = Field(..., min_length=1)


class AccessTokenOut(BaseModel):
    """Response body for register/login/refresh on success."""

    access_token: str
    token_type: str = "bearer"


class AuthStatusOut(BaseModel):
    """Response body for ``GET /auth/status``. Public, no auth required."""

    account_exists: bool
