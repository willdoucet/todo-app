"""
Integration tests for /tasks API endpoints.

These tests hit real FastAPI endpoints with a real PostgreSQL database.
Tasks require a list and family member to exist, so we use fixtures.
"""

import pytest


# =============================================================================
# GET /tasks/ - List all tasks
# =============================================================================

class TestGetTasks:
    """Tests for GET /tasks/ endpoint."""

    async def test_returns_empty_list_when_no_tasks_exist(self, client):
        """Should return empty array when database has no tasks."""
        response = await client.get("/tasks/")

        assert response.status_code == 200
        assert response.json() == []

    async def test_returns_all_tasks(self, client, test_task):
        """Should return all tasks with nested family_member."""
        response = await client.get("/tasks/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Test Task"
        # Verify nested relationship is included
        assert "family_member" in data[0]
        assert data[0]["family_member"]["name"] == "Test User"

    async def test_filters_by_list_id(self, client, test_list, test_family_member, db_session):
        """Should filter tasks by list_id query parameter."""
        # Arrange: Create a second list with its own task
        from app.models import List, Task

        other_list = List(name="Other List", color="#00FF00", icon="star")
        db_session.add(other_list)
        await db_session.commit()
        await db_session.refresh(other_list)

        # Task in first list
        task1 = Task(
            title="Task in Test List",
            list_id=test_list.id,
            assigned_to=test_family_member.id,
        )
        # Task in second list
        task2 = Task(
            title="Task in Other List",
            list_id=other_list.id,
            assigned_to=test_family_member.id,
        )
        db_session.add_all([task1, task2])
        await db_session.commit()

        # Act: Filter by first list
        response = await client.get(f"/tasks/?list_id={test_list.id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Task in Test List"


# =============================================================================
# GET /tasks/{id} - Get single task
# =============================================================================

class TestGetTask:
    """Tests for GET /tasks/{id} endpoint."""

    async def test_returns_task_when_found(self, client, test_task):
        """Should return the task with all fields."""
        response = await client.get(f"/tasks/{test_task.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_task.id
        assert data["title"] == "Test Task"
        assert data["description"] == "A test task"
        assert data["completed"] is False
        assert data["important"] is False
        # Verify nested family_member
        assert data["family_member"]["name"] == "Test User"

    async def test_returns_404_when_not_found(self, client):
        """Should return 404 when task doesn't exist."""
        response = await client.get("/tasks/99999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Task not found"


# =============================================================================
# POST /tasks/ - Create task
# =============================================================================

class TestCreateTask:
    """Tests for POST /tasks/ endpoint."""

    async def test_creates_task_with_required_fields(self, client, test_list, test_family_member):
        """Should create a task and return 201."""
        new_task = {
            "title": "Buy groceries",
            "list_id": test_list.id,
            "assigned_to": test_family_member.id,
        }

        response = await client.post("/tasks/", json=new_task)

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Buy groceries"
        assert data["completed"] is False  # default
        assert data["important"] is False  # default
        assert "id" in data
        assert "created_at" in data
        # Nested family_member should be included
        assert data["family_member"]["id"] == test_family_member.id

    async def test_creates_task_with_all_fields(self, client, test_list, test_family_member):
        """Should create a task with optional fields."""
        new_task = {
            "title": "Important meeting",
            "description": "Discuss Q4 planning",
            "list_id": test_list.id,
            "assigned_to": test_family_member.id,
            "completed": False,
            "important": True,
            "due_date": "2024-12-25T10:00:00",
        }

        response = await client.post("/tasks/", json=new_task)

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Important meeting"
        assert data["description"] == "Discuss Q4 planning"
        assert data["important"] is True
        assert "2024-12-25" in data["due_date"]

    async def test_rejects_missing_required_fields(self, client):
        """Should return 422 when required fields are missing."""
        incomplete_task = {"title": "Missing fields"}

        response = await client.post("/tasks/", json=incomplete_task)

        assert response.status_code == 422

    async def test_rejects_empty_title(self, client, test_list, test_family_member):
        """Should return 422 when title is empty."""
        invalid_task = {
            "title": "",
            "list_id": test_list.id,
            "assigned_to": test_family_member.id,
        }

        response = await client.post("/tasks/", json=invalid_task)

        assert response.status_code == 422


# =============================================================================
# PATCH /tasks/{id} - Update task
# =============================================================================

class TestUpdateTask:
    """Tests for PATCH /tasks/{id} endpoint."""

    async def test_updates_task_title(self, client, test_task):
        """Should update the task title."""
        update_data = {"title": "Updated Title"}

        response = await client.patch(f"/tasks/{test_task.id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        # Other fields unchanged
        assert data["description"] == "A test task"

    async def test_marks_task_as_completed(self, client, test_task):
        """Should toggle the completed status."""
        update_data = {"completed": True}

        response = await client.patch(f"/tasks/{test_task.id}", json=update_data)

        assert response.status_code == 200
        assert response.json()["completed"] is True

    async def test_marks_task_as_important(self, client, test_task):
        """Should toggle the important status."""
        update_data = {"important": True}

        response = await client.patch(f"/tasks/{test_task.id}", json=update_data)

        assert response.status_code == 200
        assert response.json()["important"] is True

    async def test_updates_multiple_fields(self, client, test_task):
        """Should update multiple fields at once."""
        update_data = {
            "title": "New Title",
            "description": "New description",
            "completed": True,
            "important": True,
        }

        response = await client.patch(f"/tasks/{test_task.id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Title"
        assert data["description"] == "New description"
        assert data["completed"] is True
        assert data["important"] is True

    async def test_returns_404_when_not_found(self, client):
        """Should return 404 when task doesn't exist."""
        response = await client.patch("/tasks/99999", json={"title": "New"})

        assert response.status_code == 404
        assert response.json()["detail"] == "Task not found"


# =============================================================================
# DELETE /tasks/{id} - Delete task
# =============================================================================

class TestDeleteTask:
    """Tests for DELETE /tasks/{id} endpoint."""

    async def test_deletes_task_and_returns_it(self, client, test_task):
        """Should delete the task and return the deleted object."""
        task_id = test_task.id

        response = await client.delete(f"/tasks/{task_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == task_id
        assert data["title"] == "Test Task"

        # Verify it's actually deleted
        get_response = await client.get(f"/tasks/{task_id}")
        assert get_response.status_code == 404

    async def test_returns_404_when_not_found(self, client):
        """Should return 404 when task doesn't exist."""
        response = await client.delete("/tasks/99999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Task not found"
