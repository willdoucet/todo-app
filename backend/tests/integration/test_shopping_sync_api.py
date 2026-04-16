"""Integration tests for shopping list aggregation sync via API endpoints.

Tests the full flow: create meal entries / food items → sync to shopping list →
verify aggregated shopping tasks, check-flip, list swap, and unlink behaviors.
"""

import pytest
from datetime import date
from unittest.mock import patch

from sqlalchemy import select

from decimal import Decimal

from app.models import Task, MealEntry, Item, RecipeDetail, FoodItemDetail, AppSettings
from app.services.shopping_sync import sync_meal_to_shopping_list


# =============================================================================
# Celery mock (module-wide) — prevent real task dispatch
# =============================================================================

@pytest.fixture(autouse=True)
def mock_celery_tasks():
    """Prevent Celery tasks from being dispatched during tests."""
    with patch("app.tasks.sync_shopping_list_add.delay") as mock_add, \
         patch("app.tasks.sync_shopping_list_remove.delay") as mock_remove:
        yield {"add": mock_add, "remove": mock_remove}


# =============================================================================
# Helpers
# =============================================================================

async def _link_shopping_list(db_session, settings, list_id):
    """Set mealboard_shopping_list_id on AppSettings."""
    settings.mealboard_shopping_list_id = list_id
    await db_session.commit()
    await db_session.refresh(settings)


async def _create_food_item(db_session, name, quantity=1.0, unit="each", category="fruit", emoji="🍎"):
    """Create an Item (item_type=food_item) + FoodItemDetail directly in the DB.

    Returns the Item (has .id). Kept as `_create_food_item` with original signature
    so test bodies don't need to change after the item-model refactor.
    """
    item = Item(
        name=name,
        item_type="food_item",
        icon_emoji=emoji,
        is_favorite=False,
    )
    db_session.add(item)
    await db_session.flush()
    detail = FoodItemDetail(
        item_id=item.id,
        category=category,
        shopping_quantity=Decimal(str(quantity)),
        shopping_unit=unit,
    )
    db_session.add(detail)
    await db_session.commit()
    await db_session.refresh(item)
    return item


async def _create_recipe(db_session, name, ingredients):
    """Create an Item (item_type=recipe) + RecipeDetail directly in the DB."""
    item = Item(
        name=name,
        item_type="recipe",
        is_favorite=False,
        tags=[],
    )
    db_session.add(item)
    await db_session.flush()
    detail = RecipeDetail(
        item_id=item.id,
        description="Test recipe",
        ingredients=ingredients,
        instructions="Test",
        prep_time_minutes=5,
        cook_time_minutes=10,
        servings=4,
    )
    db_session.add(detail)
    await db_session.commit()
    await db_session.refresh(item)
    return item


async def _create_meal_entry_and_sync(client, db_session, slot_id, **kwargs):
    """Create a meal entry via API (sets status=pending), then sync directly.

    Accepts legacy kwargs `recipe_id=`, `food_item_id=`, `item_type=` for
    backward-compat with the test bodies written before the item-model refactor.
    All three collapse into a single `item_id` in the new API shape.
    """
    # Translate legacy kwargs: both recipe_id and food_item_id now map to item_id
    # since Item is a unified table.
    item_id = kwargs.pop("recipe_id", None) or kwargs.pop("food_item_id", None)
    kwargs.pop("item_type", None)  # dropped from the new MealEntryCreate schema

    payload = {
        "date": date.today().isoformat(),
        "meal_slot_type_id": slot_id,
    }
    if item_id is not None:
        payload["item_id"] = item_id
    payload.update(kwargs)

    resp = await client.post("/meal-entries/", json=payload)
    assert resp.status_code == 201, resp.text
    entry_id = resp.json()["id"]

    # The API sets status to "pending" after commit. Sync directly.
    await sync_meal_to_shopping_list(db_session, entry_id)
    return entry_id


async def _get_auto_tasks(db_session, list_id):
    """Return all mealboard_auto tasks on a list."""
    result = await db_session.execute(
        select(Task)
        .where(Task.list_id == list_id, Task.aggregation_source == "mealboard_auto")
    )
    return result.scalars().all()


async def _get_all_tasks_on_list(db_session, list_id):
    """Return all tasks on a list (auto + manual)."""
    result = await db_session.execute(
        select(Task).where(Task.list_id == list_id)
    )
    return result.scalars().all()


