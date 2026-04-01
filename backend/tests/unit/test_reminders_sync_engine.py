"""Unit tests for reminders sync engine helper functions.

Tests _update_local_task_from_remote, _resolve_conflict logic using plain objects.
Same pattern as test_sync_engine.py — direct function calls with fake objects.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock

from app.services.reminders_sync_engine import (
    _update_local_task_from_remote,
    _resolve_conflict,
)
from app.services.sync_base import SYNCED, PENDING_PUSH


class FakeTask:
    """Minimal stand-in for Task ORM object."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestUpdateLocalTaskFromRemote:
    """Tests for _update_local_task_from_remote helper."""

    def test_updates_all_remote_fields(self):
        local = FakeTask(
            title="Old Title",
            description="Old desc",
            due_date=datetime(2026, 1, 1, 10, 0),
            priority=0,
            completed=False,
            completed_at=None,
            etag="old-etag",
            last_modified_remote=None,
            sync_status=PENDING_PUSH,
        )
        remote = {
            "title": "New Title",
            "description": "New desc",
            "due_date": datetime(2026, 2, 1, 10, 0),
            "priority": 5,
            "completed": True,
            "completed_at": datetime(2026, 1, 15, 12, 0),
            "etag": "new-etag",
            "last_modified_remote": datetime(2026, 1, 20, 8, 0),
        }

        _update_local_task_from_remote(local, remote)

        assert local.title == "New Title"
        assert local.description == "New desc"
        assert local.due_date == datetime(2026, 2, 1, 10, 0)
        assert local.priority == 5
        assert local.completed is True
        assert local.completed_at == datetime(2026, 1, 15, 12, 0)
        assert local.etag == "new-etag"
        assert local.last_modified_remote == datetime(2026, 1, 20, 8, 0)
        assert local.sync_status == SYNCED

    def test_sets_defaults_for_missing_optional_fields(self):
        """When remote dict has no optional keys, defaults are applied."""
        local = FakeTask(
            title="X",
            description="Some desc",
            due_date=datetime(2026, 1, 1),
            priority=9,
            completed=True,
            completed_at=datetime(2026, 1, 1),
            etag="etag-1",
            last_modified_remote=datetime(2026, 1, 1),
            sync_status=PENDING_PUSH,
        )
        remote = {
            "title": "Minimal Remote",
            # no description, due_date, priority, completed, completed_at, etag, last_modified_remote
        }

        _update_local_task_from_remote(local, remote)

        assert local.title == "Minimal Remote"
        assert local.description is None
        assert local.due_date is None
        assert local.priority == 0
        assert local.completed is False
        assert local.completed_at is None
        assert local.etag is None
        assert local.last_modified_remote is None
        assert local.sync_status == SYNCED

    def test_preserves_local_only_fields(self):
        """Fields like assigned_to and calendar_integration_id must NOT be touched."""
        local = FakeTask(
            title="X",
            description=None,
            due_date=None,
            priority=0,
            completed=False,
            completed_at=None,
            etag=None,
            last_modified_remote=None,
            sync_status=SYNCED,
            assigned_to=42,
            calendar_integration_id=7,
            list_id=10,
        )
        remote = {"title": "Y"}

        _update_local_task_from_remote(local, remote)

        assert local.assigned_to == 42
        assert local.calendar_integration_id == 7
        assert local.list_id == 10


class TestResolveConflict:
    """Tests for _resolve_conflict (last-write-wins)."""

    def test_remote_wins_when_newer(self):
        local = FakeTask(
            title="Local Edit",
            description=None,
            due_date=None,
            priority=0,
            completed=False,
            completed_at=None,
            etag=None,
            last_modified_remote=None,
            sync_status=PENDING_PUSH,
            updated_at=datetime(2026, 1, 1, 10, 0),
        )
        remote = {
            "title": "Remote Edit",
            "last_modified_remote": datetime(2026, 1, 1, 12, 0),  # Newer
        }
        stats = {"updated": 0, "skipped": 0}

        _resolve_conflict(local, remote, stats)

        assert local.title == "Remote Edit"
        assert local.sync_status == SYNCED
        assert stats["updated"] == 1
        assert stats["skipped"] == 0

    def test_local_wins_when_newer(self):
        local = FakeTask(
            title="Local Edit",
            description=None,
            due_date=None,
            priority=0,
            completed=False,
            completed_at=None,
            etag=None,
            last_modified_remote=None,
            sync_status=PENDING_PUSH,
            updated_at=datetime(2026, 1, 1, 14, 0),  # Newer
        )
        remote = {
            "title": "Remote Edit",
            "last_modified_remote": datetime(2026, 1, 1, 10, 0),
        }
        stats = {"updated": 0, "skipped": 0}

        _resolve_conflict(local, remote, stats)

        assert local.title == "Local Edit"  # NOT overwritten
        assert stats["skipped"] == 1
        assert stats["updated"] == 0

    def test_remote_wins_when_no_timestamps(self):
        """When timestamps are missing, remote wins as safe default."""
        local = FakeTask(
            title="Local",
            description=None,
            due_date=None,
            priority=0,
            completed=False,
            completed_at=None,
            etag=None,
            last_modified_remote=None,
            sync_status=PENDING_PUSH,
            updated_at=None,
        )
        remote = {
            "title": "Remote",
            "last_modified_remote": None,
        }
        stats = {"updated": 0, "skipped": 0}

        _resolve_conflict(local, remote, stats)

        assert local.title == "Remote"
        assert stats["updated"] == 1


class TestPriorityMappingPreservation:
    """Priority values 0, 1, 5, 9 must be preserved through update."""

    @pytest.mark.parametrize("priority", [0, 1, 5, 9])
    def test_priority_preserved_through_update(self, priority):
        local = FakeTask(
            title="Task",
            description=None,
            due_date=None,
            priority=0,
            completed=False,
            completed_at=None,
            etag=None,
            last_modified_remote=None,
            sync_status=PENDING_PUSH,
        )
        remote = {
            "title": "Task",
            "priority": priority,
        }

        _update_local_task_from_remote(local, remote)

        assert local.priority == priority
