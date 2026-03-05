"""Unit tests for sync engine helper functions.

Tests _update_local_from_remote, _resolve_conflict logic using plain objects.
The full pull/push functions are tested via integration tests.
"""

import pytest
from datetime import datetime, date
from unittest.mock import MagicMock

from app.services.sync_engine import (
    _update_local_from_remote,
    _resolve_conflict,
    SYNCED,
    PENDING_PUSH,
)


class FakeEvent:
    """Minimal stand-in for CalendarEvent ORM object."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestUpdateLocalFromRemote:
    """Tests for _update_local_from_remote helper."""

    def test_updates_remote_fields(self):
        local = FakeEvent(
            title="Old Title",
            description="Old desc",
            date=date(2026, 1, 1),
            start_time="09:00",
            end_time="10:00",
            all_day=False,
            timezone="America/New_York",
            etag="old-etag",
            last_modified_remote=None,
            sync_status=PENDING_PUSH,
            assigned_to=42,
            calendar_integration_id=7,
        )
        remote = {
            "title": "New Title",
            "description": "New desc",
            "date": date(2026, 1, 2),
            "start_time": "14:00",
            "end_time": "15:00",
            "all_day": False,
            "timezone": "America/Los_Angeles",
            "etag": "new-etag",
            "last_modified_remote": datetime(2026, 1, 2, 12, 0),
        }

        _update_local_from_remote(local, remote)

        assert local.title == "New Title"
        assert local.description == "New desc"
        assert local.date == date(2026, 1, 2)
        assert local.start_time == "14:00"
        assert local.end_time == "15:00"
        assert local.timezone == "America/Los_Angeles"
        assert local.etag == "new-etag"
        assert local.sync_status == SYNCED

    def test_preserves_local_only_fields(self):
        """assigned_to and calendar_integration_id must NOT be overwritten."""
        local = FakeEvent(
            title="X", description=None, date=date(2026, 1, 1),
            start_time=None, end_time=None, all_day=True,
            timezone=None,
            etag=None, last_modified_remote=None, sync_status=SYNCED,
            assigned_to=99,
            calendar_integration_id=5,
        )
        remote = {
            "title": "Y", "description": None,
            "date": date(2026, 1, 1),
            "start_time": None, "end_time": None, "all_day": True,
            "timezone": None,
        }

        _update_local_from_remote(local, remote)

        assert local.assigned_to == 99
        assert local.calendar_integration_id == 5

    def test_updates_timezone_field(self):
        """timezone should be updated from remote data."""
        local = FakeEvent(
            title="X", description=None, date=date(2026, 1, 1),
            start_time="10:00", end_time="11:00", all_day=False,
            timezone="America/New_York",
            etag=None, last_modified_remote=None, sync_status=SYNCED,
            assigned_to=1, calendar_integration_id=1,
        )
        remote = {
            "title": "X", "description": None,
            "date": date(2026, 1, 1),
            "start_time": "10:00", "end_time": "11:00", "all_day": False,
            "timezone": "America/Los_Angeles",
        }

        _update_local_from_remote(local, remote)

        assert local.timezone == "America/Los_Angeles"


class TestResolveConflict:
    """Tests for _resolve_conflict (last-write-wins)."""

    def test_remote_wins_when_newer(self):
        local = FakeEvent(
            title="Local Edit",
            description=None, date=date(2026, 1, 1),
            start_time=None, end_time=None, all_day=True,
            timezone=None,
            etag=None, last_modified_remote=None,
            sync_status=PENDING_PUSH,
            updated_at=datetime(2026, 1, 1, 10, 0),
            external_id="test-uid", assigned_to=1, calendar_integration_id=1,
        )
        remote = {
            "title": "Remote Edit",
            "description": None,
            "date": date(2026, 1, 1),
            "start_time": None, "end_time": None, "all_day": True,
            "timezone": None,
            "last_modified_remote": datetime(2026, 1, 1, 12, 0),  # Newer
        }
        stats = {"updated": 0, "skipped": 0}

        _resolve_conflict(local, remote, stats)

        assert local.title == "Remote Edit"
        assert local.sync_status == SYNCED
        assert stats["updated"] == 1
        assert stats["skipped"] == 0

    def test_local_wins_when_newer(self):
        local = FakeEvent(
            title="Local Edit",
            description=None, date=date(2026, 1, 1),
            start_time=None, end_time=None, all_day=True,
            timezone=None,
            etag=None, last_modified_remote=None,
            sync_status=PENDING_PUSH,
            updated_at=datetime(2026, 1, 1, 14, 0),  # Newer
            external_id="test-uid", assigned_to=1, calendar_integration_id=1,
        )
        remote = {
            "title": "Remote Edit",
            "description": None,
            "date": date(2026, 1, 1),
            "start_time": None, "end_time": None, "all_day": True,
            "timezone": None,
            "last_modified_remote": datetime(2026, 1, 1, 10, 0),
        }
        stats = {"updated": 0, "skipped": 0}

        _resolve_conflict(local, remote, stats)

        assert local.title == "Local Edit"  # NOT overwritten
        assert stats["skipped"] == 1
        assert stats["updated"] == 0

    def test_remote_wins_when_no_timestamps(self):
        """When timestamps are missing, remote wins as safe default."""
        local = FakeEvent(
            title="Local",
            description=None, date=date(2026, 1, 1),
            start_time=None, end_time=None, all_day=True,
            timezone=None,
            etag=None, last_modified_remote=None,
            sync_status=PENDING_PUSH,
            updated_at=None,
            external_id="test-uid", assigned_to=1, calendar_integration_id=1,
        )
        remote = {
            "title": "Remote",
            "description": None,
            "date": date(2026, 1, 1),
            "start_time": None, "end_time": None, "all_day": True,
            "timezone": None,
            "last_modified_remote": None,
        }
        stats = {"updated": 0, "skipped": 0}

        _resolve_conflict(local, remote, stats)

        assert local.title == "Remote"
        assert stats["updated"] == 1
