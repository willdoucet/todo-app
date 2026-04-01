"""Unit tests for CalDAV VTODO ↔ Task mapping.

Tests vtodo_to_task_data and task_data_to_vtodo without connecting to any CalDAV server.
"""

import pytest
from datetime import date, datetime, timezone

import icalendar

from app.services.caldav_client import (
    vtodo_to_task_data,
    task_data_to_vtodo,
)


# =============================================================================
# vtodo_to_task_data tests
# =============================================================================


class TestVtodoToTaskData:
    """Tests for converting VTODO → dict."""

    def _make_vtodo(self, **kwargs):
        """Helper: build a VTODO component with given properties."""
        vtodo = icalendar.Todo()
        for key, val in kwargs.items():
            vtodo.add(key, val)
        return vtodo

    def test_valid_vtodo(self):
        """Complete VTODO should parse all fields correctly."""
        vtodo = self._make_vtodo(
            uid="todo-123",
            summary="Buy groceries",
            description="Milk, eggs, bread",
            due=datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc),
            priority=1,
            status="NEEDS-ACTION",
        )
        result = vtodo_to_task_data(vtodo)

        assert result["external_id"] == "todo-123"
        assert result["title"] == "Buy groceries"
        assert result["description"] == "Milk, eggs, bread"
        assert result["due_date"] == datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc)
        assert result["priority"] == 1
        assert result["completed"] is False
        assert result["completed_at"] is None
        assert result["parent_external_id"] is None

    def test_missing_uid_returns_none(self):
        """VTODO without UID should be skipped."""
        vtodo = self._make_vtodo(summary="No UID")
        assert vtodo_to_task_data(vtodo) is None

    def test_missing_summary_returns_none(self):
        """VTODO without SUMMARY should be skipped."""
        vtodo = self._make_vtodo(uid="no-summary")
        assert vtodo_to_task_data(vtodo) is None

    def test_no_due_date(self):
        """VTODO without DUE should produce due_date=None."""
        vtodo = self._make_vtodo(
            uid="no-due",
            summary="No deadline",
        )
        result = vtodo_to_task_data(vtodo)
        assert result is not None
        assert result["due_date"] is None

    def test_date_only_due(self):
        """VTODO with date-only DUE (not datetime) should parse."""
        vtodo = self._make_vtodo(
            uid="date-due",
            summary="Date only",
            due=date(2026, 6, 15),
        )
        result = vtodo_to_task_data(vtodo)
        assert result["due_date"] == datetime(2026, 6, 15, 0, 0)

    def test_related_to_parsing(self):
        """RELATED-TO should map to parent_external_id."""
        vtodo = self._make_vtodo(
            uid="child-1",
            summary="Subtask",
        )
        vtodo.add("related-to", "parent-uid-abc")
        result = vtodo_to_task_data(vtodo)
        assert result["parent_external_id"] == "parent-uid-abc"

    def test_completed_status(self):
        """STATUS=COMPLETED should set completed=True."""
        vtodo = self._make_vtodo(
            uid="done-1",
            summary="Finished task",
            status="COMPLETED",
        )
        result = vtodo_to_task_data(vtodo)
        assert result["completed"] is True

    def test_completed_at_timestamp(self):
        """COMPLETED property should map to completed_at."""
        vtodo = self._make_vtodo(
            uid="done-2",
            summary="Finished task",
            status="COMPLETED",
            completed=datetime(2026, 3, 10, 14, 30, tzinfo=timezone.utc),
        )
        result = vtodo_to_task_data(vtodo)
        assert result["completed"] is True
        assert result["completed_at"] is not None
        assert result["completed_at"].year == 2026

    def test_long_title_truncated(self):
        """Titles longer than 100 chars should be truncated."""
        vtodo = self._make_vtodo(
            uid="long-title",
            summary="X" * 200,
        )
        result = vtodo_to_task_data(vtodo)
        assert len(result["title"]) == 100

    def test_long_description_truncated(self):
        """Descriptions longer than 500 chars should be truncated."""
        vtodo = self._make_vtodo(
            uid="long-desc",
            summary="Test",
            description="Y" * 600,
        )
        result = vtodo_to_task_data(vtodo)
        assert len(result["description"]) == 500

    def test_last_modified_parsed(self):
        """LAST-MODIFIED should be parsed as naive UTC datetime."""
        vtodo = self._make_vtodo(
            uid="mod-test",
            summary="Modified Todo",
        )
        vtodo.add("last-modified", datetime(2026, 2, 28, 18, 30, tzinfo=timezone.utc))
        result = vtodo_to_task_data(vtodo)
        assert result["last_modified_remote"] is not None
        assert result["last_modified_remote"].tzinfo is None  # Stored as naive UTC


# =============================================================================
# Priority mapping tests
# =============================================================================


