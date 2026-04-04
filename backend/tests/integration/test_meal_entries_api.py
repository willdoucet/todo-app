"""Integration tests for /meal-entries API endpoints."""

import pytest
from datetime import date, timedelta
from unittest.mock import patch


# Mock Celery tasks to avoid dispatching real background tasks during tests
@pytest.fixture(autouse=True)
def mock_celery_tasks():
    """Prevent Celery tasks from being dispatched during tests."""
    with patch("app.tasks.sync_shopping_list_add.delay") as mock_add, \
         patch("app.tasks.sync_shopping_list_remove.delay") as mock_remove:
        yield {"add": mock_add, "remove": mock_remove}


class TestGetMealEntries:
    """Tests for GET /meal-entries/"""

    async def test_requires_date_parameters(self, client):
        response = await client.get("/meal-entries/")
        assert response.status_code == 422

    async def test_returns_empty_when_no_entries(self, client, test_meal_slot_types):
        today = date.today()
        response = await client.get(f"/meal-entries/?start_date={today}&end_date={today}")
        assert response.status_code == 200
        assert response.json() == []

    async def test_returns_entries_in_date_range(self, client, test_meal_entry):
        today = date.today()
        response = await client.get(f"/meal-entries/?start_date={today}&end_date={today}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == test_meal_entry.id
        assert data[0]["item_type"] == "recipe"
        assert data[0]["recipe"]["name"] == "Test Recipe"
        assert data[0]["meal_slot_type"]["name"] == "Dinner"

    async def test_excludes_entries_outside_range(self, client, test_meal_entry):
        yesterday = date.today() - timedelta(days=1)
        response = await client.get(f"/meal-entries/?start_date={yesterday}&end_date={yesterday}")
        assert response.status_code == 200
        assert response.json() == []

    async def test_filter_by_family_member(self, client, db_session, test_meal_slot_dinner, test_family_member):
        """Filter meals where family_member is a participant."""
        from app.models import MealEntry, meal_entry_participants
        today = date.today()

        # Create entry with explicit participant
        entry = MealEntry(
            date=today,
            meal_slot_type_id=test_meal_slot_dinner.id,
            custom_meal_name="Sandwich",
            item_type="custom",
        )
        db_session.add(entry)
        await db_session.commit()
        await db_session.refresh(entry)

        # Insert junction row
        await db_session.execute(
            meal_entry_participants.insert().values(
                meal_entry_id=entry.id, family_member_id=test_family_member.id
            )
        )
        await db_session.commit()

        # Filter by the participant
        response = await client.get(
            f"/meal-entries/?start_date={today}&end_date={today}&family_member_id={test_family_member.id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == entry.id


class TestCreateMealEntry:
    """Tests for POST /meal-entries/"""

    async def test_creates_recipe_meal_entry(self, client, test_recipe, test_meal_slot_dinner, test_family_member):
        response = await client.post(
            "/meal-entries/",
            json={
                "date": date.today().isoformat(),
                "meal_slot_type_id": test_meal_slot_dinner.id,
                "recipe_id": test_recipe.id,
                "item_type": "recipe",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["item_type"] == "recipe"
        assert data["recipe"]["name"] == "Test Recipe"
        # Participants auto-materialized from slot type defaults (empty = everyone)
        assert len(data["participants"]) >= 1

    async def test_creates_food_item_entry(self, client, test_food_item, test_meal_slot_types):
        snack = next(s for s in test_meal_slot_types if s.name == "Snack")
        response = await client.post(
            "/meal-entries/",
            json={
                "date": date.today().isoformat(),
                "meal_slot_type_id": snack.id,
                "food_item_id": test_food_item.id,
                "item_type": "food_item",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["item_type"] == "food_item"
        assert data["food_item"]["name"] == "Banana"

    async def test_creates_custom_meal_entry(self, client, test_meal_slot_dinner):
        response = await client.post(
            "/meal-entries/",
            json={
                "date": date.today().isoformat(),
                "meal_slot_type_id": test_meal_slot_dinner.id,
                "custom_meal_name": "Leftover pizza",
                "item_type": "custom",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["item_type"] == "custom"
        assert data["custom_meal_name"] == "Leftover pizza"
        assert data["recipe"] is None
        assert data["food_item"] is None

    async def test_explicit_participants(self, client, test_meal_slot_dinner, test_family_member, test_system_member):
        response = await client.post(
            "/meal-entries/",
            json={
                "date": date.today().isoformat(),
                "meal_slot_type_id": test_meal_slot_dinner.id,
                "custom_meal_name": "Kid lunch",
                "item_type": "custom",
                "participant_ids": [test_family_member.id],
            },
        )
        assert response.status_code == 201
        data = response.json()
        # Only the explicit participant, not the system member
        participant_ids = [p["id"] for p in data["participants"]]
        assert participant_ids == [test_family_member.id]

    async def test_rejects_missing_required_fields(self, client):
        response = await client.post("/meal-entries/", json={"date": "2026-01-01"})
        assert response.status_code == 422


class TestUpdateMealEntry:
    """Tests for PATCH /meal-entries/{id}"""

    async def test_marks_cooked(self, client, test_meal_entry):
        response = await client.patch(
            f"/meal-entries/{test_meal_entry.id}",
            json={"was_cooked": True},
        )
        assert response.status_code == 200
        assert response.json()["was_cooked"] is True

    async def test_updates_notes(self, client, test_meal_entry):
        response = await client.patch(
            f"/meal-entries/{test_meal_entry.id}",
            json={"notes": "Extra garlic"},
        )
        assert response.status_code == 200
        assert response.json()["notes"] == "Extra garlic"

    async def test_changes_slot_type(self, client, test_meal_entry, test_meal_slot_types):
        lunch = next(s for s in test_meal_slot_types if s.name == "Lunch")
        response = await client.patch(
            f"/meal-entries/{test_meal_entry.id}",
            json={"meal_slot_type_id": lunch.id},
        )
        assert response.status_code == 200
        assert response.json()["meal_slot_type_id"] == lunch.id

    async def test_updates_participants(self, client, test_meal_entry, test_family_member):
        response = await client.patch(
            f"/meal-entries/{test_meal_entry.id}",
            json={"participant_ids": [test_family_member.id]},
        )
        assert response.status_code == 200
        data = response.json()
        participant_ids = [p["id"] for p in data["participants"]]
        assert participant_ids == [test_family_member.id]

    async def test_returns_404_when_not_found(self, client):
        response = await client.patch("/meal-entries/99999", json={"was_cooked": True})
        assert response.status_code == 404


class TestDeleteMealEntry:
    """Tests for DELETE /meal-entries/{id}"""

    async def test_deletes_meal_entry(self, client, test_meal_entry):
        entry_id = test_meal_entry.id
        response = await client.delete(f"/meal-entries/{entry_id}")
        assert response.status_code == 200

        # Verify it's deleted
        get_response = await client.get(f"/meal-entries/{entry_id}")
        assert get_response.status_code == 404

    async def test_returns_404_when_not_found(self, client):
        response = await client.delete("/meal-entries/99999")
        assert response.status_code == 404


class TestRecipeCascade:
    """Tests for recipe FK cascade behavior."""

    async def test_meal_entry_preserved_when_recipe_deleted(
        self, client, db_session, test_meal_entry, test_recipe
    ):
        """Recipe deletion sets food_item_id to NULL but meal entry remains."""
        entry_id = test_meal_entry.id

        # Delete recipe
        response = await client.delete(f"/recipes/{test_recipe.id}")
        assert response.status_code == 200

        # Entry still exists, recipe_id is NULL
        today = date.today()
        response = await client.get(f"/meal-entries/?start_date={today}&end_date={today}")
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == entry_id
        assert data[0]["recipe_id"] is None
        assert data[0]["recipe"] is None
