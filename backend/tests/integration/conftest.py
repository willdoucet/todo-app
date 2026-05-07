"""
Integration test fixtures with real PostgreSQL database.

These fixtures spin up a real PostgreSQL container (via testcontainers
locally, the GitHub Actions postgres service in CI, or todo_app_test
inside docker-compose), create schema once per session, and isolate
each test via per-test transaction rollback.

M5 PR1: every protected route now requires a valid Authorization header
(`Bearer <jwt>`). The `client` fixture mints a fresh JWT per test and
attaches it as a default header — so existing tests stay green without
any test-file edits. An `unauth_client` fixture is provided for tests
that need to exercise the 401 path explicitly.
"""

import os
import tempfile

# Set UPLOAD_DIR before importing app (app creates directory at import time)
_test_upload_dir = tempfile.mkdtemp(prefix="test_uploads_")
os.environ["UPLOAD_DIR"] = _test_upload_dir

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
from httpx import AsyncClient, ASGITransport

from app.models import Base, FamilyMember, List, Task, CalendarEvent
from app.main import app
from app.database import get_db


# =============================================================================
# Auth Config — autouse session fixture (M5 PR1)
# =============================================================================
#
# Integration tests use ASGITransport(app=app), which does NOT run
# FastAPI's lifespan, so `_initialize_auth_config` from `main.py` never
# fires. Without this fixture, the first `tokens.encode_access_token`
# call (or any `Depends(get_current_user)` evaluation) would raise
# AuthConfigError("Auth config not initialized…").
#
# Mirrors the unit-test pattern at tests/unit/auth/test_dependencies.py.
#
# Function-scoped autouse (not session-scoped) because the auth subfolder
# (tests/integration/auth/) has its own per-test `install_auth_test_config`
# that calls `auth_config.reset()` at teardown — leaving `_settings=None`
# for any test that runs afterward. Function scope re-installs before
# every test so the next test (in any folder, including the auth subfolder
# itself) always starts with a fresh, configured auth state. Switching
# this to session scope would brick every integration test ordered
# after an auth-subfolder test.

@pytest.fixture(autouse=True)
def install_auth_config():
    from app.auth import config as auth_config

    auth_config.configure(auth_config.AuthConfig(
        jwt_secret_key="x" * 64,
        household_access_key="dev-access-key",
    ))
    yield
    auth_config.reset()


# =============================================================================
# Database Container & Engine (session-scoped)
# =============================================================================

@pytest.fixture(scope="session")
def postgres_url():
    """
    Get PostgreSQL connection URL.

    For CI (GitHub Actions), uses the service container.
    For local development, uses testcontainers to spin up PostgreSQL.
    """
    # Check if running in CI with pre-configured test database
    # NOTE: Uses TEST_DATABASE_URL (not DATABASE_URL) to avoid accidentally
    # connecting to the live dev database when running inside docker-compose.
    if os.environ.get("TEST_DATABASE_URL"):
        return os.environ["TEST_DATABASE_URL"]

    # Local development: use testcontainers
    from testcontainers.postgres import PostgresContainer

    postgres = PostgresContainer("postgres:15")
    postgres.start()

    # Convert the URL to async format
    url = postgres.get_connection_url()
    if "postgresql+psycopg2://" in url:
        async_url = url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    else:
        async_url = url.replace("postgresql://", "postgresql+asyncpg://")

    # Store container reference for cleanup
    pytest.postgres_container = postgres

    return async_url


# Session-scoped engine: shared across all integration tests via the
# session-scoped event loop. Per-test isolation is achieved through
# transaction rollback inside the `db_session` fixture below.
#
# Schema setup is intentionally NOT done here — it lives inside
# `db_session` so that a per-test, idempotent `create_all` heals the
# schema if a previous test (e.g. tests/integration/auth/test_refresh.py
# at L180-182) ran its own `Base.metadata.drop_all` and left the DB
# table-less. `Base.metadata.create_all` is idempotent
# (CREATE TABLE IF NOT EXISTS), so paying the cost per-test is cheap
# and the alternative (rebuilding the test runner's order assumptions)
# is much riskier.

@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def test_engine(postgres_url):
    engine = create_async_engine(postgres_url, echo=False)
    yield engine
    # Final cleanup: drop the schema so a downstream consumer of
    # `todo_app_test` (e.g. the visual-test profile's api-test container,
    # which runs `alembic upgrade head` at boot) starts from a known
    # empty DB. Original conftest achieved this via per-test drop_all;
    # we do it once at session end instead. Idempotent — drop_all on a
    # missing table is a no-op.
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    finally:
        await engine.dispose()


