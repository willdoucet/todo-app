"""
Unit tests for Pydantic schemas.

These tests verify that our schemas correctly validate input data,
rejecting invalid inputs and accepting valid ones.

Schema validation is our first line of defense against bad data -
it happens before any database operations.
"""

import pytest
from pydantic import ValidationError
from datetime import datetime, date

from app.schemas import (
    FamilyMemberCreate,
    FamilyMemberUpdate,
    TaskCreate,
    TaskUpdate,
    ResponsibilityCreate,
    ResponsibilityUpdate,
    ResponsibilityCategory,
    ListCreate,
    ListUpdate,
    ResponsibilityCompletionCreate,
)


# =============================================================================
# FamilyMemberCreate Tests
# =============================================================================

class TestFamilyMemberCreate:
    """Tests for FamilyMemberCreate schema validation."""

    def test_valid_family_member(self):
        """Should accept valid family member data."""
        member = FamilyMemberCreate(name="Alice")
        assert member.name == "Alice"
        assert member.photo_url is None

    def test_valid_with_photo_url(self):
        """Should accept family member with photo URL."""
        member = FamilyMemberCreate(name="Bob", photo_url="/uploads/bob.jpg")
        assert member.name == "Bob"
        assert member.photo_url == "/uploads/bob.jpg"

    def test_rejects_empty_name(self):
        """Should reject empty name (min_length=1)."""
        with pytest.raises(ValidationError) as exc_info:
            FamilyMemberCreate(name="")

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("name",)
        assert "String should have at least 1 character" in errors[0]["msg"]

    def test_rejects_name_too_long(self):
        """Should reject name over 50 characters."""
        long_name = "A" * 51
        with pytest.raises(ValidationError) as exc_info:
            FamilyMemberCreate(name=long_name)

        errors = exc_info.value.errors()
        assert errors[0]["loc"] == ("name",)
        assert "String should have at most 50 characters" in errors[0]["msg"]

    def test_rejects_missing_name(self):
        """Should reject when name is not provided."""
        with pytest.raises(ValidationError) as exc_info:
            FamilyMemberCreate()

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_accepts_max_length_name(self):
        """Should accept name at exactly 50 characters."""
        name = "A" * 50
        member = FamilyMemberCreate(name=name)
        assert len(member.name) == 50


# =============================================================================
# TaskCreate Tests
# =============================================================================

class TestTaskCreate:
    """Tests for TaskCreate schema validation."""

    @pytest.fixture
    def valid_task_data(self):
        """Minimal valid task data."""
        return {
            "title": "Buy groceries",
            "assigned_to": 1,
            "list_id": 1,
        }

    def test_valid_minimal_task(self, valid_task_data):
        """Should accept minimal valid task data."""
        task = TaskCreate(**valid_task_data)
        assert task.title == "Buy groceries"
        assert task.assigned_to == 1
        assert task.list_id == 1
        assert task.completed is False  # default
        assert task.important is False  # default
        assert task.description is None
        assert task.due_date is None

    def test_valid_full_task(self, valid_task_data):
        """Should accept task with all fields."""
        task = TaskCreate(
            **valid_task_data,
            description="Milk, eggs, bread",
            due_date=datetime(2024, 12, 25, 10, 0),
            completed=True,
            important=True,
        )
        assert task.description == "Milk, eggs, bread"
        assert task.completed is True
        assert task.important is True

    def test_rejects_empty_title(self, valid_task_data):
        """Should reject empty title."""
        valid_task_data["title"] = ""
        with pytest.raises(ValidationError) as exc_info:
            TaskCreate(**valid_task_data)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("title",) for e in errors)

    def test_rejects_title_too_long(self, valid_task_data):
        """Should reject title over 100 characters."""
        valid_task_data["title"] = "A" * 101
        with pytest.raises(ValidationError) as exc_info:
            TaskCreate(**valid_task_data)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("title",) for e in errors)

    def test_rejects_empty_description(self, valid_task_data):
        """Should reject empty description (if provided, must be at least 1 char)."""
        valid_task_data["description"] = ""
        with pytest.raises(ValidationError) as exc_info:
            TaskCreate(**valid_task_data)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("description",) for e in errors)

    def test_rejects_description_too_long(self, valid_task_data):
        """Should reject description over 500 characters."""
        valid_task_data["description"] = "A" * 501
        with pytest.raises(ValidationError) as exc_info:
            TaskCreate(**valid_task_data)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("description",) for e in errors)

    def test_rejects_assigned_to_zero(self, valid_task_data):
        """Should reject assigned_to = 0 (must be >= 1)."""
        valid_task_data["assigned_to"] = 0
        with pytest.raises(ValidationError) as exc_info:
            TaskCreate(**valid_task_data)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("assigned_to",) for e in errors)

    def test_rejects_assigned_to_negative(self, valid_task_data):
        """Should reject negative assigned_to."""
        valid_task_data["assigned_to"] = -1
        with pytest.raises(ValidationError) as exc_info:
            TaskCreate(**valid_task_data)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("assigned_to",) for e in errors)

    def test_rejects_assigned_to_too_large(self, valid_task_data):
        """Should reject assigned_to over 1,000,000."""
        valid_task_data["assigned_to"] = 1000001
        with pytest.raises(ValidationError) as exc_info:
            TaskCreate(**valid_task_data)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("assigned_to",) for e in errors)

    def test_rejects_list_id_zero(self, valid_task_data):
        """Should reject list_id = 0 (must be >= 1)."""
        valid_task_data["list_id"] = 0
        with pytest.raises(ValidationError) as exc_info:
            TaskCreate(**valid_task_data)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("list_id",) for e in errors)

    def test_rejects_missing_required_fields(self):
        """Should reject when required fields are missing."""
        with pytest.raises(ValidationError) as exc_info:
            TaskCreate(title="Test")  # missing assigned_to and list_id

        errors = exc_info.value.errors()
        error_locs = [e["loc"] for e in errors]
        assert ("assigned_to",) in error_locs
        assert ("list_id",) in error_locs


