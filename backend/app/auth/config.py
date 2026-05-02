"""Auth configuration loader with fail-closed validation.

Two ways to install settings:

- Production / dev: lifespan (or app startup) calls ``load_from_env()`` and
  passes the result to ``configure()``. Missing, blank, too-short, or
  placeholder secrets raise ``AuthConfigError`` and the app refuses to boot.
- Tests: ``conftest.py`` calls ``configure(AuthConfig(...))`` directly with
  explicit dev-only values. The test override path never reads ``os.environ``.

Module import is intentionally side-effect-free — no env reads, no
validation. Validation is deferred to ``load_from_env()`` so test runs that
import ``app.main`` without auth env vars do not crash before the test
even gets a chance to install its overrides.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

# Substring deny list — any of these inside the lowercased secret value
# fails closed. Substring match is intentional: a base64 secret happening
# to contain "todo" is astronomically unlikely; a placeholder slipping
# into prod is the realistic failure mode.
PLACEHOLDER_DENY_LIST: tuple[str, ...] = (
    "changeme",
    "change-me",
    "your-secret",
    "your_secret",
    "placeholder",
    "example",
    "replace-me",
    "replace_me",
    "todo",
    "default",
    "insecure",
    "test-key",
    "test_key",
)

JWT_SECRET_MIN_LENGTH = 32


class AuthConfigError(RuntimeError):
    """Raised when an auth secret fails validation. Bubbles up out of startup."""


@dataclass(frozen=True)
class AuthConfig:
    """Validated auth secrets used by the rest of `app.auth`."""

    jwt_secret_key: str
    household_access_key: str


_settings: Optional[AuthConfig] = None


def _validate_secret(name: str, value: Optional[str], *, min_length: int = 0) -> str:
    """Apply the four fail-closed rules from the M3 plan to a single secret value."""
    if value is None:
        raise AuthConfigError(f"{name} is unset")
    stripped = value.strip()
    if not stripped:
        raise AuthConfigError(f"{name} is blank after stripping whitespace")
    if min_length and len(stripped) < min_length:
        raise AuthConfigError(
            f"{name} must be at least {min_length} characters; got {len(stripped)}"
        )
    lowered = stripped.lower()
    for placeholder in PLACEHOLDER_DENY_LIST:
        if placeholder in lowered:
            raise AuthConfigError(
                f"{name} contains forbidden placeholder substring '{placeholder}'"
            )
    return stripped


def load_from_env() -> AuthConfig:
    """Read process env and apply fail-closed validation. Production lifespan path."""
    jwt_key = _validate_secret(
        "JWT_SECRET_KEY",
        os.environ.get("JWT_SECRET_KEY"),
        min_length=JWT_SECRET_MIN_LENGTH,
    )
    access_key = _validate_secret(
        "HOUSEHOLD_ACCESS_KEY",
        os.environ.get("HOUSEHOLD_ACCESS_KEY"),
    )
    return AuthConfig(jwt_secret_key=jwt_key, household_access_key=access_key)


def configure(settings: AuthConfig) -> None:
    """Install validated settings. Called once at startup, or directly from tests."""
    global _settings
    _settings = settings


def get_settings() -> AuthConfig:
    """Read installed settings. Raises if no one has configured() yet."""
    if _settings is None:
        raise AuthConfigError(
            "Auth config not initialized. Call configure() during startup."
        )
    return _settings


def reset() -> None:
    """Clear installed settings. Test helper — not for production code."""
    global _settings
    _settings = None
