"""Integration tests for the /integrations API endpoints.

CalDAV calls and Celery tasks are mocked — these test the HTTP layer,
database operations, and request/response schemas.
"""

import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock

from app.models import FamilyMember, CalendarIntegration, CalendarEvent
from app.utils.encryption import encrypt_password


# =============================================================================
# Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def family_member(db_session):
    member = FamilyMember(name="Alice", is_system=False)
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(member)
    return member


@pytest_asyncio.fixture
async def integration(db_session, family_member):
    """Create a connected integration."""
    integ = CalendarIntegration(
        family_member_id=family_member.id,
        provider="icloud",
        email="alice@icloud.com",
        encrypted_password=encrypt_password("test-pass"),
        status="ACTIVE",
        selected_calendars=["https://caldav.icloud.com/cal1"],
    )
    db_session.add(integ)
    await db_session.commit()
    await db_session.refresh(integ)
    return integ


@pytest_asyncio.fixture
async def synced_event(db_session, family_member, integration):
    """Create a calendar event belonging to the integration."""
    from datetime import date

    event = CalendarEvent(
        title="Synced Event",
        date=date(2026, 3, 1),
        start_time="10:00",
        end_time="11:00",
        source="ICLOUD",
        external_id="uid-123",
        assigned_to=family_member.id,
        calendar_integration_id=integration.id,
        sync_status="SYNCED",
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    return event


# =============================================================================
# POST /integrations/icloud/validate
# =============================================================================


class TestValidateICloud:
    """Tests for POST /integrations/icloud/validate."""

    @patch("app.routes.integrations.caldav_client")
    async def test_returns_calendar_list(self, mock_caldav, client, family_member):
        """Should validate credentials and return calendars."""
        mock_principal = MagicMock()
        mock_caldav.connect_icloud.return_value = (MagicMock(), mock_principal)
        mock_caldav.list_calendars.return_value = [
            {"url": "https://caldav.icloud.com/cal1", "name": "Personal", "color": "#FF0000"},
            {"url": "https://caldav.icloud.com/cal2", "name": "Work", "color": "#0000FF"},
        ]
        mock_cal = MagicMock()
        mock_caldav.get_calendar_by_url.return_value = mock_cal
        mock_caldav.fetch_events.return_value = [
            {"external_id": "uid-1", "title": "Event 1"},
            {"external_id": "uid-2", "title": "Event 2"},
        ]

        response = await client.post("/integrations/icloud/validate", json={
            "email": "alice@icloud.com",
            "password": "app-pass",
            "family_member_id": family_member.id,
        })

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "Personal"
        assert data[0]["color"] == "#FF0000"
        assert data[0]["event_count"] == 2
        assert data[1]["name"] == "Work"

    @patch("app.routes.integrations.caldav_client")
    async def test_bad_credentials_returns_400(self, mock_caldav, client, family_member):
        """Should return 400 when CalDAV connection fails."""
        mock_caldav.connect_icloud.side_effect = Exception("Auth failed")

        response = await client.post("/integrations/icloud/validate", json={
            "email": "bad@icloud.com",
            "password": "wrong",
            "family_member_id": family_member.id,
        })

        assert response.status_code == 400
        assert "Could not connect" in response.json()["detail"]


# =============================================================================
# POST /integrations/icloud/connect
# =============================================================================


class TestConnectICloud:
    """Tests for POST /integrations/icloud/connect."""

    @patch("app.tasks.sync_single_integration")
    @patch("app.routes.integrations.caldav_client")
    async def test_creates_integration(self, mock_caldav, mock_task, client, family_member):
        """Should create integration and dispatch sync task."""
        mock_caldav.connect_icloud.return_value = (MagicMock(), MagicMock())
        mock_task.delay = MagicMock()

        response = await client.post("/integrations/icloud/connect", json={
            "email": "alice@icloud.com",
            "password": "app-pass",
            "family_member_id": family_member.id,
            "selected_calendars": ["https://caldav.icloud.com/cal1"],
        })

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "alice@icloud.com"
        assert data["status"] == "SYNCING"
        assert data["family_member_id"] == family_member.id
        assert "password" not in data  # Never returned
        assert "encrypted_password" not in data

        # Verify task was dispatched
        mock_task.delay.assert_called_once()

    @patch("app.routes.integrations.caldav_client")
    async def test_connect_bad_credentials_returns_400(self, mock_caldav, client, family_member):
        """Should return 400 when CalDAV validation fails."""
        mock_caldav.connect_icloud.side_effect = Exception("Auth failed")

        response = await client.post("/integrations/icloud/connect", json={
            "email": "bad@icloud.com",
            "password": "wrong",
            "family_member_id": family_member.id,
        })

        assert response.status_code == 400


# =============================================================================
# GET /integrations/
# =============================================================================


class TestListIntegrations:
    """Tests for GET /integrations/."""

    async def test_returns_empty_list(self, client):
        assert (await client.get("/integrations/")).json() == []

    async def test_returns_connected_integrations(self, client, integration):
        response = await client.get("/integrations/")
        data = response.json()
        assert len(data) == 1
        assert data[0]["email"] == "alice@icloud.com"
        assert data[0]["status"] == "ACTIVE"

    async def test_filters_by_family_member(self, client, integration, family_member):
        response = await client.get(f"/integrations/?family_member_id={family_member.id}")
        assert len(response.json()) == 1

        response = await client.get("/integrations/?family_member_id=99999")
        assert len(response.json()) == 0


# =============================================================================
# GET /integrations/{id}
# =============================================================================


class TestGetIntegration:
    async def test_returns_integration(self, client, integration):
        response = await client.get(f"/integrations/{integration.id}")
        assert response.status_code == 200
        assert response.json()["email"] == "alice@icloud.com"

    async def test_returns_404(self, client):
        response = await client.get("/integrations/99999")
        assert response.status_code == 404


# =============================================================================
# POST /integrations/{id}/sync
# =============================================================================


class TestTriggerSync:
    @patch("app.tasks.sync_single_integration")
    async def test_triggers_sync_task(self, mock_task, client, integration):
        mock_task.delay = MagicMock()

        response = await client.post(f"/integrations/{integration.id}/sync")

        assert response.status_code == 200
        assert response.json()["status"] == "SYNCING"
        mock_task.delay.assert_called_once_with(integration.id)

    async def test_returns_404(self, client):
        response = await client.post("/integrations/99999/sync")
        assert response.status_code == 404


# =============================================================================
# DELETE /integrations/{id}
# =============================================================================


class TestDisconnectIntegration:
    async def test_deletes_integration_and_events(self, client, integration, synced_event):
        response = await client.delete(f"/integrations/{integration.id}")

        assert response.status_code == 200
        assert response.json()["email"] == "alice@icloud.com"

        # Verify integration is gone
        response = await client.get(f"/integrations/{integration.id}")
        assert response.status_code == 404

        # Verify synced event is also gone
        response = await client.get(f"/calendar-events/{synced_event.id}")
        assert response.status_code == 404

    async def test_returns_404(self, client):
        response = await client.delete("/integrations/99999")
        assert response.status_code == 404
