"""Unit tests for app.auth.config — fail-closed validation rules.

One assertion (or one parametrize ID) per rule from the M3 plan's
"Auth secrets fail closed" enumeration:

1. Both secrets unset → fail.
2. Each secret in isolation unset → fail.
3. Whitespace-only value → fail.
4. JWT_SECRET_KEY length 31 → fail; length 32 → pass.
5. Each placeholder substring → fail (case-insensitive substring match).
6. Genuine `secrets.token_urlsafe(32)` value → pass.
7. Test override (`configure()`) bypasses validation and does not read process env.
8. Importing `app.auth.config` without env vars set does not raise.
"""

import importlib
import secrets

import pytest

from app.auth import config as auth_config
from app.auth.config import (
    PLACEHOLDER_DENY_LIST,
    AuthConfig,
    AuthConfigError,
    JWT_SECRET_MIN_LENGTH,
)


VALID_JWT = secrets.token_urlsafe(48)  # 64-char url-safe — well above min length
VALID_AK = secrets.token_urlsafe(32)


@pytest.fixture(autouse=True)
def _reset_auth_config():
    """Make sure each test starts with a fresh, uninstalled config."""
    auth_config.reset()
    yield
    auth_config.reset()


@pytest.fixture
def clean_env(monkeypatch):
    """Strip auth env vars; let each test set what it needs."""
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.delenv("HOUSEHOLD_ACCESS_KEY", raising=False)
    return monkeypatch


# =============================================================================
# Rule 1 — Both secrets unset
# =============================================================================

def test_both_secrets_unset_fails(clean_env):
    with pytest.raises(AuthConfigError, match="JWT_SECRET_KEY is unset"):
        auth_config.load_from_env()


# =============================================================================
# Rule 2 — Each secret in isolation unset
# =============================================================================

def test_jwt_unset_only_fails(clean_env):
    clean_env.setenv("HOUSEHOLD_ACCESS_KEY", VALID_AK)
    with pytest.raises(AuthConfigError, match="JWT_SECRET_KEY is unset"):
        auth_config.load_from_env()


def test_household_unset_only_fails(clean_env):
    clean_env.setenv("JWT_SECRET_KEY", VALID_JWT)
    with pytest.raises(AuthConfigError, match="HOUSEHOLD_ACCESS_KEY is unset"):
        auth_config.load_from_env()


# =============================================================================
# Rule 3 — Whitespace-only value
# =============================================================================

def test_jwt_whitespace_only_fails(clean_env):
    clean_env.setenv("JWT_SECRET_KEY", "   \t \n  ")
    clean_env.setenv("HOUSEHOLD_ACCESS_KEY", VALID_AK)
    with pytest.raises(AuthConfigError, match="JWT_SECRET_KEY is blank"):
        auth_config.load_from_env()


def test_household_whitespace_only_fails(clean_env):
    clean_env.setenv("JWT_SECRET_KEY", VALID_JWT)
    clean_env.setenv("HOUSEHOLD_ACCESS_KEY", "   ")
    with pytest.raises(AuthConfigError, match="HOUSEHOLD_ACCESS_KEY is blank"):
        auth_config.load_from_env()


# =============================================================================
# Rule 4 — JWT_SECRET_KEY length boundary (31 fails, 32 passes)
# =============================================================================

def test_jwt_length_31_fails(clean_env):
    clean_env.setenv("JWT_SECRET_KEY", "x" * 31)
    clean_env.setenv("HOUSEHOLD_ACCESS_KEY", VALID_AK)
    with pytest.raises(AuthConfigError, match=f"at least {JWT_SECRET_MIN_LENGTH}"):
        auth_config.load_from_env()


def test_jwt_length_32_passes(clean_env):
    # Use a 32-char string that contains no placeholder substring.
    clean_env.setenv("JWT_SECRET_KEY", "abcdefghijklmnopqrstuvwxyz012345")
    clean_env.setenv("HOUSEHOLD_ACCESS_KEY", VALID_AK)
    cfg = auth_config.load_from_env()
    assert len(cfg.jwt_secret_key) == JWT_SECRET_MIN_LENGTH


