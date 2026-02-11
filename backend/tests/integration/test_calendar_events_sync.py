"""Integration tests for ICLOUD event editing/deleting with sync_status.

Verifies that PATCH/DELETE on ICLOUD events succeeds and sets sync_status
to PENDING_PUSH (Celery push tasks are mocked).
"""

import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock
from datetime import date

from app.models import FamilyMember, CalendarIntegration, CalendarEvent
from app.utils.encryption import encrypt_password


@pytest_asyncio.fixture
async def member(db_session):
    m = FamilyMember(name="Bob", is_system=False)
    db_session.add(m)
    await db_session.commit()
    await db_session.refresh(m)
    return m


@pytest_asyncio.fixture
async def integration(db_session, member):
    integ = CalendarIntegration(
        family_member_id=member.id,
        provider="icloud",
        email="bob@icloud.com",
        encrypted_password=encrypt_password("test"),
        status="ACTIVE",
        selected_calendars=["https://caldav.icloud.com/cal1"],
    )
    db_session.add(integ)
    await db_session.commit()
    await db_session.refresh(integ)
    return integ


@pytest_asyncio.fixture
async def icloud_event(db_session, member, integration):
    event = CalendarEvent(
        title="iCloud Meeting",
        date=date(2026, 3, 10),
        start_time="09:00",
        end_time="10:00",
        source="ICLOUD",
        external_id="uid-abc",
        assigned_to=member.id,
        calendar_integration_id=integration.id,
        sync_status="SYNCED",
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    return event


class TestPatchICloudEvent:
    """PATCH /calendar-events/{id} on ICLOUD events."""

    @patch("app.tasks.push_event_to_icloud")
    async def test_updates_icloud_event(self, mock_task, client, icloud_event):
        mock_task.apply_async = MagicMock()

        response = await client.patch(
            f"/calendar-events/{icloud_event.id}",
            json={"title": "Updated Meeting"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Meeting"
        assert data["sync_status"] == "PENDING_PUSH"

    @patch("app.tasks.push_event_to_icloud")
    async def test_dispatches_push_task(self, mock_task, client, icloud_event):
        mock_task.apply_async = MagicMock()

        await client.patch(
            f"/calendar-events/{icloud_event.id}",
            json={"title": "Changed"},
        )

        mock_task.apply_async.assert_called_once()
        call_args = mock_task.apply_async.call_args
        assert call_args.kwargs.get("args") == [icloud_event.id] or call_args[1].get("args") == [icloud_event.id]


class TestDeleteICloudEvent:
    """DELETE /calendar-events/{id} on ICLOUD events."""

    @patch("app.tasks.push_delete_to_icloud")
    async def test_deletes_icloud_event(self, mock_task, client, icloud_event):
        mock_task.apply_async = MagicMock()

        response = await client.delete(f"/calendar-events/{icloud_event.id}")

        assert response.status_code == 200
        assert response.json()["id"] == icloud_event.id

        # Verify actually deleted
        get_response = await client.get(f"/calendar-events/{icloud_event.id}")
        assert get_response.status_code == 404

    @patch("app.tasks.push_delete_to_icloud")
    async def test_dispatches_delete_push_task(self, mock_task, client, icloud_event):
        mock_task.apply_async = MagicMock()

        await client.delete(f"/calendar-events/{icloud_event.id}")

        mock_task.apply_async.assert_called_once()
        call_args = mock_task.apply_async.call_args
        args = call_args.kwargs.get("args") or call_args[1].get("args")
        assert args[0] == "uid-abc"  # external_id
        assert args[1] == icloud_event.calendar_integration_id