# =============================================================================
# 1. Aggregation spec examples
# =============================================================================


class TestAggregationSpecExamples:
    """Six aggregation scenarios from the design plan."""

    async def test_banana_food_item_plus_recipe_banana_aggregates(
        self, client, db_session, test_list, test_meal_slot_dinner, test_app_settings, test_family_member,
    ):
        """Banana food item (1 each) + recipe with 2 bananas → 1 row, '3 each banana'."""
        await _link_shopping_list(db_session, test_app_settings, test_list.id)

        banana = await _create_food_item(db_session, "Banana", quantity=1.0, unit="each", emoji="🍌")
        recipe = await _create_recipe(db_session, "Banana Smoothie", [
            {"name": "Banana", "quantity": 2, "unit": None, "category": "fruit"},
        ])

        # Create food_item meal entry + sync
        await _create_meal_entry_and_sync(
            client, db_session, test_meal_slot_dinner.id,
            food_item_id=banana.id, item_type="food_item",
        )
        # Create recipe meal entry + sync
        await _create_meal_entry_and_sync(
            client, db_session, test_meal_slot_dinner.id,
            recipe_id=recipe.id, item_type="recipe",
        )

        tasks = await _get_auto_tasks(db_session, test_list.id)
        assert len(tasks) == 1, f"Expected 1 row, got {len(tasks)}: {[t.title for t in tasks]}"
        assert tasks[0].aggregation_key_name == "banana"
        assert "3" in tasks[0].title
        assert "each" in tasks[0].title

    async def test_bananas_plural_food_item_plus_recipe_banana_aggregates(
        self, client, db_session, test_list, test_meal_slot_dinner, test_app_settings, test_family_member,
    ):
        """'Bananas' food item + recipe with '1 banana' → single row (canonical: 'banana')."""
        await _link_shopping_list(db_session, test_app_settings, test_list.id)

        bananas_item = await _create_food_item(db_session, "Bananas", quantity=1.0, unit="each", emoji="🍌")
        recipe = await _create_recipe(db_session, "Banana Bread", [
            {"name": "banana", "quantity": 1, "unit": None, "category": "fruit"},
        ])

        await _create_meal_entry_and_sync(
            client, db_session, test_meal_slot_dinner.id,
            food_item_id=bananas_item.id, item_type="food_item",
        )
        await _create_meal_entry_and_sync(
            client, db_session, test_meal_slot_dinner.id,
            recipe_id=recipe.id, item_type="recipe",
        )

        tasks = await _get_auto_tasks(db_session, test_list.id)
        assert len(tasks) == 1, f"Expected 1 row, got {len(tasks)}: {[t.title for t in tasks]}"
        assert tasks[0].aggregation_key_name == "banana"

    async def test_grapes_bunch_aggregates(
        self, client, db_session, test_list, test_meal_slot_dinner, test_app_settings, test_family_member,
    ):
        """Grapes food item (1 bunch) + recipe '1 bunch grapes' → '2 bunch grapes'."""
        await _link_shopping_list(db_session, test_app_settings, test_list.id)

        grapes = await _create_food_item(db_session, "Grapes", quantity=1.0, unit="bunch", emoji="🍇")
        recipe = await _create_recipe(db_session, "Grape Salad", [
            {"name": "grapes", "quantity": 1, "unit": "bunch", "category": "fruit"},
        ])

        await _create_meal_entry_and_sync(
            client, db_session, test_meal_slot_dinner.id,
            food_item_id=grapes.id, item_type="food_item",
        )
        await _create_meal_entry_and_sync(
            client, db_session, test_meal_slot_dinner.id,
            recipe_id=recipe.id, item_type="recipe",
        )

        tasks = await _get_auto_tasks(db_session, test_list.id)
        assert len(tasks) == 1, f"Expected 1 row, got {len(tasks)}: {[t.title for t in tasks]}"
        assert "2" in tasks[0].title
        assert "bunch" in tasks[0].title

    async def test_corn_incompatible_units_separate_rows(
        self, client, db_session, test_list, test_meal_slot_dinner, test_app_settings, test_family_member,
    ):
        """Corn food item (1 ear) + recipe '2 cups corn kernels' → TWO rows (incompatible units)."""
        await _link_shopping_list(db_session, test_app_settings, test_list.id)

        corn = await _create_food_item(db_session, "Corn", quantity=1.0, unit="ear", emoji="🌽")
        recipe = await _create_recipe(db_session, "Corn Chowder", [
            {"name": "corn kernels", "quantity": 2, "unit": "cup", "category": "vegetable"},
        ])

        await _create_meal_entry_and_sync(
            client, db_session, test_meal_slot_dinner.id,
            food_item_id=corn.id, item_type="food_item",
        )
        await _create_meal_entry_and_sync(
            client, db_session, test_meal_slot_dinner.id,
            recipe_id=recipe.id, item_type="recipe",
        )

        tasks = await _get_auto_tasks(db_session, test_list.id)
        # "corn" (ear/count) and "corn kernel" (cup/volume) are different canonical names + units
        assert len(tasks) == 2, f"Expected 2 rows, got {len(tasks)}: {[t.title for t in tasks]}"

    async def test_weight_conversion_lb_and_oz(
        self, client, db_session, test_list, test_meal_slot_dinner, test_app_settings, test_family_member,
    ):
        """Recipe 1 lb ground beef + recipe 16 oz ground beef → '2 lb ground beef'."""
        await _link_shopping_list(db_session, test_app_settings, test_list.id)

        recipe1 = await _create_recipe(db_session, "Burgers", [
            {"name": "ground beef", "quantity": 1, "unit": "lb", "category": "Protein"},
        ])
        recipe2 = await _create_recipe(db_session, "Tacos", [
            {"name": "ground beef", "quantity": 16, "unit": "oz", "category": "Protein"},
        ])

        await _create_meal_entry_and_sync(
            client, db_session, test_meal_slot_dinner.id,
            recipe_id=recipe1.id, item_type="recipe",
        )
        await _create_meal_entry_and_sync(
            client, db_session, test_meal_slot_dinner.id,
            recipe_id=recipe2.id, item_type="recipe",
        )

        tasks = await _get_auto_tasks(db_session, test_list.id)
        # Both are weight group → aggregate into single row
        weight_tasks = [t for t in tasks if t.aggregation_key_name == "ground beef"]
        assert len(weight_tasks) == 1, f"Expected 1 ground beef row, got {len(weight_tasks)}"

        task = weight_tasks[0]
        assert "2" in task.title
        assert "lb" in task.title

    async def test_pantry_staple_deduplicates(
        self, client, db_session, test_list, test_meal_slot_dinner, test_app_settings, test_family_member,
    ):
        """Olive oil (no quantity) added via two recipes → single row, name only."""
        await _link_shopping_list(db_session, test_app_settings, test_list.id)

        recipe1 = await _create_recipe(db_session, "Roast Chicken", [
            {"name": "olive oil", "quantity": 0, "unit": None, "category": "Pantry"},
        ])
        recipe2 = await _create_recipe(db_session, "Salad Dressing", [
            {"name": "olive oil", "quantity": 0, "unit": None, "category": "Pantry"},
        ])

        await _create_meal_entry_and_sync(
            client, db_session, test_meal_slot_dinner.id,
            recipe_id=recipe1.id, item_type="recipe",
        )
        await _create_meal_entry_and_sync(
            client, db_session, test_meal_slot_dinner.id,
            recipe_id=recipe2.id, item_type="recipe",
        )

        tasks = await _get_auto_tasks(db_session, test_list.id)
        olive_oil = [t for t in tasks if t.aggregation_key_name == "olive oil"]
        assert len(olive_oil) == 1, f"Expected 1 olive oil row, got {len(olive_oil)}"
        assert olive_oil[0].aggregation_unit is None
        assert olive_oil[0].title == "olive oil"


