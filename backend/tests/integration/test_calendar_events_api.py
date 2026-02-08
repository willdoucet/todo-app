"""
Integration tests for /calendar-events API endpoints.

Calendar events support:
- CRUD for manually created events
- Date range filtering
- Member assignment filtering
- Source-based edit/delete restrictions (only MANUAL events editable)
- Time validation (HH:MM format, end_time > start_time)
"""

import pytest


# =============================================================================
# GET /calendar-events/ - List calendar events
# =============================================================================

class TestGetCalendarEvents:
    """Tests for GET /calendar-events/ endpoint."""

    async def test_requires_date_range(self, client):
        """Should return 422 when date range params are missing."""
        response = await client.get("/calendar-events/")
        assert response.status_code == 422

    async def test_returns_events_in_date_range(self, client, test_calendar_event):
        """Should return events within the specified date range."""
        response = await client.get(
            "/calendar-events/",
            params={"start_date": "2026-02-01", "end_date": "2026-02-28"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Test Event"
        assert data[0]["date"] == "2026-02-10"
        assert data[0]["start_time"] == "09:00"
        assert data[0]["end_time"] == "10:00"

    async def test_excludes_events_outside_range(self, client, test_calendar_event):
        """Should not return events outside the date range."""
        response = await client.get(
            "/calendar-events/",
            params={"start_date": "2026-03-01", "end_date": "2026-03-31"},
        )

        assert response.status_code == 200
        assert response.json() == []

    async def test_filters_by_assigned_to(
        self, client, test_calendar_event, test_all_day_event
    ):
        """Should filter by assigned_to member when provided."""
        # test_calendar_event is assigned, test_all_day_event is not
        response = await client.get(
            "/calendar-events/",
            params={
                "start_date": "2026-02-01",
                "end_date": "2026-02-28",
                "assigned_to": test_calendar_event.assigned_to,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Test Event"

    async def test_includes_family_member_in_response(
        self, client, test_calendar_event
    ):
        """Should include nested family_member with color."""
        response = await client.get(
            "/calendar-events/",
            params={"start_date": "2026-02-01", "end_date": "2026-02-28"},
        )

        data = response.json()
        assert data[0]["family_member"] is not None
        assert data[0]["family_member"]["name"] == "Test User"
        assert data[0]["family_member"]["color"] == "#3B82F6"


# =============================================================================
# GET /calendar-events/{id} - Get single event
# =============================================================================

class TestGetCalendarEvent:
    """Tests for GET /calendar-events/{id} endpoint."""

    async def test_returns_event_when_found(self, client, test_calendar_event):
        """Should return the calendar event."""
        response = await client.get(
            f"/calendar-events/{test_calendar_event.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_calendar_event.id
        assert data["title"] == "Test Event"

    async def test_returns_404_when_not_found(self, client):
        """Should return 404 when event doesn't exist."""
        response = await client.get("/calendar-events/99999")
        assert response.status_code == 404


# =============================================================================
# POST /calendar-events/ - Create event
# =============================================================================

class TestCreateCalendarEvent:
    """Tests for POST /calendar-events/ endpoint."""

    async def test_creates_timed_event(self, client, test_family_member):
        """Should create a timed event and return 201."""
        new_event = {
            "title": "Meeting",
            "date": "2026-02-15",
            "start_time": "14:00",
            "end_time": "15:30",
            "assigned_to": test_family_member.id,
        }

        response = await client.post("/calendar-events/", json=new_event)

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Meeting"
        assert data["start_time"] == "14:00"
        assert data["end_time"] == "15:30"
        assert data["source"] == "MANUAL"
        assert data["family_member"]["name"] == "Test User"

    async def test_creates_all_day_event(self, client):
        """Should create an all-day event without times."""
        new_event = {
            "title": "Holiday",
            "date": "2026-02-20",
            "all_day": True,
        }

        response = await client.post("/calendar-events/", json=new_event)

        assert response.status_code == 201
        data = response.json()
        assert data["all_day"] is True
        assert data["start_time"] is None
        assert data["end_time"] is None

    async def test_rejects_invalid_time_format(self, client):
        """Should return 422 for invalid time format."""
        bad_event = {
            "title": "Bad",
            "date": "2026-02-15",
            "start_time": "9am",
        }

        response = await client.post("/calendar-events/", json=bad_event)
        assert response.status_code == 422

    async def test_rejects_end_before_start(self, client):
        """Should return 422 when end_time is before start_time."""
        bad_event = {
            "title": "Backwards",
            "date": "2026-02-15",
            "start_time": "14:00",
            "end_time": "10:00",
        }

        response = await client.post("/calendar-events/", json=bad_event)
        assert response.status_code == 422

    async def test_rejects_empty_title(self, client):
        """Should return 422 when title is empty."""
        bad_event = {"title": "", "date": "2026-02-15"}

        response = await client.post("/calendar-events/", json=bad_event)
        assert response.status_code == 422


# =============================================================================
# PATCH /calendar-events/{id} - Update event
# =============================================================================

class TestUpdateCalendarEvent:
    """Tests for PATCH /calendar-events/{id} endpoint."""

    async def test_updates_manual_event(self, client, test_calendar_event):
        """Should update a MANUAL event."""
        response = await client.patch(
            f"/calendar-events/{test_calendar_event.id}",
            json={"title": "Updated Title"},
        )

        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"

    async def test_rejects_update_of_synced_event(self, client, test_synced_event):
        """Should return 400 when trying to update a non-MANUAL event."""
        response = await client.patch(
            f"/calendar-events/{test_synced_event.id}",
            json={"title": "Hacked"},
        )

        assert response.status_code == 400
        assert "manually created" in response.json()["detail"]

    async def test_returns_404_when_not_found(self, client):
        """Should return 404 when event doesn't exist."""
        response = await client.patch(
            "/calendar-events/99999",
            json={"title": "Nope"},
        )
        assert response.status_code == 404


# =============================================================================
# DELETE /calendar-events/{id} - Delete event
# =============================================================================

class TestDeleteCalendarEvent:
    """Tests for DELETE /calendar-events/{id} endpoint."""

    async def test_deletes_manual_event(self, client, test_calendar_event):
        """Should delete a MANUAL event and return it."""
        event_id = test_calendar_event.id

        response = await client.delete(f"/calendar-events/{event_id}")

        assert response.status_code == 200
        assert response.json()["id"] == event_id

        # Verify actually deleted
        get_response = await client.get(f"/calendar-events/{event_id}")
        assert get_response.status_code == 404

    async def test_rejects_delete_of_synced_event(self, client, test_synced_event):
        """Should return 400 when trying to delete a non-MANUAL event."""
        response = await client.delete(
            f"/calendar-events/{test_synced_event.id}"
        )

        assert response.status_code == 400
        assert "manually created" in response.json()["detail"]

    async def test_returns_404_when_not_found(self, client):
        """Should return 404 when event doesn't exist."""
        response = await client.delete("/calendar-events/99999")
        assert response.status_code == 404
