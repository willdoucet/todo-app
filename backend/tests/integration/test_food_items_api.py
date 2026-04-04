"""Integration tests for /food-items API endpoints."""

import pytest


class TestGetFoodItems:
    """Tests for GET /food-items/"""

    async def test_returns_empty_when_no_items(self, client):
        response = await client.get("/food-items/")
        assert response.status_code == 200
        assert response.json() == []

    async def test_returns_all_items(self, client, test_food_item):
        response = await client.get("/food-items/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Banana"
        assert data[0]["emoji"] == "🍌"
        assert data[0]["category"] == "fruit"

    async def test_search_by_name(self, client, db_session):
        from app.models import FoodItem
        db_session.add_all([
            FoodItem(name="Banana", category="fruit"),
            FoodItem(name="Apple", category="fruit"),
            FoodItem(name="Yogurt", category="dairy"),
        ])
        await db_session.commit()

        response = await client.get("/food-items/?search=ban")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Banana"

    async def test_filter_by_category(self, client, db_session):
        from app.models import FoodItem
        db_session.add_all([
            FoodItem(name="Banana", category="fruit"),
            FoodItem(name="Apple", category="fruit"),
            FoodItem(name="Yogurt", category="dairy"),
        ])
        await db_session.commit()

        response = await client.get("/food-items/?category=fruit")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(item["category"] == "fruit" for item in data)


class TestCreateFoodItem:
    """Tests for POST /food-items/"""

    async def test_creates_food_item(self, client):
        response = await client.post(
            "/food-items/",
            json={"name": "Yogurt", "emoji": "🥛", "category": "dairy"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Yogurt"
        assert data["emoji"] == "🥛"
        assert data["category"] == "dairy"
        assert data["is_favorite"] is False

    async def test_creates_minimal_food_item(self, client):
        response = await client.post("/food-items/", json={"name": "Bread"})
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Bread"
        assert data["emoji"] is None
        assert data["category"] is None

    async def test_rejects_duplicate_name(self, client, test_food_item):
        response = await client.post("/food-items/", json={"name": "Banana"})
        assert response.status_code == 409

    async def test_rejects_missing_name(self, client):
        response = await client.post("/food-items/", json={"emoji": "🍌"})
        assert response.status_code == 422


class TestUpdateFoodItem:
    """Tests for PATCH /food-items/{id}"""

    async def test_updates_emoji(self, client, test_food_item):
        response = await client.patch(
            f"/food-items/{test_food_item.id}",
            json={"emoji": "🍌✨"},
        )
        assert response.status_code == 200
        assert response.json()["emoji"] == "🍌✨"

    async def test_toggles_favorite(self, client, test_food_item):
        response = await client.patch(
            f"/food-items/{test_food_item.id}",
            json={"is_favorite": True},
        )
        assert response.status_code == 200
        assert response.json()["is_favorite"] is True

    async def test_returns_404_when_not_found(self, client):
        response = await client.patch("/food-items/99999", json={"name": "X"})
        assert response.status_code == 404


class TestDeleteFoodItem:
    """Tests for DELETE /food-items/{id}"""

    async def test_deletes_food_item(self, client, test_food_item):
        response = await client.delete(f"/food-items/{test_food_item.id}")
        assert response.status_code == 200

        # Verify it's gone
        get_response = await client.get(f"/food-items/")
        assert len(get_response.json()) == 0

    async def test_returns_404_when_not_found(self, client):
        response = await client.delete("/food-items/99999")
        assert response.status_code == 404