# =============================================================================
# 2. on_item_checked (check-flip)
# =============================================================================


class TestOnItemChecked:
    """Test that checking a mealboard_auto task flips it to manual."""

    async def test_check_flips_aggregation_source_to_null(
        self, client, db_session, test_list, test_meal_slot_dinner, test_app_settings, test_family_member,
    ):
        """Check an auto task → aggregation_source becomes NULL."""
        await _link_shopping_list(db_session, test_app_settings, test_list.id)

        recipe = await _create_recipe(db_session, "Simple Meal", [
            {"name": "chicken", "quantity": 1, "unit": "lb", "category": "Protein"},
        ])
        await _create_meal_entry_and_sync(
            client, db_session, test_meal_slot_dinner.id,
            recipe_id=recipe.id, item_type="recipe",
        )

        tasks = await _get_auto_tasks(db_session, test_list.id)
        assert len(tasks) == 1
        task_id = tasks[0].id

        # Check the task via API
        resp = await client.patch(f"/tasks/{task_id}", json={"completed": True})
        assert resp.status_code == 200

        # Verify aggregation_source is now NULL
        # No expire_all — use fresh queries below
        result = await db_session.execute(select(Task).where(Task.id == task_id))
        checked_task = result.scalar_one()
        assert checked_task.aggregation_source is None
        assert checked_task.completed is True

    async def test_new_auto_row_created_after_check(
        self, client, db_session, test_list, test_meal_slot_dinner, test_app_settings, test_family_member,
    ):
        """After check-flip, adding same ingredient again creates a new mealboard_auto row."""
        await _link_shopping_list(db_session, test_app_settings, test_list.id)

        recipe = await _create_recipe(db_session, "Pasta", [
            {"name": "garlic", "quantity": 3, "unit": "clove", "category": "Produce"},
        ])

        # Create + sync first meal entry
        await _create_meal_entry_and_sync(
            client, db_session, test_meal_slot_dinner.id,
            recipe_id=recipe.id, item_type="recipe",
        )

        tasks = await _get_auto_tasks(db_session, test_list.id)
        assert len(tasks) == 1
        first_task_id = tasks[0].id

        # Check the task (flips to manual)
        resp = await client.patch(f"/tasks/{first_task_id}", json={"completed": True})
        assert resp.status_code == 200

        # Create another meal entry with same ingredient + sync
        recipe2 = await _create_recipe(db_session, "Stir Fry", [
            {"name": "garlic", "quantity": 2, "unit": "clove", "category": "Produce"},
        ])
        await _create_meal_entry_and_sync(
            client, db_session, test_meal_slot_dinner.id,
            recipe_id=recipe2.id, item_type="recipe",
        )

        # Now there should be 2 tasks: 1 manual (checked) + 1 new auto
        all_tasks = await _get_all_tasks_on_list(db_session, test_list.id)
        garlic_tasks = [t for t in all_tasks if t.aggregation_key_name == "garlic"]
        assert len(garlic_tasks) == 2, f"Expected 2 garlic tasks, got {len(garlic_tasks)}"

        manual = [t for t in garlic_tasks if t.aggregation_source is None]
        auto = [t for t in garlic_tasks if t.aggregation_source == "mealboard_auto"]
        assert len(manual) == 1
        assert len(auto) == 1
        assert manual[0].completed is True
        assert auto[0].completed is False


