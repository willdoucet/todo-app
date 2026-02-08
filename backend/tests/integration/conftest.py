"""
Integration test fixtures with real PostgreSQL database.

These fixtures spin up a real PostgreSQL container using testcontainers,
create tables, and provide a clean database for each test.
"""

import os
import tempfile

# Set UPLOAD_DIR before importing app (app creates directory at import time)
_test_upload_dir = tempfile.mkdtemp(prefix="test_uploads_")
os.environ["UPLOAD_DIR"] = _test_upload_dir

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from httpx import AsyncClient, ASGITransport

from app.models import Base, FamilyMember, List, Task, CalendarEvent
from app.main import app
from app.database import get_db


# =============================================================================
# Database Container & Engine (session-scoped, non-async)
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


# =============================================================================
# Per-Test Database Session
# =============================================================================

@pytest_asyncio.fixture
async def db_session(postgres_url):
    """
    Provide a database session for each test.

    Creates fresh engine and tables for each test for isolation.
    """
    # Create fresh engine for this test
    engine = create_async_engine(postgres_url, echo=False)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

    # Drop all tables (clean slate for next test)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    # Dispose engine
    await engine.dispose()


# =============================================================================
# API Client Fixture
# =============================================================================

@pytest_asyncio.fixture
async def client(db_session):
    """
    Async HTTP client for testing API endpoints.

    Overrides the database dependency to use our test session.
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
        important=False,
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
        category="MORNING",
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
    """Create a test recipe in the database."""
    from app.models import Recipe

    recipe = Recipe(
        name="Test Recipe",
        description="A test recipe",
        ingredients=[
            {"name": "Test ingredient", "quantity": 1, "unit": "cups", "category": "Pantry"}
        ],
        instructions="Test instructions",
        prep_time_minutes=10,
        cook_time_minutes=20,
        servings=4,
        is_favorite=False,
        tags=["test"],
    )
    db_session.add(recipe)
    await db_session.commit()
    await db_session.refresh(recipe)
    return recipe


@pytest_asyncio.fixture
async def test_favorite_recipe(db_session):
    """Create a favorite test recipe in the database."""
    from app.models import Recipe

    recipe = Recipe(
        name="Favorite Recipe",
        description="A favorite recipe",
        ingredients=[{"name": "Ingredient", "quantity": 2, "unit": "cups", "category": "Pantry"}],
        instructions="Favorite instructions",
        prep_time_minutes=15,
        cook_time_minutes=30,
        servings=6,
        is_favorite=True,
        tags=["favorite", "test"],
    )
    db_session.add(recipe)
    await db_session.commit()
    await db_session.refresh(recipe)
    return recipe


@pytest_asyncio.fixture
async def test_meal_plan(db_session, test_recipe):
    """Create a test meal plan in the database."""
    from app.models import MealPlan
    from datetime import date

    meal_plan = MealPlan(
        date=date.today(),
        category="DINNER",
        recipe_id=test_recipe.id,
        was_cooked=False,
    )
    db_session.add(meal_plan)
    await db_session.commit()
    await db_session.refresh(meal_plan)
    return meal_plan


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
    """Create a test synced (non-MANUAL) calendar event."""
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
