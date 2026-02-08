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
        "color": "#3B82F6",
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
    member.color = "#3B82F6"
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
    member.color = "#D97452"
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


# =============================================================================
# Mealboard Sample Data Fixtures
# =============================================================================


@pytest.fixture
def sample_recipe_data():
    """Sample data for creating a recipe."""
    return {
        "name": "Honey Garlic Chicken",
        "description": "Quick and easy dinner",
        "ingredients": [
            {"name": "Chicken breast", "quantity": 2, "unit": "lb", "category": "Protein"},
            {"name": "Honey", "quantity": 0.25, "unit": "cups", "category": "Pantry"},
        ],
        "instructions": "1. Season chicken. 2. Cook in pan. 3. Add sauce.",
        "prep_time_minutes": 10,
        "cook_time_minutes": 25,
        "servings": 4,
        "is_favorite": True,
        "tags": ["chicken", "quick", "dinner"],
    }


@pytest.fixture
def sample_meal_plan_data():
    """Sample data for creating a meal plan."""
    return {
        "date": date.today().isoformat(),
        "category": "DINNER",
        "recipe_id": None,
        "custom_meal_name": None,
        "was_cooked": False,
        "notes": None,
    }


@pytest.fixture
def mock_recipe():
    """A mock Recipe object for unit tests."""
    recipe = MagicMock()
    recipe.id = 1
    recipe.name = "Test Recipe"
    recipe.description = "A test recipe"
    recipe.ingredients = [{"name": "Test", "quantity": 1, "unit": "cups", "category": "Pantry"}]
    recipe.instructions = "Test instructions"
    recipe.prep_time_minutes = 10
    recipe.cook_time_minutes = 20
    recipe.servings = 4
    recipe.image_url = None
    recipe.is_favorite = False
    recipe.tags = ["test"]
    recipe.created_at = datetime.now()
    recipe.updated_at = None
    return recipe


@pytest.fixture
def mock_meal_plan(mock_recipe):
    """A mock MealPlan object for unit tests."""
    meal_plan = MagicMock()
    meal_plan.id = 1
    meal_plan.date = date.today()
    meal_plan.category = "DINNER"
    meal_plan.recipe_id = 1
    meal_plan.recipe = mock_recipe
    meal_plan.custom_meal_name = None
    meal_plan.was_cooked = False
    meal_plan.notes = None
    meal_plan.created_at = datetime.now()
    meal_plan.updated_at = None
    return meal_plan
