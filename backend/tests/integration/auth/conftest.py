"""Auth-scoped integration test fixtures.

Inherits ``db_session`` and ``client`` from the parent integration
conftest. Adds:

- ``install_auth_test_config`` (autouse) — installs explicit dev-test
  auth secrets via :func:`app.auth.config.configure` so endpoints don't
  need ``JWT_SECRET_KEY`` / ``HOUSEHOLD_ACCESS_KEY`` env vars to run.
  Also swaps the password hasher for a fast-params instance so argon2
  doesn't burn 50ms per hash.
- ``register_user`` — convenience helper that POSTs /auth/register and
  returns ``(access_token, refresh_cookie_value, response)``.

Test design notes:

- The lifespan hook in ``app.main`` does not run under
  ``ASGITransport(app=app)``, so we install auth config explicitly here
  rather than relying on os.environ.
- Importing ``app.auth.models`` ensures User + RefreshToken are
  registered with ``Base.metadata`` before ``db_session`` runs
  ``create_all``. Without this, tests would silently see no auth tables.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from argon2 import PasswordHasher

from app.auth import config as auth_config
from app.auth import models as _auth_models  # noqa: F401  # register tables
from app.auth import passwords

TEST_HOUSEHOLD_ACCESS_KEY = "dev-access-key-for-integration-tests"
TEST_JWT_SECRET_KEY = "x" * 64  # 64-char string with no placeholder substring


@pytest.fixture(autouse=True)
def install_auth_test_config():
    """Install dev-test auth config + fast hasher for every test in this
    directory. Restores production defaults afterward."""
    test_cfg = auth_config.AuthConfig(
        jwt_secret_key=TEST_JWT_SECRET_KEY,
        household_access_key=TEST_HOUSEHOLD_ACCESS_KEY,
    )
    auth_config.configure(test_cfg)
    fast = PasswordHasher(memory_cost=8, time_cost=1, parallelism=1)
    passwords.set_password_hasher(fast)
    yield
    auth_config.reset()
    passwords.set_password_hasher(PasswordHasher())


@pytest_asyncio.fixture
async def register_user(client):
    """Convenience: register a user and return its tokens."""

    async def _register(
        email: str = "user@example.com",
        password: str = "correct-horse-battery-staple",
    ):
        resp = await client.post(
            "/auth/register",
            json={
                "email": email,
                "password": password,
                "access_key": TEST_HOUSEHOLD_ACCESS_KEY,
            },
        )
        assert resp.status_code == 200, resp.text
        access = resp.json()["access_token"]
        cookie = resp.cookies.get("__Host-refresh")
        return access, cookie, resp

    return _register
