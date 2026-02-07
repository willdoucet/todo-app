"""
Integration tests for /meal-plans API endpoints.

These tests hit real FastAPI endpoints with a real PostgreSQL database.
"""

import pytest
from datetime import date, timedelta


# =============================================================================
# GET /meal-plans/ - List meal plans by date range
# =============================================================================


class TestGetMealPlans:
    """Tests for GET /meal-plans/ endpoint."""

    async def test_requires_date_parameters(self, client):
        """Should return 422 when date parameters are missing."""
        response = await client.get("/meal-plans/")

        assert response.status_code == 422

    async def test_returns_empty_list_when_no_plans_exist(self, client):
        """Should return empty array when no plans in date range."""
        today = date.today()
        response = await client.get(
            f"/meal-plans/?start_date={today}&end_date={today}"
        )

        assert response.status_code == 200
        assert response.json() == []

    async def test_returns_plans_in_date_range(self, client, test_meal_plan):
        """Should return meal plans within the specified date range."""
        today = date.today()
        response = await client.get(
            f"/meal-plans/?start_date={today}&end_date={today}"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["category"] == "DINNER"
        # Nested recipe should be included
        assert data[0]["recipe"]["name"] == "Test Recipe"

    async def test_excludes_plans_outside_date_range(self, client, test_meal_plan):
        """Should not return plans outside the date range."""
        yesterday = date.today() - timedelta(days=1)
        response = await client.get(
            f"/meal-plans/?start_date={yesterday}&end_date={yesterday}"
        )

        assert response.status_code == 200
        assert response.json() == []


# =============================================================================
# GET /meal-plans/{id} - Get single meal plan
# =============================================================================


class TestGetMealPlan:
    """Tests for GET /meal-plans/{id} endpoint."""

    async def test_returns_meal_plan_when_found(self, client, test_meal_plan, test_recipe):
        """Should return the meal plan with nested recipe."""
        response = await client.get(f"/meal-plans/{test_meal_plan.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_meal_plan.id
        assert data["category"] == "DINNER"
        assert data["was_cooked"] is False
        # Nested recipe
        assert data["recipe"]["id"] == test_recipe.id
        assert data["recipe"]["name"] == "Test Recipe"

    async def test_returns_404_when_not_found(self, client):
        """Should return 404 when meal plan doesn't exist."""
        response = await client.get("/meal-plans/99999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Meal plan not found"


# =============================================================================
# POST /meal-plans/ - Create meal plan
# =============================================================================


class TestCreateMealPlan:
    """Tests for POST /meal-plans/ endpoint."""

    async def test_creates_meal_plan_with_recipe(self, client, test_recipe):
        """Should create a meal plan linked to a recipe."""
        today = date.today()
        new_meal_plan = {
            "date": today.isoformat(),
            "category": "LUNCH",
            "recipe_id": test_recipe.id,
        }

        response = await client.post("/meal-plans/", json=new_meal_plan)

        assert response.status_code == 201
        data = response.json()
        assert data["date"] == today.isoformat()
        assert data["category"] == "LUNCH"
        assert data["recipe_id"] == test_recipe.id
        assert data["recipe"]["name"] == "Test Recipe"
        assert data["was_cooked"] is False
        assert "id" in data

    async def test_creates_meal_plan_with_custom_meal(self, client):
        """Should create a meal plan with a custom meal name."""
        today = date.today()
        new_meal_plan = {
            "date": today.isoformat(),
            "category": "BREAKFAST",
            "custom_meal_name": "Leftovers from yesterday",
        }

        response = await client.post("/meal-plans/", json=new_meal_plan)

        assert response.status_code == 201
        data = response.json()
        assert data["category"] == "BREAKFAST"
        assert data["custom_meal_name"] == "Leftovers from yesterday"
        assert data["recipe_id"] is None
        assert data["recipe"] is None

    async def test_creates_meal_plan_with_notes(self, client, test_recipe):
        """Should create a meal plan with notes."""
        today = date.today()
        new_meal_plan = {
            "date": today.isoformat(),
            "category": "DINNER",
            "recipe_id": test_recipe.id,
            "notes": "Double the garlic",
        }

        response = await client.post("/meal-plans/", json=new_meal_plan)

        assert response.status_code == 201
        assert response.json()["notes"] == "Double the garlic"

    async def test_rejects_missing_required_fields(self, client):
        """Should return 422 when required fields are missing."""
        incomplete_plan = {"category": "DINNER"}

        response = await client.post("/meal-plans/", json=incomplete_plan)

        assert response.status_code == 422


# =============================================================================
# PATCH /meal-plans/{id} - Update meal plan
# =============================================================================


class TestUpdateMealPlan:
    """Tests for PATCH /meal-plans/{id} endpoint."""

    async def test_marks_meal_as_cooked(self, client, test_meal_plan):
        """Should toggle the was_cooked status."""
        update_data = {"was_cooked": True}

        response = await client.patch(
            f"/meal-plans/{test_meal_plan.id}", json=update_data
        )

        assert response.status_code == 200
        assert response.json()["was_cooked"] is True

    async def test_updates_notes(self, client, test_meal_plan):
        """Should update the notes field."""
        update_data = {"notes": "Made with extra spice"}

        response = await client.patch(
            f"/meal-plans/{test_meal_plan.id}", json=update_data
        )

        assert response.status_code == 200
        assert response.json()["notes"] == "Made with extra spice"

    async def test_changes_category(self, client, test_meal_plan):
        """Should change the meal category."""
        update_data = {"category": "LUNCH"}

        response = await client.patch(
            f"/meal-plans/{test_meal_plan.id}", json=update_data
        )

        assert response.status_code == 200
        assert response.json()["category"] == "LUNCH"

    async def test_switches_to_custom_meal(self, client, test_meal_plan):
        """Should switch from recipe to custom meal."""
        update_data = {
            "recipe_id": None,
            "custom_meal_name": "Takeout pizza",
        }

        response = await client.patch(
            f"/meal-plans/{test_meal_plan.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["custom_meal_name"] == "Takeout pizza"

    async def test_returns_404_when_not_found(self, client):
        """Should return 404 when meal plan doesn't exist."""
        response = await client.patch(
            "/meal-plans/99999", json={"was_cooked": True}
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Meal plan not found"


# =============================================================================
# DELETE /meal-plans/{id} - Delete meal plan
# =============================================================================


class TestDeleteMealPlan:
    """Tests for DELETE /meal-plans/{id} endpoint."""

    async def test_deletes_meal_plan_and_returns_it(self, client, test_meal_plan):
        """Should delete the meal plan and return the deleted object."""
        meal_plan_id = test_meal_plan.id

        response = await client.delete(f"/meal-plans/{meal_plan_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == meal_plan_id
        assert data["category"] == "DINNER"

        # Verify it's actually deleted
        get_response = await client.get(f"/meal-plans/{meal_plan_id}")
        assert get_response.status_code == 404

    async def test_returns_404_when_not_found(self, client):
        """Should return 404 when meal plan doesn't exist."""
        response = await client.delete("/meal-plans/99999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Meal plan not found"


# =============================================================================
# Recipe cascade behavior
# =============================================================================


class TestRecipeCascade:
    """Tests for cascade behavior when recipe is deleted."""

    async def test_meal_plan_preserved_when_recipe_deleted(
        self, client, db_session, test_meal_plan, test_recipe
    ):
        """Meal plan should remain with recipe_id set to NULL when recipe is deleted."""
        meal_plan_id = test_meal_plan.id

        # Delete the recipe
        delete_response = await client.delete(f"/recipes/{test_recipe.id}")
        assert delete_response.status_code == 200

        # Meal plan should still exist but with no recipe
        today = date.today()
        get_response = await client.get(
            f"/meal-plans/?start_date={today}&end_date={today}"
        )
        assert get_response.status_code == 200
        data = get_response.json()
        assert len(data) == 1
        assert data[0]["id"] == meal_plan_id
        assert data[0]["recipe_id"] is None
        assert data[0]["recipe"] is None