# =============================================================================
# 3. swap_mealboard_list
# =============================================================================


class TestSwapMealboardList:
    """Test switching the linked shopping list moves auto rows."""

    async def test_swap_moves_auto_rows_to_new_list(
        self, client, db_session, test_meal_slot_dinner, test_app_settings, test_family_member,
    ):
        """Link list A, add meals → swap to list B → auto rows on B, not A."""
        from app.models import List as ListModel

        # Create two lists
        list_a = ListModel(name="Shopping A", color="#FF0000", icon="cart")
        list_b = ListModel(name="Shopping B", color="#00FF00", icon="cart")
        db_session.add(list_a)
        db_session.add(list_b)
        await db_session.commit()
        await db_session.refresh(list_a)
        await db_session.refresh(list_b)

        # Link list A
        await _link_shopping_list(db_session, test_app_settings, list_a.id)

        recipe = await _create_recipe(db_session, "Chicken Soup", [
            {"name": "chicken", "quantity": 2, "unit": "lb", "category": "Protein"},
            {"name": "carrots", "quantity": 3, "unit": "each", "category": "Produce"},
        ])
        await _create_meal_entry_and_sync(
            client, db_session, test_meal_slot_dinner.id,
            recipe_id=recipe.id, item_type="recipe",
        )

        # Verify items on list A
        tasks_a = await _get_auto_tasks(db_session, list_a.id)
        assert len(tasks_a) == 2

        # Swap to list B via app-settings PATCH
        resp = await client.patch("/app-settings/", json={"mealboard_shopping_list_id": list_b.id})
        assert resp.status_code == 200
        assert resp.json()["mealboard_shopping_list_id"] == list_b.id

        # Expire cached state
        # No expire_all — use fresh queries below

        # Auto rows should be on list B now, not list A
        tasks_a_after = await _get_auto_tasks(db_session, list_a.id)
        tasks_b_after = await _get_auto_tasks(db_session, list_b.id)
        assert len(tasks_a_after) == 0, f"Expected 0 auto tasks on A, got {len(tasks_a_after)}"
        assert len(tasks_b_after) == 2, f"Expected 2 auto tasks on B, got {len(tasks_b_after)}"

    async def test_swap_keeps_manual_checked_items_on_old_list(
        self, client, db_session, test_meal_slot_dinner, test_app_settings, test_family_member,
    ):
        """Manual (checked) items stay on old list after swap."""
        from app.models import List as ListModel

        list_a = ListModel(name="Shopping A", color="#FF0000", icon="cart")
        list_b = ListModel(name="Shopping B", color="#00FF00", icon="cart")
        db_session.add(list_a)
        db_session.add(list_b)
        await db_session.commit()
        await db_session.refresh(list_a)
        await db_session.refresh(list_b)

        await _link_shopping_list(db_session, test_app_settings, list_a.id)

        recipe = await _create_recipe(db_session, "Steak Dinner", [
            {"name": "steak", "quantity": 1, "unit": "lb", "category": "Protein"},
        ])
        await _create_meal_entry_and_sync(
            client, db_session, test_meal_slot_dinner.id,
            recipe_id=recipe.id, item_type="recipe",
        )

        # Check the task (flips to manual)
        tasks = await _get_auto_tasks(db_session, list_a.id)
        assert len(tasks) == 1
        resp = await client.patch(f"/tasks/{tasks[0].id}", json={"completed": True})
        assert resp.status_code == 200

        # Swap to list B
        resp = await client.patch("/app-settings/", json={"mealboard_shopping_list_id": list_b.id})
        assert resp.status_code == 200

        # No expire_all — use fresh queries below

        # Checked/manual task stays on list A
        all_a = await _get_all_tasks_on_list(db_session, list_a.id)
        assert len(all_a) == 1
        assert all_a[0].completed is True
        assert all_a[0].aggregation_source is None


