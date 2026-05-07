"""Auth-scoped integration test fixtures.

Inherits ``db_session`` from the parent integration conftest, and
overrides ``client`` so auth tests run against an UNauthenticated
HTTP client. The parent ``client`` fixture pre-attaches a Bearer JWT
for a per-test ``auth_user`` row that gets inserted on every test
pulling the parent ``client``; that would break tests like
"register first user when none exists" — they'd see
``account_exists: True`` because the auto-injected user is already there.

Adds:

- ``install_auth_test_config`` (autouse) — installs explicit dev-test
  auth secrets via :func:`app.auth.config.configure` so endpoints don't
  need ``JWT_SECRET_KEY`` / ``HOUSEHOLD_ACCESS_KEY`` env vars to run.
  Also swaps the password hasher for a fast-params instance so argon2
  doesn't burn 50ms per hash.
- ``client`` — overrides the parent fixture to drop the default Bearer
  header and the ``auth_user`` dependency.
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
from httpx import AsyncClient, ASGITransport

from app.auth import config as auth_config
from app.auth import models as _auth_models  # noqa: F401  # register tables
from app.auth import passwords
from app.database import get_db
from app.main import app

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
async def client(db_session):
    """Override the parent `client` fixture: NO default Bearer header,
    NO `auth_user` dependency. Auth subfolder tests own their auth state
    end-to-end (register, login, logout, refresh).
    """

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


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
