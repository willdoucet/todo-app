"""
Integration tests for /responsibilities API endpoints.

Responsibilities are recurring tasks with:
- Categories (list of MORNING, AFTERNOON, EVENING, CHORE)
- Frequency (list of days like ["monday", "tuesday"])
- Completion tracking per date, family member, and category
"""

import pytest
from datetime import date


# =============================================================================
# GET /responsibilities/ - List all responsibilities
# =============================================================================

class TestGetResponsibilities:
    """Tests for GET /responsibilities/ endpoint."""

    async def test_returns_empty_list_when_no_responsibilities_exist(self, client):
        """Should return empty array when database has no responsibilities."""
        response = await client.get("/responsibilities/")

        assert response.status_code == 200
        assert response.json() == []

    async def test_returns_all_responsibilities(self, client, test_responsibility):
        """Should return all responsibilities with nested family_member."""
        response = await client.get("/responsibilities/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Make bed"
        assert data[0]["categories"] == ["MORNING"]
        assert data[0]["frequency"] == ["monday", "tuesday", "wednesday", "thursday", "friday"]
        # Verify nested relationship
        assert "family_member" in data[0]
        assert data[0]["family_member"]["name"] == "Test User"

    async def test_filters_by_assigned_to(self, client, db_session, test_family_member):
        """Should filter responsibilities by assigned_to query parameter."""
        from app.models import FamilyMember, Responsibility

        # Create another family member with their own responsibility
        other_member = FamilyMember(name="Other User", is_system=False)
        db_session.add(other_member)
        await db_session.commit()
        await db_session.refresh(other_member)

        # Responsibility for test_family_member
        resp1 = Responsibility(
            title="Task for Test User",
            categories=["MORNING"],
            assigned_to=test_family_member.id,
            frequency=["monday"],
        )
        # Responsibility for other_member
        resp2 = Responsibility(
            title="Task for Other User",
            categories=["EVENING"],
            assigned_to=other_member.id,
            frequency=["friday"],
        )
        db_session.add_all([resp1, resp2])
        await db_session.commit()

        # Act: Filter by test_family_member
        response = await client.get(f"/responsibilities/?assigned_to={test_family_member.id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Task for Test User"


# =============================================================================
# GET /responsibilities/{id} - Get single responsibility
# =============================================================================

class TestGetResponsibility:
    """Tests for GET /responsibilities/{id} endpoint."""

    async def test_returns_responsibility_when_found(self, client, test_responsibility):
        """Should return the responsibility with all fields."""
        response = await client.get(f"/responsibilities/{test_responsibility.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_responsibility.id
        assert data["title"] == "Make bed"
        assert data["description"] == "Make your bed every morning"
        assert data["categories"] == ["MORNING"]
        assert data["family_member"]["name"] == "Test User"

    async def test_returns_404_when_not_found(self, client):
        """Should return 404 when responsibility doesn't exist."""
        response = await client.get("/responsibilities/99999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Responsibility not found"


# =============================================================================
# POST /responsibilities/ - Create responsibility
# =============================================================================

class TestCreateResponsibility:
    """Tests for POST /responsibilities/ endpoint."""

    async def test_creates_responsibility(self, client, test_family_member):
        """Should create a responsibility and return 201."""
        new_resp = {
            "title": "Do homework",
            "categories": ["AFTERNOON"],
            "assigned_to": test_family_member.id,
            "frequency": ["monday", "wednesday", "friday"],
        }

        response = await client.post("/responsibilities/", json=new_resp)

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Do homework"
        assert data["categories"] == ["AFTERNOON"]
        assert data["frequency"] == ["monday", "wednesday", "friday"]
        assert "id" in data
        assert data["family_member"]["id"] == test_family_member.id

    async def test_creates_responsibility_with_multiple_categories(self, client, test_family_member):
        """Should create a responsibility with multiple categories."""
        new_resp = {
            "title": "Brush teeth",
            "categories": ["MORNING", "EVENING"],
            "assigned_to": test_family_member.id,
            "frequency": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
        }

        response = await client.post("/responsibilities/", json=new_resp)

        assert response.status_code == 201
        data = response.json()
        assert data["categories"] == ["MORNING", "EVENING"]

    async def test_creates_responsibility_with_all_fields(self, client, test_family_member):
        """Should create a responsibility with optional fields."""
        new_resp = {
            "title": "Evening routine",
            "description": "Brush teeth, read book",
            "categories": ["EVENING"],
            "assigned_to": test_family_member.id,
            "frequency": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
            "icon_url": "/uploads/icon.png",
        }

        response = await client.post("/responsibilities/", json=new_resp)

        assert response.status_code == 201
        data = response.json()
        assert data["description"] == "Brush teeth, read book"
        assert data["icon_url"] == "/uploads/icon.png"

    async def test_rejects_empty_frequency(self, client, test_family_member):
        """Should return 422 when frequency list is empty."""
        invalid = {
            "title": "No days",
            "categories": ["MORNING"],
            "assigned_to": test_family_member.id,
            "frequency": [],  # Empty - not allowed
        }

        response = await client.post("/responsibilities/", json=invalid)

        assert response.status_code == 422

    async def test_rejects_invalid_category(self, client, test_family_member):
        """Should return 422 when category is invalid."""
        invalid = {
            "title": "Bad category",
            "categories": ["INVALID"],
            "assigned_to": test_family_member.id,
            "frequency": ["monday"],
        }

        response = await client.post("/responsibilities/", json=invalid)

        assert response.status_code == 422

    async def test_rejects_empty_categories(self, client, test_family_member):
        """Should return 422 when categories list is empty."""
        invalid = {
            "title": "No categories",
            "categories": [],
            "assigned_to": test_family_member.id,
            "frequency": ["monday"],
        }

        response = await client.post("/responsibilities/", json=invalid)

        assert response.status_code == 422


# =============================================================================
# PATCH /responsibilities/{id} - Update responsibility
# =============================================================================

class TestUpdateResponsibility:
    """Tests for PATCH /responsibilities/{id} endpoint."""

    async def test_updates_responsibility_title(self, client, test_responsibility):
        """Should update the responsibility title."""
        update_data = {"title": "Updated Title"}

        response = await client.patch(
            f"/responsibilities/{test_responsibility.id}",
            json=update_data,
        )

        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"

    async def test_updates_categories(self, client, test_responsibility):
        """Should update the categories."""
        update_data = {"categories": ["CHORE"]}

        response = await client.patch(
            f"/responsibilities/{test_responsibility.id}",
            json=update_data,
        )

        assert response.status_code == 200
        assert response.json()["categories"] == ["CHORE"]

    async def test_updates_to_multiple_categories(self, client, test_responsibility):
        """Should update to multiple categories."""
        update_data = {"categories": ["MORNING", "EVENING"]}

        response = await client.patch(
            f"/responsibilities/{test_responsibility.id}",
            json=update_data,
        )

        assert response.status_code == 200
        assert response.json()["categories"] == ["MORNING", "EVENING"]

    async def test_updates_frequency(self, client, test_responsibility):
        """Should update the frequency."""
        update_data = {"frequency": ["saturday", "sunday"]}

        response = await client.patch(
            f"/responsibilities/{test_responsibility.id}",
            json=update_data,
        )

        assert response.status_code == 200
        assert response.json()["frequency"] == ["saturday", "sunday"]

    async def test_returns_404_when_not_found(self, client):
        """Should return 404 when responsibility doesn't exist."""
        response = await client.patch(
            "/responsibilities/99999",
            json={"title": "New"},
        )

        assert response.status_code == 404


# =============================================================================
# DELETE /responsibilities/{id} - Delete responsibility
# =============================================================================

class TestDeleteResponsibility:
    """Tests for DELETE /responsibilities/{id} endpoint."""

    async def test_deletes_responsibility_and_returns_204(self, client, test_responsibility):
        """Should delete the responsibility and return 204 No Content."""
        resp_id = test_responsibility.id

        response = await client.delete(f"/responsibilities/{resp_id}")

        assert response.status_code == 204
        assert response.content == b""  # No content

        # Verify it's actually deleted
        get_response = await client.get(f"/responsibilities/{resp_id}")
        assert get_response.status_code == 404

    async def test_returns_404_when_not_found(self, client):
        """Should return 404 when responsibility doesn't exist."""
        response = await client.delete("/responsibilities/99999")

        assert response.status_code == 404


# =============================================================================
# GET /responsibilities/completions - Get completions for a date
# =============================================================================

class TestGetCompletions:
    """Tests for GET /responsibilities/completions endpoint."""

    async def test_returns_empty_list_when_no_completions(self, client):
        """Should return empty array when no completions for the date."""
        response = await client.get("/responsibilities/completions?date=2024-06-15")

        assert response.status_code == 200
        assert response.json() == []

    async def test_returns_completions_for_date(
        self, client, test_responsibility, test_family_member
    ):
        """Should return completions for the specified date."""
        # First, create a completion by toggling
        target_date = "2024-06-15"
        await client.post(
            f"/responsibilities/{test_responsibility.id}/complete"
            f"?date={target_date}&family_member_id={test_family_member.id}&category=MORNING"
        )

        # Now fetch completions for that date
        response = await client.get(f"/responsibilities/completions?date={target_date}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["responsibility_id"] == test_responsibility.id
        assert data[0]["family_member_id"] == test_family_member.id
        assert data[0]["category"] == "MORNING"


# =============================================================================
# POST /responsibilities/{id}/complete - Toggle completion
# =============================================================================

class TestToggleCompletion:
    """Tests for POST /responsibilities/{id}/complete endpoint."""

    async def test_marks_responsibility_complete(
        self, client, test_responsibility, test_family_member
    ):
        """Should mark responsibility as complete and return completed=true."""
        target_date = "2024-06-15"

        response = await client.post(
            f"/responsibilities/{test_responsibility.id}/complete"
            f"?date={target_date}&family_member_id={test_family_member.id}&category=MORNING"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["completed"] is True
        assert data["completion"] is not None
        assert data["completion"]["responsibility_id"] == test_responsibility.id
        assert data["completion"]["category"] == "MORNING"

    async def test_marks_responsibility_incomplete(
        self, client, test_responsibility, test_family_member
    ):
        """Should mark responsibility as incomplete when toggled again."""
        target_date = "2024-06-15"
        url = (
            f"/responsibilities/{test_responsibility.id}/complete"
            f"?date={target_date}&family_member_id={test_family_member.id}&category=MORNING"
        )

        # First toggle: complete
        response1 = await client.post(url)
        assert response1.json()["completed"] is True

        # Second toggle: incomplete
        response2 = await client.post(url)
        assert response2.status_code == 200
        data = response2.json()
        assert data["completed"] is False
        assert data["completion"] is None

    async def test_returns_404_when_responsibility_not_found(self, client, test_family_member):
        """Should return 404 when responsibility doesn't exist."""
        response = await client.post(
            f"/responsibilities/99999/complete"
            f"?date=2024-06-15&family_member_id={test_family_member.id}&category=MORNING"
        )

        assert response.status_code == 404

    async def test_completions_are_per_date(
        self, client, test_responsibility, test_family_member
    ):
        """Completions on different dates are independent."""
        date1 = "2024-06-15"
        date2 = "2024-06-16"
        member_id = test_family_member.id

        # Complete on date1
        resp1 = await client.post(
            f"/responsibilities/{test_responsibility.id}/complete"
            f"?date={date1}&family_member_id={member_id}&category=MORNING"
        )
        assert resp1.json()["completed"] is True

        # Complete on date2 (independent)
        resp2 = await client.post(
            f"/responsibilities/{test_responsibility.id}/complete"
            f"?date={date2}&family_member_id={member_id}&category=MORNING"
        )
        assert resp2.json()["completed"] is True

        # Verify: both dates have completions
        completions1 = await client.get(f"/responsibilities/completions?date={date1}")
        completions2 = await client.get(f"/responsibilities/completions?date={date2}")
        assert len(completions1.json()) == 1
        assert len(completions2.json()) == 1

        # Uncomplete date1, date2 should remain
        resp3 = await client.post(
            f"/responsibilities/{test_responsibility.id}/complete"
            f"?date={date1}&family_member_id={member_id}&category=MORNING"
        )
        assert resp3.json()["completed"] is False

        completions1_after = await client.get(f"/responsibilities/completions?date={date1}")
        completions2_after = await client.get(f"/responsibilities/completions?date={date2}")
        assert len(completions1_after.json()) == 0  # Uncompleted
        assert len(completions2_after.json()) == 1  # Still complete

    async def test_completions_are_per_category(
        self, client, db_session, test_family_member
    ):
        """Completions for different categories are independent."""
        from app.models import Responsibility

        # Create a multi-category responsibility
        resp = Responsibility(
            title="Brush teeth",
            categories=["MORNING", "EVENING"],
            assigned_to=test_family_member.id,
            frequency=["monday", "tuesday", "wednesday", "thursday", "friday"],
        )
        db_session.add(resp)
        await db_session.commit()
        await db_session.refresh(resp)

        target_date = "2024-06-15"
        member_id = test_family_member.id

        # Complete MORNING
        resp1 = await client.post(
            f"/responsibilities/{resp.id}/complete"
            f"?date={target_date}&family_member_id={member_id}&category=MORNING"
        )
        assert resp1.json()["completed"] is True

        # Complete EVENING (independent)
        resp2 = await client.post(
            f"/responsibilities/{resp.id}/complete"
            f"?date={target_date}&family_member_id={member_id}&category=EVENING"
        )
        assert resp2.json()["completed"] is True

        # Verify: both categories have completions
        completions = await client.get(f"/responsibilities/completions?date={target_date}")
        data = completions.json()
        assert len(data) == 2
        categories = [c["category"] for c in data]
        assert "MORNING" in categories
        assert "EVENING" in categories

        # Uncomplete MORNING, EVENING should remain
        resp3 = await client.post(
            f"/responsibilities/{resp.id}/complete"
            f"?date={target_date}&family_member_id={member_id}&category=MORNING"
        )
        assert resp3.json()["completed"] is False

        completions_after = await client.get(f"/responsibilities/completions?date={target_date}")
        data_after = completions_after.json()
        assert len(data_after) == 1
        assert data_after[0]["category"] == "EVENING"