# =============================================================================
# Per-Test Database Session — transaction rollback isolation (M5 PR1)
# =============================================================================
#
# Schema is verified-and-created idempotently before each test. Per-test
# data is rolled back via SAVEPOINT-mode transaction.
#
# `join_transaction_mode='create_savepoint'` keeps existing
# `await db_session.commit()` calls transparent — the commit ends the
# inner SAVEPOINT instead of releasing the outer transaction, so
# cross-test isolation holds. Without this, a route handler's
# `await db.commit()` would commit the test's data to the table for
# real, defeating rollback isolation.
#
# INCOMPATIBLE WITH pytest-xdist: the per-test `ALTER SEQUENCE ... RESTART
# WITH 1` below is non-transactional and globally visible. Parallel workers
# would race on sequence values and produce duplicate-key errors with no
# obvious cause. Keep tests serial (default pytest behavior).

@pytest_asyncio.fixture
async def db_session(test_engine):
    # Idempotent schema verification — heals the schema if a previous
    # test (e.g. test_refresh.py's manual drop_all) torched it.
    # Also resets all auto-increment sequences to 1: PostgreSQL
    # sequences are NOT transactional, so a rolled-back INSERT still
    # advances the sequence. Without this, tests that hardcode
    # `assert user.id == 1` start failing once enough prior tests have
    # auto-inserted users (e.g. via the auth_user fixture).
    async with test_engine.begin() as setup_conn:
        await setup_conn.execute(text("CREATE EXTENSION IF NOT EXISTS citext"))
        await setup_conn.run_sync(Base.metadata.create_all)
        seq_rows = await setup_conn.execute(
            text(
                "SELECT sequence_name FROM information_schema.sequences "
                "WHERE sequence_schema = 'public'"
            )
        )
        for (seq_name,) in seq_rows.fetchall():
            await setup_conn.execute(text(f'ALTER SEQUENCE "{seq_name}" RESTART WITH 1'))

    async with test_engine.connect() as conn:
        outer = await conn.begin()
        session = AsyncSession(
            bind=conn,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            await session.close()
            await outer.rollback()


# =============================================================================
# Auth User & Headers (M5 PR1)
# =============================================================================
#
# Per-test fixture user. Inserted into the users table inside the test's
# SAVEPOINT-mode transaction so the FastAPI handler (which shares the
# session via `dependency_override`) sees it on validate_bearer's live
# DB lookup. Rolled back at teardown along with everything else the
# test wrote.
#
# The upsert pattern (`ON CONFLICT (email) DO UPDATE`) is defensive —
# it tolerates a previous test session that crashed mid-run and left a
# stale `auth-test@local` row behind. Within a clean session, no
# conflict ever fires.

@pytest_asyncio.fixture
async def auth_user(db_session):
    result = await db_session.execute(
        text(
            "INSERT INTO users (email, password_hash, session_version) "
            "VALUES (:email, :hash, :sv) "
            "ON CONFLICT (email) DO UPDATE "
            "  SET session_version = EXCLUDED.session_version "
            "RETURNING id"
        ),
        {
            "email": "auth-test@local",
            # password_hash is never read on the JWT path; literal
            # string avoids ~700ms argon2 cost per insert.
            "hash": "argon2-placeholder-not-validated-on-jwt-path",
            "sv": 1,
        },
    )
    row = result.fetchone()
    # Release the SAVEPOINT so the FastAPI handler (which uses the same
    # AsyncSession via dependency_override) sees the row on its
    # subsequent SELECT during validate_bearer.
    await db_session.commit()
    return {"id": row[0], "email": "auth-test@local", "session_version": 1}


@pytest.fixture
def auth_headers(auth_user):
    """Mint a fresh access JWT for auth_user; return {'Authorization': 'Bearer <jwt>'}.

    Mints directly via `tokens.encode_access_token` (rather than calling
    `/auth/login`) to skip the registration/login round-trip per test.
    The auth dependency itself is exhaustively unit-tested at the JWT
    layer; integration tests only need a valid Authorization header to
    exercise downstream behavior.
    """
    from app.auth import tokens

    token = tokens.encode_access_token(
        user_id=auth_user["id"],
        session_version=auth_user["session_version"],
    )
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# API Client Fixture
# =============================================================================
#
# M5 PR1 deviation from plan: the plan threaded `auth_headers` through
# every `await client.X(...)` call across 18 test files (~273 call
# sites). Instead, the `client` fixture installs `auth_headers` as
# default request headers on the AsyncClient — same outcome (real JWT
# path through every protected route on the happy path), zero test-file
# edits, much smaller blast radius. Per-call `headers={...}` kwargs in
# existing tests still merge cleanly with the default auth header.
#
# Tests that need an unauthenticated client (e.g. test_auth_enforcement.py)
# use the sibling `unauth_client` fixture below.

@pytest_asyncio.fixture
async def client(db_session, auth_headers):
    """
    Async HTTP client for testing API endpoints.

    Overrides the database dependency to use our test session and
    attaches a valid Bearer token as a default header so every
    M5-protected route returns 200 on the happy path.
    """
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers=auth_headers,
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def unauth_client(db_session):
    """Async HTTP client without a default Authorization header.

    Used by tests that need to verify 401 behavior on protected routes
    (e.g. test_auth_enforcement.py).
    """
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


# =============================================================================
# Test Data Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def test_family_member(db_session):
    """Create a test family member in the database."""
    member = FamilyMember(name="Test User", is_system=False, color="#3B82F6")
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(member)
    return member


@pytest_asyncio.fixture
async def test_system_member(db_session):
    """Create the system 'Everyone' member in the database."""
    member = FamilyMember(name="Everyone", is_system=True, color="#D97452")
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(member)
    return member


@pytest_asyncio.fixture
async def test_list(db_session):
    """Create a test list in the database."""
    list_obj = List(name="Test List", color="#EF4444", icon="clipboard")
    db_session.add(list_obj)
    await db_session.commit()
    await db_session.refresh(list_obj)
    return list_obj


@pytest_asyncio.fixture
async def test_task(db_session, test_list, test_family_member):
    """Create a test task in the database."""
    task = Task(
        title="Test Task",
        description="A test task",
        list_id=test_list.id,
        assigned_to=test_family_member.id,
        completed=False,
        priority=0,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


@pytest_asyncio.fixture
async def test_responsibility(db_session, test_family_member):
    """Create a test responsibility in the database."""
    from app.models import Responsibility

    responsibility = Responsibility(
        title="Make bed",
        description="Make your bed every morning",
        categories=["MORNING"],
        assigned_to=test_family_member.id,
        frequency=["monday", "tuesday", "wednesday", "thursday", "friday"],
        icon_url=None,
    )
    db_session.add(responsibility)
    await db_session.commit()
    await db_session.refresh(responsibility)
    return responsibility


# =============================================================================
# Mealboard Test Data Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def test_recipe(db_session):
    """Create a test recipe as an Item + RecipeDetail pair.

    Migrated from the legacy Recipe model after the item-model refactor. The return
    value is an Item with .recipe_detail populated so existing tests that access
    recipe.name / recipe.id / recipe.is_favorite still work; tests that read detail
    fields (description, ingredients, instructions, prep/cook time, servings) must
    go through .recipe_detail.
    """
    from app.models import Item, RecipeDetail

    item = Item(
        name="Test Recipe",
        item_type="recipe",
        is_favorite=False,
        tags=["test"],
    )
    db_session.add(item)
    await db_session.flush()
    detail = RecipeDetail(
        item_id=item.id,
        description="A test recipe",
        ingredients=[
            {"name": "Test ingredient", "quantity": 1, "unit": "cup", "category": "Pantry"}
        ],
        instructions="Test instructions",
        prep_time_minutes=10,
        cook_time_minutes=20,
        servings=4,
    )
    db_session.add(detail)
    await db_session.commit()
    await db_session.refresh(item)
    return item


@pytest_asyncio.fixture
async def test_favorite_recipe(db_session):
    """Create a favorite test recipe as an Item + RecipeDetail pair."""
    from app.models import Item, RecipeDetail

    item = Item(
        name="Favorite Recipe",
        item_type="recipe",
        is_favorite=True,
        tags=["favorite", "test"],
    )
    db_session.add(item)
    await db_session.flush()
    detail = RecipeDetail(
        item_id=item.id,
        description="A favorite recipe",
        ingredients=[{"name": "Ingredient", "quantity": 2, "unit": "cup", "category": "Pantry"}],
        instructions="Favorite instructions",
        prep_time_minutes=15,
        cook_time_minutes=30,
        servings=6,
    )
    db_session.add(detail)
    await db_session.commit()
    await db_session.refresh(item)
    return item


@pytest_asyncio.fixture
async def test_meal_slot_types(db_session):
    """Create the 4 default meal slot types (Breakfast, Lunch, Dinner, Snack)."""
    from app.models import MealSlotType

    slots = [
        MealSlotType(name="Breakfast", sort_order=1, color="#F5A623", icon="☀", is_default=True, default_participants=[]),
        MealSlotType(name="Lunch", sort_order=2, color="#6B8F71", icon="🥪", is_default=True, default_participants=[]),
        MealSlotType(name="Dinner", sort_order=3, color="#E8927C", icon="🍽", is_default=True, default_participants=[]),
        MealSlotType(name="Snack", sort_order=4, color="#B8A9C9", icon="🍌", is_default=True, default_participants=[]),
    ]
    for slot in slots:
        db_session.add(slot)
    await db_session.commit()
    for slot in slots:
        await db_session.refresh(slot)
    return slots


@pytest_asyncio.fixture
async def test_meal_slot_dinner(test_meal_slot_types):
    """Return just the Dinner slot type for convenience."""
    return test_meal_slot_types[2]  # Dinner


@pytest_asyncio.fixture
async def test_food_item(db_session):
    """Create a test food item as an Item + FoodItemDetail pair."""
    from app.models import Item, FoodItemDetail
    from decimal import Decimal

    item = Item(
        name="Banana",
        item_type="food_item",
        icon_emoji="🍌",
        is_favorite=False,
    )
    db_session.add(item)
    await db_session.flush()
    detail = FoodItemDetail(
        item_id=item.id,
        category="fruit",
        shopping_quantity=Decimal("1.0"),
        shopping_unit="each",
    )
    db_session.add(detail)
    await db_session.commit()
    await db_session.refresh(item)
    return item


@pytest_asyncio.fixture
async def test_meal_entry(db_session, test_recipe, test_meal_slot_dinner):
    """Create a test meal entry (dinner with a recipe)."""
    from app.models import MealEntry
    from datetime import date

    entry = MealEntry(
        date=date.today(),
        meal_slot_type_id=test_meal_slot_dinner.id,
        item_id=test_recipe.id,
        was_cooked=False,
    )
    db_session.add(entry)
    await db_session.commit()
    await db_session.refresh(entry)
    return entry


@pytest_asyncio.fixture
async def test_app_settings(db_session):
    """Create the singleton app settings row."""
    from app.models import AppSettings

    settings = AppSettings(
        timezone="UTC",
        week_start_day="monday",
        measurement_system="imperial",
    )
    db_session.add(settings)
    await db_session.commit()
    await db_session.refresh(settings)
    return settings


# =============================================================================
# Calendar Event Test Data Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def test_calendar_event(db_session, test_family_member):
    """Create a test calendar event in the database."""
    from datetime import date

    event = CalendarEvent(
        title="Test Event",
        description="A test event",
        date=date(2026, 2, 10),
        start_time="09:00",
        end_time="10:00",
        all_day=False,
        source="MANUAL",
        assigned_to=test_family_member.id,
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    return event


@pytest_asyncio.fixture
async def test_all_day_event(db_session):
    """Create a test all-day calendar event in the database."""
    from datetime import date

    event = CalendarEvent(
        title="All Day Event",
        date=date(2026, 2, 10),
        all_day=True,
        source="MANUAL",
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    return event


@pytest_asyncio.fixture
async def test_synced_event(db_session):
    """Create a test synced iCloud calendar event."""
    from datetime import date

    event = CalendarEvent(
        title="Synced Event",
        date=date(2026, 2, 10),
        start_time="14:00",
        end_time="15:00",
        source="ICLOUD",
        external_id="icloud-123",
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    return event


@pytest_asyncio.fixture
async def test_google_event(db_session):
    """Create a test Google Calendar event (not editable/deletable)."""
    from datetime import date

    event = CalendarEvent(
        title="Google Event",
        date=date(2026, 2, 10),
        start_time="10:00",
        end_time="11:00",
        source="GOOGLE",
        external_id="google-456",
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    return event