# =============================================================================
# 4. unlink_mealboard_list
# =============================================================================


class TestUnlinkMealboardList:
    """Test setting mealboard_shopping_list_id=null cleans up."""

    async def test_unlink_deletes_auto_rows_and_skips_entries(
        self, client, db_session, test_list, test_meal_slot_dinner, test_app_settings, test_family_member,
    ):
        """PATCH settings list_id=null → auto rows deleted, meal entries marked skipped."""
        await _link_shopping_list(db_session, test_app_settings, test_list.id)

        recipe = await _create_recipe(db_session, "Fish Tacos", [
            {"name": "fish", "quantity": 1, "unit": "lb", "category": "Protein"},
            {"name": "tortillas", "quantity": 8, "unit": "each", "category": "Grain"},
        ])
        entry_id = await _create_meal_entry_and_sync(
            client, db_session, test_meal_slot_dinner.id,
            recipe_id=recipe.id, item_type="recipe",
        )

        # Verify auto rows exist
        tasks = await _get_auto_tasks(db_session, test_list.id)
        assert len(tasks) == 2

        # Unlink via PATCH (set to null)
        resp = await client.patch("/app-settings/", json={"mealboard_shopping_list_id": None})
        assert resp.status_code == 200
        assert resp.json()["mealboard_shopping_list_id"] is None

        # No expire_all — use fresh queries below

        # Auto rows should be deleted
        tasks_after = await _get_auto_tasks(db_session, test_list.id)
        assert len(tasks_after) == 0

        # Meal entry should be marked "skipped"
        result = await db_session.execute(
            select(MealEntry).where(MealEntry.id == entry_id)
        )
        entry = result.scalar_one()
        assert entry.shopping_sync_status == "skipped"
        assert entry.synced_to_list_id is None


# =============================================================================
# 5. Celery task guards
# =============================================================================


