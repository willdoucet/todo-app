"""
Integration tests for iCloud Reminders API endpoints.

Tests hit real FastAPI endpoints with a real PostgreSQL database.
"""

import os
import pytest
import pytest_asyncio

from app.models import CalendarIntegration, IntegrationStatus, Calendar, List, Task
from app.utils.encryption import encrypt_password


@pytest_asyncio.fixture
async def test_integration(db_session, test_family_member):
    """Create a CalendarIntegration for reminders tests."""
    integration = CalendarIntegration(
        family_member_id=test_family_member.id,
        provider="icloud",
        email="test@icloud.com",
        encrypted_password=encrypt_password("fake-password"),
        status=IntegrationStatus.ACTIVE,
    )
    db_session.add(integration)
    await db_session.commit()
    await db_session.refresh(integration)
    return integration


# =============================================================================
# POST /integrations/icloud/validate-reminders
# =============================================================================


class TestValidateReminders:
    """Tests for POST /integrations/icloud/validate-reminders."""

    async def test_returns_400_with_invalid_credentials(self, client, test_integration):
        """Should return 400 since fake credentials can't connect to iCloud."""
        response = await client.post(
            "/integrations/icloud/validate-reminders",
            json={"integration_id": test_integration.id},
        )

        # Endpoint tries to connect to iCloud with fake creds — expect 400
        assert response.status_code == 400
        data = response.json()
        assert "Could not connect to iCloud" in data["detail"]

    async def test_returns_404_for_missing_integration(self, client):
        """Should return 404 when integration does not exist."""
        response = await client.post(
            "/integrations/icloud/validate-reminders",
            json={"integration_id": 99999},
        )

        assert response.status_code == 404

    async def test_rejects_invalid_payload(self, client):
        """Should return 422 for missing integration_id."""
        response = await client.post(
            "/integrations/icloud/validate-reminders",
            json={},
        )

        assert response.status_code == 422


# =============================================================================
# DELETE /integrations/{id}/reminders
# =============================================================================


class TestDisconnectReminders:
    """Tests for DELETE /integrations/{id}/reminders."""

    async def test_disconnect_clears_sync_metadata(
        self, client, db_session, test_integration, test_family_member
    ):
        """Should clear sync metadata on tasks and lists, delete reminder Calendar rows."""
        # Create a reminder Calendar row
        cal = Calendar(
            calendar_integration_id=test_integration.id,
            calendar_url="https://caldav.icloud.com/reminders/list-1",
            name="Shopping",
            is_todo=True,
        )
        db_session.add(cal)
        await db_session.flush()

        # Create a synced list
        synced_list = List(
            name="Shopping",
            external_id="https://caldav.icloud.com/reminders/list-1",
            calendar_integration_id=test_integration.id,
        )
        db_session.add(synced_list)
        await db_session.flush()

        # Create a synced task
        synced_task = Task(
            title="Buy milk",
            list_id=synced_list.id,
            assigned_to=test_family_member.id,
            external_id="icloud-todo-123",
            etag="etag-1",
            sync_status="SYNCED",
            calendar_integration_id=test_integration.id,
        )
        db_session.add(synced_task)
        await db_session.commit()
        await db_session.refresh(synced_task)

        # Act
        response = await client.delete(
            f"/integrations/{test_integration.id}/reminders"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "Reminders disconnected" in data["detail"]

        # Verify task sync metadata was cleared
        await db_session.refresh(synced_task)
        assert synced_task.external_id is None
        assert synced_task.etag is None
        assert synced_task.sync_status is None
        assert synced_task.calendar_integration_id is None

        # Verify list sync metadata was cleared
        await db_session.refresh(synced_list)
        assert synced_list.external_id is None
        assert synced_list.calendar_integration_id is None

    async def test_disconnect_returns_404_for_missing_integration(self, client):
        """Should return 404 when integration does not exist."""
        response = await client.delete("/integrations/99999/reminders")

        assert response.status_code == 404


# =============================================================================
# DELETE /lists/{id} — synced list deletion blocked
# =============================================================================


class TestSyncedListDeleteBlocked:
    """Synced lists cannot be deleted via the normal list delete endpoint."""

    async def test_cannot_delete_synced_list(
        self, client, db_session, test_integration
    ):
        """DELETE /lists/{id} should return 400 for a synced list."""
        synced_list = List(
            name="iCloud Reminders",
            calendar_integration_id=test_integration.id,
        )
        db_session.add(synced_list)
        await db_session.commit()
        await db_session.refresh(synced_list)

        response = await client.delete(f"/lists/{synced_list.id}")

        assert response.status_code == 400
        assert "Cannot delete a synced list" in response.json()["detail"]

    async def test_can_delete_local_list(self, client, db_session):
        """DELETE /lists/{id} should succeed for a normal (non-synced) list."""
        local_list = List(name="Local List", color="#FF0000")
        db_session.add(local_list)
        await db_session.commit()
        await db_session.refresh(local_list)

        response = await client.delete(f"/lists/{local_list.id}")

        assert response.status_code == 200