class TestPriorityMapping:
    """Tests for iCalendar → app priority mapping.

    iCalendar: 0=undefined, 1-4=high, 5=medium, 6-9=low
    App: 0=none, 1=high, 5=medium, 9=low
    """

    def _make_vtodo_with_priority(self, priority):
        vtodo = icalendar.Todo()
        vtodo.add("uid", f"prio-{priority}")
        vtodo.add("summary", f"Priority {priority}")
        vtodo.add("priority", priority)
        return vtodo

    def test_priority_0_maps_to_none(self):
        result = vtodo_to_task_data(self._make_vtodo_with_priority(0))
        assert result["priority"] == 0

    def test_priority_1_maps_to_high(self):
        result = vtodo_to_task_data(self._make_vtodo_with_priority(1))
        assert result["priority"] == 1

    def test_priority_2_maps_to_high(self):
        result = vtodo_to_task_data(self._make_vtodo_with_priority(2))
        assert result["priority"] == 1

    def test_priority_4_maps_to_high(self):
        result = vtodo_to_task_data(self._make_vtodo_with_priority(4))
        assert result["priority"] == 1

    def test_priority_5_maps_to_medium(self):
        result = vtodo_to_task_data(self._make_vtodo_with_priority(5))
        assert result["priority"] == 5

    def test_priority_6_maps_to_low(self):
        result = vtodo_to_task_data(self._make_vtodo_with_priority(6))
        assert result["priority"] == 9

    def test_priority_9_maps_to_low(self):
        result = vtodo_to_task_data(self._make_vtodo_with_priority(9))
        assert result["priority"] == 9


# =============================================================================
# task_data_to_vtodo tests
# =============================================================================


class TestTaskDataToVtodo:
    """Tests for converting dict → iCalendar VTODO."""

    def test_basic_todo(self):
        """Basic task data should produce correct VTODO."""
        data = {
            "title": "Buy milk",
            "description": "2% milk",
            "priority": 1,
            "completed": False,
            "external_id": "existing-uid",
        }
        cal = task_data_to_vtodo(data)
        ical_str = cal.to_ical().decode()

        assert "SUMMARY:Buy milk" in ical_str
        assert "DESCRIPTION:2% milk" in ical_str
        assert "UID:existing-uid" in ical_str
        assert "STATUS:NEEDS-ACTION" in ical_str

    def test_completed_todo(self):
        """Completed task should set STATUS:COMPLETED."""
        data = {
            "title": "Done task",
            "completed": True,
            "completed_at": datetime(2026, 3, 10, 14, 30, tzinfo=timezone.utc),
            "external_id": "done-uid",
        }
        cal = task_data_to_vtodo(data)
        ical_str = cal.to_ical().decode()

        assert "STATUS:COMPLETED" in ical_str

    def test_with_due_date(self):
        """Task with due date should include DUE property."""
        data = {
            "title": "Due task",
            "due_date": datetime(2026, 6, 15, 10, 0),
            "external_id": "due-uid",
        }
        cal = task_data_to_vtodo(data)
        parsed = icalendar.Calendar.from_ical(cal.to_ical())
        for comp in parsed.walk():
            if comp.name == "VTODO":
                assert comp.get("DUE") is not None

    def test_with_parent(self):
        """Task with parent should include RELATED-TO."""
        data = {
            "title": "Subtask",
            "parent_external_id": "parent-uid",
            "external_id": "child-uid",
        }
        cal = task_data_to_vtodo(data)
        ical_str = cal.to_ical().decode()
        assert "RELATED-TO:parent-uid" in ical_str

    def test_generates_uid_when_missing(self):
        """Should generate a @familyhub.app UID when external_id is absent."""
        data = {"title": "New Todo"}
        cal = task_data_to_vtodo(data)
        ical_str = cal.to_ical().decode()
        assert "@familyhub.app" in ical_str

    def test_priority_preserved(self):
        """Priority value should be passed through to VTODO."""
        data = {"title": "Priority task", "priority": 5, "external_id": "prio-uid"}
        cal = task_data_to_vtodo(data)
        parsed = icalendar.Calendar.from_ical(cal.to_ical())
        for comp in parsed.walk():
            if comp.name == "VTODO":
                assert int(comp.get("PRIORITY")) == 5


# =============================================================================
# Round-trip test
# =============================================================================


class TestVtodoRoundTrip:
    """Test that task_data_to_vtodo → vtodo_to_task_data preserves data."""

    def test_round_trip_fidelity(self):
        original = {
            "title": "Round Trip",
            "description": "Test desc",
            "due_date": datetime(2026, 6, 15, 10, 0),
            "priority": 5,
            "completed": False,
            "external_id": "rt-uid-1",
        }
        cal = task_data_to_vtodo(original)

        parsed = icalendar.Calendar.from_ical(cal.to_ical())
        for comp in parsed.walk():
            if comp.name == "VTODO":
                result = vtodo_to_task_data(comp)
                assert result["title"] == "Round Trip"
                assert result["description"] == "Test desc"
                assert result["priority"] == 5
                assert result["completed"] is False
                assert result["external_id"] == "rt-uid-1"

    def test_completed_round_trip(self):
        original = {
            "title": "Completed RT",
            "completed": True,
            "completed_at": datetime(2026, 3, 10, 14, 30, tzinfo=timezone.utc),
            "priority": 1,
            "external_id": "rt-done-uid",
        }
        cal = task_data_to_vtodo(original)

        parsed = icalendar.Calendar.from_ical(cal.to_ical())
        for comp in parsed.walk():
            if comp.name == "VTODO":
                result = vtodo_to_task_data(comp)
                assert result["completed"] is True
                assert result["completed_at"] is not None
                assert result["priority"] == 1