def test_household_min_length_not_enforced(clean_env):
    """HOUSEHOLD_ACCESS_KEY has no minimum length; only the 4 substantive checks apply."""
    clean_env.setenv("JWT_SECRET_KEY", VALID_JWT)
    clean_env.setenv("HOUSEHOLD_ACCESS_KEY", "short")
    cfg = auth_config.load_from_env()
    assert cfg.household_access_key == "short"


# =============================================================================
# Rule 5 — Placeholder substring deny-list
# =============================================================================

@pytest.mark.parametrize("placeholder", PLACEHOLDER_DENY_LIST)
def test_placeholder_in_jwt_fails(clean_env, placeholder):
    # Pad to satisfy length rule, so the failure must be the placeholder check.
    value = placeholder + "z" * 32
    clean_env.setenv("JWT_SECRET_KEY", value)
    clean_env.setenv("HOUSEHOLD_ACCESS_KEY", VALID_AK)
    with pytest.raises(AuthConfigError, match="forbidden placeholder substring"):
        auth_config.load_from_env()


@pytest.mark.parametrize("placeholder", PLACEHOLDER_DENY_LIST)
def test_placeholder_in_household_fails(clean_env, placeholder):
    clean_env.setenv("JWT_SECRET_KEY", VALID_JWT)
    clean_env.setenv("HOUSEHOLD_ACCESS_KEY", placeholder + "abc")
    with pytest.raises(AuthConfigError, match="forbidden placeholder substring"):
        auth_config.load_from_env()


def test_placeholder_match_is_case_insensitive(clean_env):
    clean_env.setenv("JWT_SECRET_KEY", "ChangeMe" + "x" * 32)
    clean_env.setenv("HOUSEHOLD_ACCESS_KEY", VALID_AK)
    with pytest.raises(AuthConfigError, match="changeme"):
        auth_config.load_from_env()


# =============================================================================
# Rule 6 — Genuine secrets.token_urlsafe value passes
# =============================================================================

def test_genuine_token_urlsafe_passes(clean_env):
    clean_env.setenv("JWT_SECRET_KEY", VALID_JWT)
    clean_env.setenv("HOUSEHOLD_ACCESS_KEY", VALID_AK)
    cfg = auth_config.load_from_env()
    assert cfg.jwt_secret_key == VALID_JWT
    assert cfg.household_access_key == VALID_AK


# =============================================================================
# Rule 7 — Test override path bypasses production validation, does not read env
# =============================================================================

def test_configure_bypasses_env_and_validation(monkeypatch):
    """The conftest test path uses configure() with explicit values. It must
    NOT call load_from_env(), must NOT touch os.environ, and must NOT
    invoke the placeholder/length validators."""
    # Set obviously-bad env values; configure() should ignore them entirely.
    monkeypatch.setenv("JWT_SECRET_KEY", "changeme")  # would fail validation
    monkeypatch.setenv("HOUSEHOLD_ACCESS_KEY", "")  # would fail validation

    test_cfg = AuthConfig(
        jwt_secret_key="dev-test-jwt-secret-key-32-chars",
        household_access_key="dev-access-key",
    )
    auth_config.configure(test_cfg)
    assert auth_config.get_settings() is test_cfg


def test_get_settings_before_configure_raises():
    auth_config.reset()
    with pytest.raises(AuthConfigError, match="not initialized"):
        auth_config.get_settings()


# =============================================================================
# Rule 8 — Module import is side-effect-free
# =============================================================================

def test_module_import_is_side_effect_free(clean_env):
    """Reimporting app.auth.config without auth env vars set does not validate."""
    # No exception expected.
    importlib.reload(auth_config)


def test_app_main_import_does_not_validate_auth(clean_env):
    """Importing app.main without auth env vars set must not crash. Auth
    validation is deferred to lifespan/startup, so the import path stays clean."""
    import app.main
    importlib.reload(app.main)
