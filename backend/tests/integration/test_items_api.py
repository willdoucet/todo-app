"""Integration tests for the unified /items API.

Replaces the legacy /recipes and /food-items test files. Covers:
    - List + filter by type/favorites/search
    - Get single item with detail eager-loaded
    - Create (both types) + validation (XOR, missing detail, duplicate name)
    - Patch (both types)
    - Soft-delete + undo flow (Expansion B)
    - FK RESTRICT behavior when meal_entries reference an item

These tests hit real FastAPI endpoints with a real PostgreSQL database via the
shared `client` fixture from `conftest.py`.
"""

import pytest


# =============================================================================
# GET /items/ — list
# =============================================================================


class TestListItems:
    async def test_returns_empty_list_when_no_items_exist(self, client):
        response = await client.get("/items/")
        assert response.status_code == 200
        assert response.json() == []

    async def test_returns_all_items(self, client, test_recipe, test_food_item):
        response = await client.get("/items/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        names = {it["name"] for it in data}
        assert names == {"Test Recipe", "Banana"}

    async def test_filters_by_type_recipe(self, client, test_recipe, test_food_item):
        response = await client.get("/items/?type=recipe")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["item_type"] == "recipe"
        assert data[0]["name"] == "Test Recipe"
        assert data[0]["recipe_detail"] is not None
        assert data[0]["food_item_detail"] is None

    async def test_filters_by_type_food_item(self, client, test_recipe, test_food_item):
        response = await client.get("/items/?type=food_item")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["item_type"] == "food_item"
        assert data[0]["name"] == "Banana"
        assert data[0]["icon_emoji"] == "🍌"
        assert data[0]["food_item_detail"]["category"] == "fruit"
        assert data[0]["recipe_detail"] is None

    async def test_filters_by_favorites_only(self, client, test_recipe, test_favorite_recipe):
        response = await client.get("/items/?favorites_only=true")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Favorite Recipe"
        assert data[0]["is_favorite"] is True

    async def test_filters_by_search(self, client, test_recipe, test_favorite_recipe):
        response = await client.get("/items/?search=Favorite")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Favorite Recipe"


# =============================================================================
# GET /items/{id} — single
# =============================================================================


class TestGetItem:
    async def test_returns_recipe_with_detail_eager_loaded(self, client, test_recipe):
        response = await client.get(f"/items/{test_recipe.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_recipe.id
        assert data["name"] == "Test Recipe"
        assert data["item_type"] == "recipe"
        assert data["tags"] == ["test"]
        rd = data["recipe_detail"]
        assert rd["description"] == "A test recipe"
        assert rd["prep_time_minutes"] == 10
        assert rd["cook_time_minutes"] == 20
        assert rd["servings"] == 4
        assert len(rd["ingredients"]) == 1

    async def test_returns_food_item_with_detail_eager_loaded(self, client, test_food_item):
        response = await client.get(f"/items/{test_food_item.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Banana"
        assert data["icon_emoji"] == "🍌"
        fid = data["food_item_detail"]
        assert fid["category"] == "fruit"
        assert float(fid["shopping_quantity"]) == 1.0
        assert fid["shopping_unit"] == "each"

    async def test_meal_entry_count_zero_for_unused_item(self, client, test_recipe):
        """Item with no meal entries shows meal_entry_count=0 (Chunk 3 delete copy)."""
        response = await client.get(f"/items/{test_recipe.id}")
        assert response.status_code == 200
        assert response.json()["meal_entry_count"] == 0

    async def test_meal_entry_count_populated_for_used_item(self, client, test_meal_entry, test_recipe):
        """Item with a linked meal entry shows meal_entry_count=1 so the delete
        confirm renders the "used in 1 meal" copy."""
        response = await client.get(f"/items/{test_recipe.id}")
        assert response.status_code == 200
        assert response.json()["meal_entry_count"] == 1

    async def test_list_items_attaches_meal_entry_count(self, client, test_meal_entry, test_recipe, test_food_item):
        """The list endpoint attaches meal_entry_count on every row so hover-delete
        from a card has the count without a second fetch."""
        response = await client.get("/items/")
        assert response.status_code == 200
        data = response.json()
        recipe_row = next(it for it in data if it["id"] == test_recipe.id)
        food_row = next(it for it in data if it["id"] == test_food_item.id)
        assert recipe_row["meal_entry_count"] == 1
        assert food_row["meal_entry_count"] == 0

    async def test_returns_404_when_not_found(self, client):
        response = await client.get("/items/99999")
        assert response.status_code == 404


# =============================================================================
# POST /items/ — create
# =============================================================================


class TestCreateItem:
    async def test_creates_recipe_with_detail(self, client):
        payload = {
            "name": "Simple Pasta",
            "item_type": "recipe",
            "tags": ["quick"],
            "recipe_detail": {
                "description": "A simple pasta dish",
                "ingredients": [{"name": "Pasta", "quantity": 1, "unit": "lb", "category": "Pantry"}],
                "instructions": "Boil. Drain. Eat.",
                "servings": 2,
            },
        }
        response = await client.post("/items/", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Simple Pasta"
        assert data["item_type"] == "recipe"
        assert data["recipe_detail"]["servings"] == 2
        assert data["food_item_detail"] is None

    async def test_creates_food_item_with_detail(self, client):
        payload = {
            "name": "Apple",
            "item_type": "food_item",
            "icon_emoji": "🍎",
            "food_item_detail": {"category": "fruit", "shopping_quantity": 6, "shopping_unit": "each"},
        }
        response = await client.post("/items/", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Apple"
        assert data["icon_emoji"] == "🍎"
        assert data["food_item_detail"]["category"] == "fruit"
        assert float(data["food_item_detail"]["shopping_quantity"]) == 6.0

    async def test_rejects_recipe_without_recipe_detail(self, client):
        payload = {"name": "Missing", "item_type": "recipe"}
        response = await client.post("/items/", json=payload)
        assert response.status_code == 422
        assert "recipe_detail is required" in str(response.json())

    async def test_rejects_food_item_without_food_item_detail(self, client):
        payload = {"name": "Missing", "item_type": "food_item"}
        response = await client.post("/items/", json=payload)
        assert response.status_code == 422
        assert "food_item_detail is required" in str(response.json())

    async def test_rejects_xor_violation_both_emoji_and_url(self, client):
        payload = {
            "name": "XOR Test",
            "item_type": "food_item",
            "icon_emoji": "🥦",
            "icon_url": "http://example.com/broccoli.png",
            "food_item_detail": {"category": "vegetable"},
        }
        response = await client.post("/items/", json=payload)
        assert response.status_code == 422
        assert "XOR" in str(response.json())

    async def test_rejects_duplicate_name_within_type(self, client, test_recipe):
        """Partial unique index enforces (name, item_type) uniqueness."""
        payload = {
            "name": "Test Recipe",
            "item_type": "recipe",
            "recipe_detail": {"instructions": "dup"},
        }
        response = await client.post("/items/", json=payload)
        assert response.status_code == 409
        assert "already exists" in str(response.json())

    async def test_allows_same_name_across_types(self, client, test_recipe):
        """A recipe and a food item can share a name (different item_type)."""
        payload = {
            "name": "Test Recipe",  # same as the fixture recipe
            "item_type": "food_item",
            "icon_emoji": "🍽",
            "food_item_detail": {"category": "Other"},
        }
        response = await client.post("/items/", json=payload)
        assert response.status_code == 201


# =============================================================================
# PATCH /items/{id}
# =============================================================================


class TestUpdateItem:
    async def test_updates_name(self, client, test_recipe):
        response = await client.patch(f"/items/{test_recipe.id}", json={"name": "New Name"})
        assert response.status_code == 200
        assert response.json()["name"] == "New Name"

    async def test_toggles_favorite(self, client, test_recipe):
        response = await client.patch(f"/items/{test_recipe.id}", json={"is_favorite": True})
        assert response.status_code == 200
        assert response.json()["is_favorite"] is True

    async def test_patches_recipe_detail_instructions(self, client, test_recipe):
        response = await client.patch(
            f"/items/{test_recipe.id}",
            json={"recipe_detail": {"instructions": "New instructions"}},
        )
        assert response.status_code == 200
        assert response.json()["recipe_detail"]["instructions"] == "New instructions"

    async def test_patches_food_item_detail_category(self, client, test_food_item):
        response = await client.patch(
            f"/items/{test_food_item.id}",
            json={"food_item_detail": {"category": "protein"}},
        )
        assert response.status_code == 200
        assert response.json()["food_item_detail"]["category"] == "protein"

    async def test_returns_404_when_not_found(self, client):
        response = await client.patch("/items/99999", json={"name": "nope"})
        assert response.status_code == 404


# =============================================================================
# DELETE /items/{id} + POST /items/{id}/undo — soft-delete flow
# =============================================================================


class TestSoftDeleteFlow:
    async def test_soft_delete_returns_undo_token(self, client, test_recipe):
        response = await client.delete(f"/items/{test_recipe.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_recipe.id
        assert "undo_token" in data
        assert "expires_at" in data

    async def test_soft_deleted_item_hidden_from_list(self, client, test_recipe):
        await client.delete(f"/items/{test_recipe.id}")
        list_res = await client.get("/items/")
        assert test_recipe.id not in [it["id"] for it in list_res.json()]

    async def test_soft_deleted_item_returns_404_from_get(self, client, test_recipe):
        await client.delete(f"/items/{test_recipe.id}")
        get_res = await client.get(f"/items/{test_recipe.id}")
        assert get_res.status_code == 404

    async def test_undo_restores_item(self, client, test_recipe):
        delete_res = await client.delete(f"/items/{test_recipe.id}")
        token = delete_res.json()["undo_token"]

        undo_res = await client.post(
            f"/items/{test_recipe.id}/undo", json={"undo_token": token}
        )
        assert undo_res.status_code == 200
        assert undo_res.json()["deleted_at"] is None

        # And the item is back in the list
        list_res = await client.get("/items/")
        assert test_recipe.id in [it["id"] for it in list_res.json()]

    async def test_undo_with_invalid_token_returns_410(self, client, test_recipe):
        await client.delete(f"/items/{test_recipe.id}")
        response = await client.post(
            f"/items/{test_recipe.id}/undo", json={"undo_token": "wrong-token"}
        )
        assert response.status_code == 410

    async def test_undo_with_consumed_token_returns_410(self, client, test_recipe):
        delete_res = await client.delete(f"/items/{test_recipe.id}")
        token = delete_res.json()["undo_token"]

        # First undo succeeds
        first = await client.post(f"/items/{test_recipe.id}/undo", json={"undo_token": token})
        assert first.status_code == 200

        # Second undo with the same token fails
        second = await client.post(f"/items/{test_recipe.id}/undo", json={"undo_token": token})
        assert second.status_code == 410

    async def test_delete_cascades_soft_hide_on_meal_entries(
        self, client, test_meal_entry, test_recipe
    ):
        """Soft-deleting an item should soft-hide its meal_entries (Expansion B cascade)."""
        from app.models import MealEntry
        from sqlalchemy import select

        await client.delete(f"/items/{test_recipe.id}")

        # The meal_entry row still exists but is now soft-hidden
        # (verified by the GET /meal-entries endpoint filtering it out)
        from datetime import date, timedelta
        today = date.today().isoformat()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        response = await client.get(
            f"/meal-entries/?start_date={today}&end_date={tomorrow}"
        )
        assert response.status_code == 200
        # The soft-hidden entry should NOT appear in visible_meal_entries_stmt
        visible_ids = [e["id"] for e in response.json()]
        assert test_meal_entry.id not in visible_ids


# =============================================================================
# Stub endpoint — suggest-icon (Expansion C, 501 for now)
# =============================================================================


class TestSuggestIconStub:
    async def test_returns_501_not_implemented(self, client):
        response = await client.post("/items/suggest-icon")
        assert response.status_code == 501
