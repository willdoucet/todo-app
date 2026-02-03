"""
Shared pytest fixtures for all tests.

Fixtures defined here are automatically available to both unit and integration tests.
"""

import pytest
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock


# =============================================================================
# Sample Data Fixtures
# =============================================================================

@pytest.fixture
def sample_family_member_data():
    """Sample data for creating a family member."""
    return {
        "name": "Alice",
        "is_system": False,
        "photo_url": None,
    }


@pytest.fixture
def sample_task_data():
    """Sample data for creating a task."""
    return {
        "title": "Buy groceries",
        "description": "Milk, eggs, bread",
        "due_date": date.today().isoformat(),
        "completed": False,
        "important": False,
        "assigned_to": None,
        "list_id": None,
    }


@pytest.fixture
def sample_list_data():
    """Sample data for creating a list."""
    return {
        "name": "Personal",
        "color": "#EF4444",
        "icon": "clipboard",
    }


@pytest.fixture
def sample_responsibility_data():
    """Sample data for creating a responsibility."""
    return {
        "title": "Make bed",
        "description": "Make your bed every morning",
        "category": "MORNING",
        "assigned_to": None,
        "frequency": ["monday", "tuesday", "wednesday", "thursday", "friday"],
        "icon_url": None,
    }


# =============================================================================
# Mock Fixtures for Unit Tests
# =============================================================================

@pytest.fixture
def mock_db_session():
    """
    A mocked AsyncSession for unit tests.

    This allows testing CRUD functions without a real database.
    You can configure return values in individual tests:

        mock_db_session.execute.return_value.scalar_one_or_none.return_value = some_value
    """
    session = AsyncMock()

    # Mock the execute method to return a result-like object
    mock_result = MagicMock()
    session.execute.return_value = mock_result

    return session


@pytest.fixture
def mock_family_member():
    """A mock FamilyMember object for unit tests."""
    member = MagicMock()
    member.id = 1
    member.name = "Alice"
    member.is_system = False
    member.photo_url = None
    member.created_at = datetime.now()
    member.updated_at = datetime.now()
    return member


@pytest.fixture
def mock_system_member():
    """A mock system FamilyMember (Everyone) for unit tests."""
    member = MagicMock()
    member.id = 1
    member.name = "Everyone"
    member.is_system = True
    member.photo_url = None
    member.created_at = datetime.now()
    member.updated_at = datetime.now()
    return member


@pytest.fixture
def mock_task():
    """A mock Task object for unit tests."""
    task = MagicMock()
    task.id = 1
    task.title = "Buy groceries"
    task.description = "Milk, eggs, bread"
    task.due_date = date.today()
    task.completed = False
    task.important = False
    task.assigned_to = None
    task.list_id = 1
    task.created_at = datetime.now()
    task.updated_at = datetime.now()
    return task


@pytest.fixture
def mock_list():
    """A mock List object for unit tests."""
    list_obj = MagicMock()
    list_obj.id = 1
    list_obj.name = "Personal"
    list_obj.color = "#EF4444"
    list_obj.icon = "clipboard"
    list_obj.created_at = datetime.now()
    list_obj.updated_at = datetime.now()
    return list_obj


@pytest.fixture
def mock_responsibility():
    """A mock Responsibility object for unit tests."""
    responsibility = MagicMock()
    responsibility.id = 1
    responsibility.title = "Make bed"
    responsibility.description = "Make your bed every morning"
    responsibility.category = "MORNING"
    responsibility.assigned_to = 2
    responsibility.frequency = ["monday", "tuesday", "wednesday", "thursday", "friday"]
    responsibility.icon_url = None
    responsibility.created_at = datetime.now()
    responsibility.updated_at = datetime.now()
    return responsibility


@pytest.fixture
def mock_completion():
    """A mock ResponsibilityCompletion object for unit tests."""
    completion = MagicMock()
    completion.id = 1
    completion.responsibility_id = 1
    completion.family_member_id = 2
    completion.completion_date = date.today()
    completion.created_at = datetime.now()
    return completion