class TestCeleryTaskGuards:
    """Test sync guard logic: pending → synced, and no-op on re-sync."""

    async def test_meal_entry_gets_pending_status_on_create(
        self, client, db_session, test_list, test_meal_slot_dinner, test_app_settings, test_family_member,
    ):
        """Creating a meal entry via API sets status to 'pending'."""
        await _link_shopping_list(db_session, test_app_settings, test_list.id)

        recipe = await _create_recipe(db_session, "Quick Pasta", [
            {"name": "pasta", "quantity": 1, "unit": "lb", "category": "Grain"},
        ])

        resp = await client.post("/meal-entries/", json={
            "date": date.today().isoformat(),
            "meal_slot_type_id": test_meal_slot_dinner.id,
            "item_id": recipe.id,
        })
        assert resp.status_code == 201
        entry_id = resp.json()["id"]

        # Check status is "pending" (set by crud_meal_entries after dispatch)
        # No expire_all — use fresh queries below
        result = await db_session.execute(select(MealEntry).where(MealEntry.id == entry_id))
        entry = result.scalar_one()
        assert entry.shopping_sync_status == "pending"

    async def test_sync_sets_status_to_synced(
        self, client, db_session, test_list, test_meal_slot_dinner, test_app_settings, test_family_member,
    ):
        """Calling sync directly transitions pending → synced."""
        await _link_shopping_list(db_session, test_app_settings, test_list.id)

        recipe = await _create_recipe(db_session, "Soup", [
            {"name": "onion", "quantity": 1, "unit": "each", "category": "Produce"},
        ])

        resp = await client.post("/meal-entries/", json={
            "date": date.today().isoformat(),
            "meal_slot_type_id": test_meal_slot_dinner.id,
            "item_id": recipe.id,
        })
        entry_id = resp.json()["id"]

        # Call sync directly
        await sync_meal_to_shopping_list(db_session, entry_id)

        # No expire_all — use fresh queries below
        result = await db_session.execute(select(MealEntry).where(MealEntry.id == entry_id))
        entry = result.scalar_one()
        assert entry.shopping_sync_status == "synced"
        assert entry.synced_to_list_id == test_list.id

    async def test_sync_is_noop_when_already_synced(
        self, client, db_session, test_list, test_meal_slot_dinner, test_app_settings, test_family_member,
    ):
        """If status is already 'synced', sync is a no-op (no duplicate rows)."""
        await _link_shopping_list(db_session, test_app_settings, test_list.id)

        recipe = await _create_recipe(db_session, "Grilled Cheese", [
            {"name": "cheese", "quantity": 4, "unit": "oz", "category": "Dairy"},
            {"name": "bread", "quantity": 2, "unit": "slice", "category": "Grain"},
        ])

        entry_id = await _create_meal_entry_and_sync(
            client, db_session, test_meal_slot_dinner.id,
            recipe_id=recipe.id, item_type="recipe",
        )

        # Verify synced
        # No expire_all — use fresh queries below
        result = await db_session.execute(select(MealEntry).where(MealEntry.id == entry_id))
        entry = result.scalar_one()
        assert entry.shopping_sync_status == "synced"

        # Count tasks before second sync attempt
        tasks_before = await _get_auto_tasks(db_session, test_list.id)
        count_before = len(tasks_before)

        # Call sync again — should be a no-op because status is "synced"
        await sync_meal_to_shopping_list(db_session, entry_id)

        # No expire_all — use fresh queries below
        tasks_after = await _get_auto_tasks(db_session, test_list.id)
        assert len(tasks_after) == count_before, "Re-sync should not create duplicate rows"

    async def test_sync_skips_when_no_list_linked(
        self, client, db_session, test_meal_slot_dinner, test_app_settings, test_family_member,
    ):
        """If no shopping list is linked, sync marks entry as 'skipped'."""
        # Ensure no list is linked
        test_app_settings.mealboard_shopping_list_id = None
        await db_session.commit()

        recipe = await _create_recipe(db_session, "Toast", [
            {"name": "bread", "quantity": 2, "unit": "slice", "category": "Grain"},
        ])

        resp = await client.post("/meal-entries/", json={
            "date": date.today().isoformat(),
            "meal_slot_type_id": test_meal_slot_dinner.id,
            "item_id": recipe.id,
        })
        entry_id = resp.json()["id"]

        # Call sync — should mark as skipped
        await sync_meal_to_shopping_list(db_session, entry_id)

        # No expire_all — use fresh queries below
        result = await db_session.execute(select(MealEntry).where(MealEntry.id == entry_id))
        entry = result.scalar_one()
        assert entry.shopping_sync_status == "skipped"
        assert entry.synced_to_list_id is None