# =============================================================================
# ResponsibilityCreate Tests
# =============================================================================

class TestResponsibilityCreate:
    """Tests for ResponsibilityCreate schema validation."""

    @pytest.fixture
    def valid_responsibility_data(self):
        """Minimal valid responsibility data."""
        return {
            "title": "Make bed",
            "categories": ["MORNING"],
            "assigned_to": 1,
            "frequency": ["monday", "tuesday"],
        }

    def test_valid_responsibility(self, valid_responsibility_data):
        """Should accept valid responsibility data."""
        resp = ResponsibilityCreate(**valid_responsibility_data)
        assert resp.title == "Make bed"
        assert resp.categories == [ResponsibilityCategory.MORNING]
        assert resp.assigned_to == 1
        assert resp.frequency == ["monday", "tuesday"]

    def test_valid_all_categories(self, valid_responsibility_data):
        """Should accept all valid category values."""
        for category in ["MORNING", "AFTERNOON", "EVENING", "CHORE"]:
            valid_responsibility_data["categories"] = [category]
            resp = ResponsibilityCreate(**valid_responsibility_data)
            assert resp.categories[0].value == category

    def test_valid_multiple_categories(self, valid_responsibility_data):
        """Should accept multiple categories."""
        valid_responsibility_data["categories"] = ["MORNING", "EVENING"]
        resp = ResponsibilityCreate(**valid_responsibility_data)
        assert len(resp.categories) == 2

    def test_rejects_invalid_category(self, valid_responsibility_data):
        """Should reject invalid category value."""
        valid_responsibility_data["categories"] = ["INVALID"]
        with pytest.raises(ValidationError) as exc_info:
            ResponsibilityCreate(**valid_responsibility_data)

        errors = exc_info.value.errors()
        assert any("categories" in str(e["loc"]) for e in errors)

    def test_rejects_empty_frequency(self, valid_responsibility_data):
        """Should reject empty frequency list (min_length=1)."""
        valid_responsibility_data["frequency"] = []
        with pytest.raises(ValidationError) as exc_info:
            ResponsibilityCreate(**valid_responsibility_data)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("frequency",) for e in errors)

    def test_rejects_missing_frequency(self, valid_responsibility_data):
        """Should reject when frequency is not provided."""
        del valid_responsibility_data["frequency"]
        with pytest.raises(ValidationError) as exc_info:
            ResponsibilityCreate(**valid_responsibility_data)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("frequency",) for e in errors)

    def test_rejects_empty_title(self, valid_responsibility_data):
        """Should reject empty title."""
        valid_responsibility_data["title"] = ""
        with pytest.raises(ValidationError) as exc_info:
            ResponsibilityCreate(**valid_responsibility_data)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("title",) for e in errors)

    def test_rejects_assigned_to_zero(self, valid_responsibility_data):
        """Should reject assigned_to = 0."""
        valid_responsibility_data["assigned_to"] = 0
        with pytest.raises(ValidationError) as exc_info:
            ResponsibilityCreate(**valid_responsibility_data)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("assigned_to",) for e in errors)


