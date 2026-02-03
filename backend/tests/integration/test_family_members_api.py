"""
Integration tests for /family-members API endpoints.

Family members have special business rules:
- "Everyone" is a system member that cannot be updated or deleted
- Names must be unique
- Members with assigned tasks cannot be deleted
"""

import pytest


# =============================================================================
# GET /family-members/ - List all family members
# =============================================================================

class TestGetFamilyMembers:
    """Tests for GET /family-members/ endpoint."""

    async def test_returns_empty_list_when_no_members_exist(self, client):
        """Should return empty array when database has no members."""
        response = await client.get("/family-members/")

        assert response.status_code == 200
        assert response.json() == []

    async def test_returns_all_members(self, client, test_family_member):
        """Should return all family members."""
        response = await client.get("/family-members/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test User"
        assert data[0]["is_system"] is False

    async def test_returns_system_member_first(self, client, test_system_member, test_family_member):
        """Should return 'Everyone' (system member) first in the list."""
        response = await client.get("/family-members/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        # System member should be first
        assert data[0]["name"] == "Everyone"
        assert data[0]["is_system"] is True
        # Regular member second
        assert data[1]["name"] == "Test User"


# =============================================================================
# GET /family-members/{id} - Get single family member
# =============================================================================

class TestGetFamilyMember:
    """Tests for GET /family-members/{id} endpoint."""

    async def test_returns_member_when_found(self, client, test_family_member):
        """Should return the family member."""
        response = await client.get(f"/family-members/{test_family_member.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_family_member.id
        assert data["name"] == "Test User"
        assert data["is_system"] is False

    async def test_returns_404_when_not_found(self, client):
        """Should return 404 when member doesn't exist."""
        response = await client.get("/family-members/99999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Family member not found"


# =============================================================================
# POST /family-members/ - Create family member
# =============================================================================

class TestCreateFamilyMember:
    """Tests for POST /family-members/ endpoint."""

    async def test_creates_member(self, client):
        """Should create a family member and return 201."""
        new_member = {"name": "Alice"}

        response = await client.post("/family-members/", json=new_member)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Alice"
        assert data["is_system"] is False
        assert "id" in data
        assert "created_at" in data

    async def test_creates_member_with_photo(self, client):
        """Should create a family member with photo URL."""
        new_member = {
            "name": "Bob",
            "photo_url": "/uploads/bob.jpg",
        }

        response = await client.post("/family-members/", json=new_member)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Bob"
        assert data["photo_url"] == "/uploads/bob.jpg"

    async def test_rejects_duplicate_name(self, client, test_family_member):
        """Should return 400 when name already exists."""
        duplicate = {"name": "Test User"}  # Same as fixture

        response = await client.post("/family-members/", json=duplicate)

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    async def test_rejects_empty_name(self, client):
        """Should return 422 when name is empty."""
        invalid = {"name": ""}

        response = await client.post("/family-members/", json=invalid)

        assert response.status_code == 422


# =============================================================================
# PATCH /family-members/{id} - Update family member
# =============================================================================

class TestUpdateFamilyMember:
    """Tests for PATCH /family-members/{id} endpoint."""

    async def test_updates_member_name(self, client, test_family_member):
        """Should update the member's name."""
        update_data = {"name": "Updated Name"}

        response = await client.patch(
            f"/family-members/{test_family_member.id}",
            json=update_data,
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    async def test_updates_photo_url(self, client, test_family_member):
        """Should update the member's photo URL."""
        update_data = {"photo_url": "/uploads/new-photo.jpg"}

        response = await client.patch(
            f"/family-members/{test_family_member.id}",
            json=update_data,
        )

        assert response.status_code == 200
        assert response.json()["photo_url"] == "/uploads/new-photo.jpg"

    async def test_returns_404_when_not_found(self, client):
        """Should return 404 when member doesn't exist."""
        response = await client.patch(
            "/family-members/99999",
            json={"name": "New Name"},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Family member not found"

    async def test_rejects_update_of_system_member(self, client, test_system_member):
        """Should return 400 when trying to update system member."""
        response = await client.patch(
            f"/family-members/{test_system_member.id}",
            json={"name": "Not Everyone"},
        )

        assert response.status_code == 400
        assert "system family member" in response.json()["detail"]

    async def test_rejects_duplicate_name_on_update(self, client, db_session):
        """Should return 400 when updating to a name that already exists."""
        # Arrange: Create two members
        from app.models import FamilyMember

        alice = FamilyMember(name="Alice", is_system=False)
        bob = FamilyMember(name="Bob", is_system=False)
        db_session.add_all([alice, bob])
        await db_session.commit()
        await db_session.refresh(alice)
        await db_session.refresh(bob)

        # Act: Try to rename Bob to Alice
        response = await client.patch(
            f"/family-members/{bob.id}",
            json={"name": "Alice"},
        )

        # Assert
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]


# =============================================================================
# DELETE /family-members/{id} - Delete family member
# =============================================================================

class TestDeleteFamilyMember:
    """Tests for DELETE /family-members/{id} endpoint."""

    async def test_deletes_member_and_returns_it(self, client, test_family_member):
        """Should delete the member and return the deleted object."""
        member_id = test_family_member.id

        response = await client.delete(f"/family-members/{member_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == member_id
        assert data["name"] == "Test User"

        # Verify it's actually deleted
        get_response = await client.get(f"/family-members/{member_id}")
        assert get_response.status_code == 404

    async def test_returns_404_when_not_found(self, client):
        """Should return 404 when member doesn't exist."""
        response = await client.delete("/family-members/99999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Family member not found"

    async def test_rejects_delete_of_system_member(self, client, test_system_member):
        """Should return 400 when trying to delete system member."""
        response = await client.delete(f"/family-members/{test_system_member.id}")

        assert response.status_code == 400
        assert "system family member" in response.json()["detail"]

    async def test_rejects_delete_of_member_with_tasks(
        self, client, test_task, test_family_member
    ):
        """Should return 400 when member has assigned tasks."""
        # test_task fixture creates a task assigned to test_family_member

        response = await client.delete(f"/family-members/{test_family_member.id}")

        assert response.status_code == 400
        assert "with tasks" in response.json()["detail"]
