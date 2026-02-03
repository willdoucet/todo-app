"""
Integration tests for /lists API endpoints.

These tests hit real FastAPI endpoints with a real PostgreSQL database.
Each test runs in a transaction that gets rolled back, keeping tests isolated.
"""

import pytest


# =============================================================================
# GET /lists/ - List all lists
# =============================================================================

class TestGetLists:
    """Tests for GET /lists/ endpoint."""

    async def test_returns_empty_list_when_no_lists_exist(self, client):
        """Should return empty array when database has no lists."""
        # Act
        response = await client.get("/lists/")

        # Assert
        assert response.status_code == 200
        assert response.json() == []

    async def test_returns_all_lists(self, client, test_list):
        """Should return all lists in the database."""
        # Arrange: test_list fixture creates one list

        # Act
        response = await client.get("/lists/")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test List"
        assert data[0]["color"] == "#EF4444"
        assert data[0]["icon"] == "clipboard"


# =============================================================================
# GET /lists/{id} - Get single list
# =============================================================================

class TestGetList:
    """Tests for GET /lists/{id} endpoint."""

    async def test_returns_list_when_found(self, client, test_list):
        """Should return the list when it exists."""
        # Act
        response = await client.get(f"/lists/{test_list.id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_list.id
        assert data["name"] == "Test List"
        assert data["color"] == "#EF4444"

    async def test_returns_404_when_not_found(self, client):
        """Should return 404 when list doesn't exist."""
        # Act
        response = await client.get("/lists/99999")

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "List not found"


# =============================================================================
# POST /lists/ - Create list
# =============================================================================

class TestCreateList:
    """Tests for POST /lists/ endpoint."""

    async def test_creates_list_with_all_fields(self, client):
        """Should create a list and return 201."""
        # Arrange
        new_list = {
            "name": "Work Tasks",
            "color": "#3B82F6",
            "icon": "briefcase",
        }

        # Act
        response = await client.post("/lists/", json=new_list)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Work Tasks"
        assert data["color"] == "#3B82F6"
        assert data["icon"] == "briefcase"
        assert "id" in data
        assert "created_at" in data

    async def test_creates_list_with_minimal_fields(self, client):
        """Should create a list with only required fields."""
        # Arrange: Only name is required
        new_list = {"name": "Simple List"}

        # Act
        response = await client.post("/lists/", json=new_list)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Simple List"
        assert data["color"] is None
        assert data["icon"] is None

    async def test_rejects_empty_name(self, client):
        """Should return 422 when name is empty."""
        # Arrange
        invalid_list = {"name": ""}

        # Act
        response = await client.post("/lists/", json=invalid_list)

        # Assert
        assert response.status_code == 422  # Validation error

    async def test_rejects_missing_name(self, client):
        """Should return 422 when name is missing."""
        # Arrange
        invalid_list = {"color": "#FF0000"}

        # Act
        response = await client.post("/lists/", json=invalid_list)

        # Assert
        assert response.status_code == 422  # Validation error


# =============================================================================
# PATCH /lists/{id} - Update list
# =============================================================================

class TestUpdateList:
    """Tests for PATCH /lists/{id} endpoint."""

    async def test_updates_list_name(self, client, test_list):
        """Should update the list name."""
        # Arrange
        update_data = {"name": "Updated Name"}

        # Act
        response = await client.patch(f"/lists/{test_list.id}", json=update_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        # Other fields unchanged
        assert data["color"] == "#EF4444"

    async def test_updates_multiple_fields(self, client, test_list):
        """Should update multiple fields at once."""
        # Arrange
        update_data = {
            "name": "New Name",
            "color": "#00FF00",
            "icon": "star",
        }

        # Act
        response = await client.patch(f"/lists/{test_list.id}", json=update_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["color"] == "#00FF00"
        assert data["icon"] == "star"

    async def test_returns_404_when_not_found(self, client):
        """Should return 404 when list doesn't exist."""
        # Act
        response = await client.patch("/lists/99999", json={"name": "New Name"})

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "List not found"


# =============================================================================
# DELETE /lists/{id} - Delete list
# =============================================================================

class TestDeleteList:
    """Tests for DELETE /lists/{id} endpoint."""

    async def test_deletes_list_and_returns_it(self, client, test_list):
        """Should delete the list and return the deleted object."""
        # Act
        response = await client.delete(f"/lists/{test_list.id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_list.id
        assert data["name"] == "Test List"

        # Verify it's actually deleted
        get_response = await client.get(f"/lists/{test_list.id}")
        assert get_response.status_code == 404

    async def test_returns_404_when_not_found(self, client):
        """Should return 404 when list doesn't exist."""
        # Act
        response = await client.delete("/lists/99999")

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "List not found"