# =============================================================================
# ListCreate Tests
# =============================================================================

class TestListCreate:
    """Tests for ListCreate schema validation."""

    def test_valid_minimal_list(self):
        """Should accept list with just name."""
        list_obj = ListCreate(name="Personal")
        assert list_obj.name == "Personal"
        assert list_obj.color is None
        assert list_obj.icon is None

    def test_valid_full_list(self):
        """Should accept list with all fields."""
        list_obj = ListCreate(name="Work", color="#3B82F6", icon="briefcase")
        assert list_obj.name == "Work"
        assert list_obj.color == "#3B82F6"
        assert list_obj.icon == "briefcase"

    def test_rejects_empty_name(self):
        """Should reject empty name."""
        with pytest.raises(ValidationError) as exc_info:
            ListCreate(name="")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_rejects_name_too_long(self):
        """Should reject name over 100 characters."""
        with pytest.raises(ValidationError) as exc_info:
            ListCreate(name="A" * 101)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_rejects_empty_color(self):
        """Should reject empty color (if provided, must be at least 1 char)."""
        with pytest.raises(ValidationError) as exc_info:
            ListCreate(name="Test", color="")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("color",) for e in errors)

    def test_rejects_color_too_long(self):
        """Should reject color over 7 characters (hex format is #RRGGBB = 7 chars)."""
        with pytest.raises(ValidationError) as exc_info:
            ListCreate(name="Test", color="#RRGGBBAA")  # 9 chars

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("color",) for e in errors)

    def test_accepts_valid_hex_colors(self):
        """Should accept valid hex color formats."""
        # Full hex
        list1 = ListCreate(name="Test", color="#FF0000")
        assert list1.color == "#FF0000"

        # Short hex
        list2 = ListCreate(name="Test", color="#F00")
        assert list2.color == "#F00"


# =============================================================================
# Update Schema Tests (partial updates)
# =============================================================================

class TestUpdateSchemas:
    """Tests for Update schemas - these allow partial updates."""

    def test_task_update_all_fields_optional(self):
        """TaskUpdate should allow empty update (no fields)."""
        update = TaskUpdate()
        assert update.title is None
        assert update.description is None
        assert update.completed is None

    def test_task_update_single_field(self):
        """TaskUpdate should allow updating just one field."""
        update = TaskUpdate(completed=True)
        assert update.completed is True
        assert update.title is None  # other fields unchanged

    def test_family_member_update_validates_name_length(self):
        """FamilyMemberUpdate should still validate name length."""
        with pytest.raises(ValidationError):
            FamilyMemberUpdate(name="")  # empty not allowed

        with pytest.raises(ValidationError):
            FamilyMemberUpdate(name="A" * 51)  # too long

    def test_responsibility_update_validates_categories(self):
        """ResponsibilityUpdate should validate categories if provided."""
        # Valid categories
        update = ResponsibilityUpdate(categories=[ResponsibilityCategory.EVENING])
        assert update.categories == [ResponsibilityCategory.EVENING]

        # Multiple valid categories
        update2 = ResponsibilityUpdate(categories=[ResponsibilityCategory.MORNING, ResponsibilityCategory.EVENING])
        assert len(update2.categories) == 2

        # Invalid category
        with pytest.raises(ValidationError):
            ResponsibilityUpdate(categories=["INVALID"])


# =============================================================================
# ResponsibilityCompletionCreate Tests
# =============================================================================

class TestResponsibilityCompletionCreate:
    """Tests for ResponsibilityCompletionCreate schema."""

    def test_valid_completion(self):
        """Should accept valid completion date."""
        completion = ResponsibilityCompletionCreate(completion_date=date(2024, 6, 15))
        assert completion.completion_date == date(2024, 6, 15)

    def test_rejects_missing_date(self):
        """Should reject when completion_date is missing."""
        with pytest.raises(ValidationError) as exc_info:
            ResponsibilityCompletionCreate()

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("completion_date",) for e in errors)

    def test_accepts_date_string(self):
        """Should parse date string in ISO format."""
        completion = ResponsibilityCompletionCreate(completion_date="2024-12-25")
        assert completion.completion_date == date(2024, 12, 25)
