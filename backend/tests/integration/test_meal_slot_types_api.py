"""Integration tests for /meal-slot-types API endpoints."""

import pytest


class TestGetMealSlotTypes:
    """Tests for GET /meal-slot-types/"""

    async def test_returns_all_slots_ordered_by_sort_order(self, client, test_meal_slot_types):
        response = await client.get("/meal-slot-types/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4
        # Ordered by sort_order (1, 2, 3, 4)
        assert data[0]["name"] == "Breakfast"
        assert data[1]["name"] == "Lunch"
        assert data[2]["name"] == "Dinner"
        assert data[3]["name"] == "Snack"

    async def test_returns_empty_list_when_no_slots(self, client):
        response = await client.get("/meal-slot-types/")
        assert response.status_code == 200
        assert response.json() == []

    async def test_includes_inactive_slots(self, client, db_session, test_meal_slot_types):
        # Deactivate one slot
        from app.models import MealSlotType
        from sqlalchemy import update
        await db_session.execute(
            update(MealSlotType).where(MealSlotType.name == "Snack").values(is_active=False)
        )
        await db_session.commit()

        response = await client.get("/meal-slot-types/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4  # All 4 still returned
        snack = next(s for s in data if s["name"] == "Snack")
        assert snack["is_active"] is False


class TestCreateMealSlotType:
    """Tests for POST /meal-slot-types/"""

    async def test_creates_custom_slot(self, client, test_family_member):
        response = await client.post(
            "/meal-slot-types/",
            json={
                "name": "Kid Snack",
                "sort_order": 5,
                "color": "#FF5733",
                "icon": "🍎",
                "default_participants": [test_family_member.id],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Kid Snack"
        assert data["is_default"] is False  # User-created
        assert data["is_active"] is True
        assert data["default_participants"] == [test_family_member.id]

    async def test_rejects_missing_name(self, client):
        response = await client.post("/meal-slot-types/", json={"sort_order": 5})
        assert response.status_code == 422


class TestUpdateMealSlotType:
    """Tests for PATCH /meal-slot-types/{id}"""

    async def test_renames_slot(self, client, test_meal_slot_dinner):
        response = await client.patch(
            f"/meal-slot-types/{test_meal_slot_dinner.id}",
            json={"name": "Family Dinner"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Family Dinner"

    async def test_changes_color(self, client, test_meal_slot_dinner):
        response = await client.patch(
            f"/meal-slot-types/{test_meal_slot_dinner.id}",
            json={"color": "#FF0000"},
        )
        assert response.status_code == 200
        assert response.json()["color"] == "#FF0000"

    async def test_toggles_active(self, client, test_meal_slot_dinner):
        response = await client.patch(
            f"/meal-slot-types/{test_meal_slot_dinner.id}",
            json={"is_active": False},
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is False

    async def test_returns_404_when_not_found(self, client):
        response = await client.patch("/meal-slot-types/99999", json={"name": "X"})
        assert response.status_code == 404


class TestDeleteMealSlotType:
    """Tests for DELETE /meal-slot-types/{id}"""

    async def test_hard_deletes_slot_with_no_entries(self, client, test_meal_slot_types):
        snack = next(s for s in test_meal_slot_types if s.name == "Snack")
        response = await client.delete(f"/meal-slot-types/{snack.id}")
        assert response.status_code == 200

        # Verify it's gone
        get_response = await client.get("/meal-slot-types/")
        names = [s["name"] for s in get_response.json()]
        assert "Snack" not in names

    async def test_soft_deletes_slot_with_entries(self, client, test_meal_entry, test_meal_slot_dinner):
        response = await client.delete(f"/meal-slot-types/{test_meal_slot_dinner.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False  # Soft-deleted

        # Slot is still in the list, just inactive
        get_response = await client.get("/meal-slot-types/")
        dinner = next(s for s in get_response.json() if s["id"] == test_meal_slot_dinner.id)
        assert dinner["is_active"] is False

    async def test_returns_404_when_not_found(self, client):
        response = await client.delete("/meal-slot-types/99999")
        assert response.status_code == 404


class TestResetMealSlotTypes:
    """Tests for POST /meal-slot-types/reset"""

    async def test_reactivates_default_slots(self, client, db_session, test_meal_slot_types):
        # Deactivate all defaults
        from app.models import MealSlotType
        from sqlalchemy import update
        await db_session.execute(update(MealSlotType).values(is_active=False))
        await db_session.commit()

        response = await client.post("/meal-slot-types/reset")
        assert response.status_code == 200
        data = response.json()
        # All 4 defaults should be active again
        assert all(s["is_active"] for s in data if s["is_default"])

    async def test_removes_user_created_slots_without_entries(
        self, client, db_session, test_meal_slot_types
    ):
        # Add a user-created slot
        from app.models import MealSlotType
        custom = MealSlotType(
            name="Custom", sort_order=5, is_default=False, is_active=True, default_participants=[]
        )
        db_session.add(custom)
        await db_session.commit()

        response = await client.post("/meal-slot-types/reset")
        assert response.status_code == 200
        names = [s["name"] for s in response.json()]
        assert "Custom" not in names  # Hard-deleted
