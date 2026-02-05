"""
Integration tests for /recipes API endpoints.

These tests hit real FastAPI endpoints with a real PostgreSQL database.
"""

import pytest


# =============================================================================
# GET /recipes/ - List all recipes
# =============================================================================


class TestGetRecipes:
    """Tests for GET /recipes/ endpoint."""

    async def test_returns_empty_list_when_no_recipes_exist(self, client):
        """Should return empty array when database has no recipes."""
        response = await client.get("/recipes/")

        assert response.status_code == 200
        assert response.json() == []

    async def test_returns_all_recipes(self, client, test_recipe):
        """Should return all recipes."""
        response = await client.get("/recipes/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Recipe"
        assert data[0]["instructions"] == "Test instructions"

    async def test_filters_by_favorites(self, client, test_recipe, test_favorite_recipe):
        """Should filter recipes by favorites_only query parameter."""
        # All recipes
        response = await client.get("/recipes/")
        assert len(response.json()) == 2

        # Favorites only
        response = await client.get("/recipes/?favorites_only=true")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Favorite Recipe"
        assert data[0]["is_favorite"] is True


# =============================================================================
# GET /recipes/{id} - Get single recipe
# =============================================================================


class TestGetRecipe:
    """Tests for GET /recipes/{id} endpoint."""

    async def test_returns_recipe_when_found(self, client, test_recipe):
        """Should return the recipe with all fields."""
        response = await client.get(f"/recipes/{test_recipe.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_recipe.id
        assert data["name"] == "Test Recipe"
        assert data["description"] == "A test recipe"
        assert data["prep_time_minutes"] == 10
        assert data["cook_time_minutes"] == 20
        assert data["servings"] == 4
        assert data["is_favorite"] is False
        assert data["tags"] == ["test"]
        assert len(data["ingredients"]) == 1

    async def test_returns_404_when_not_found(self, client):
        """Should return 404 when recipe doesn't exist."""
        response = await client.get("/recipes/99999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Recipe not found"


# =============================================================================
# POST /recipes/ - Create recipe
# =============================================================================


class TestCreateRecipe:
    """Tests for POST /recipes/ endpoint."""

    async def test_creates_recipe_with_required_fields(self, client):
        """Should create a recipe with minimal fields."""
        new_recipe = {
            "name": "Simple Pasta",
            "instructions": "Boil water, cook pasta, add sauce.",
        }

        response = await client.post("/recipes/", json=new_recipe)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Simple Pasta"
        assert data["instructions"] == "Boil water, cook pasta, add sauce."
        assert data["servings"] == 4  # default
        assert data["is_favorite"] is False  # default
        assert "id" in data
        assert "created_at" in data

    async def test_creates_recipe_with_all_fields(self, client):
        """Should create a recipe with all optional fields."""
        new_recipe = {
            "name": "Honey Garlic Chicken",
            "description": "Quick and easy dinner",
            "ingredients": [
                {"name": "Chicken breast", "quantity": 2, "unit": "lb", "category": "Protein"},
                {"name": "Honey", "quantity": 0.25, "unit": "cups", "category": "Pantry"},
            ],
            "instructions": "1. Season chicken. 2. Cook in pan. 3. Add sauce.",
            "prep_time_minutes": 10,
            "cook_time_minutes": 25,
            "servings": 4,
            "image_url": "https://example.com/chicken.jpg",
            "is_favorite": True,
            "tags": ["chicken", "quick", "dinner"],
        }

        response = await client.post("/recipes/", json=new_recipe)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Honey Garlic Chicken"
        assert data["description"] == "Quick and easy dinner"
        assert len(data["ingredients"]) == 2
        assert data["prep_time_minutes"] == 10
        assert data["cook_time_minutes"] == 25
        assert data["is_favorite"] is True
        assert data["tags"] == ["chicken", "quick", "dinner"]

    async def test_rejects_missing_required_fields(self, client):
        """Should return 422 when required fields are missing."""
        incomplete_recipe = {"name": "Missing Instructions"}

        response = await client.post("/recipes/", json=incomplete_recipe)

        assert response.status_code == 422

    async def test_rejects_empty_name(self, client):
        """Should return 422 when name is empty."""
        invalid_recipe = {
            "name": "",
            "instructions": "Some instructions",
        }

        response = await client.post("/recipes/", json=invalid_recipe)

        assert response.status_code == 422


# =============================================================================
# PATCH /recipes/{id} - Update recipe
# =============================================================================


class TestUpdateRecipe:
    """Tests for PATCH /recipes/{id} endpoint."""

    async def test_updates_recipe_name(self, client, test_recipe):
        """Should update the recipe name."""
        update_data = {"name": "Updated Recipe Name"}

        response = await client.patch(f"/recipes/{test_recipe.id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Recipe Name"
        # Other fields unchanged
        assert data["instructions"] == "Test instructions"

    async def test_toggles_favorite_status(self, client, test_recipe):
        """Should toggle the is_favorite status."""
        update_data = {"is_favorite": True}

        response = await client.patch(f"/recipes/{test_recipe.id}", json=update_data)

        assert response.status_code == 200
        assert response.json()["is_favorite"] is True

    async def test_updates_multiple_fields(self, client, test_recipe):
        """Should update multiple fields at once."""
        update_data = {
            "name": "New Name",
            "description": "New description",
            "cook_time_minutes": 45,
            "is_favorite": True,
        }

        response = await client.patch(f"/recipes/{test_recipe.id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["description"] == "New description"
        assert data["cook_time_minutes"] == 45
        assert data["is_favorite"] is True

    async def test_returns_404_when_not_found(self, client):
        """Should return 404 when recipe doesn't exist."""
        response = await client.patch("/recipes/99999", json={"name": "New"})

        assert response.status_code == 404
        assert response.json()["detail"] == "Recipe not found"


# =============================================================================
# DELETE /recipes/{id} - Delete recipe
# =============================================================================


class TestDeleteRecipe:
    """Tests for DELETE /recipes/{id} endpoint."""

    async def test_deletes_recipe_and_returns_it(self, client, test_recipe):
        """Should delete the recipe and return the deleted object."""
        recipe_id = test_recipe.id

        response = await client.delete(f"/recipes/{recipe_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == recipe_id
        assert data["name"] == "Test Recipe"

        # Verify it's actually deleted
        get_response = await client.get(f"/recipes/{recipe_id}")
        assert get_response.status_code == 404

    async def test_returns_404_when_not_found(self, client):
        """Should return 404 when recipe doesn't exist."""
        response = await client.delete("/recipes/99999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Recipe not found"
