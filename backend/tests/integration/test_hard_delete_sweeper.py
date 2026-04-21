"""Integration tests for the hourly hard-delete sweeper.

Covers Eng Review #3 Issue 3 — the cascade-in-code transaction pattern that
deletes soft-hidden meal_entries first, asserts there are no remaining active
rows, then deletes the expired items. The assertion gate fires loudly on a
soft-delete propagation bug rather than silently leaving orphan rows.

Tests call `crud_items.hard_delete_expired_soft_deletes_async()` directly
against the test session. The Celery task wrapper (`tasks.py`) is a thin
`run_async()` shell around the same helper and doesn't need separate coverage
— running it through Celery's broker would require a full worker in the test
environment, which isn't worth the complexity for a sync wrapper.
"""
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select


class TestHardDeleteSweeper:
    async def test_no_op_when_no_items_expired(self, db_session, test_recipe):
        """No soft-deleted items → helper returns zero counts, nothing removed."""
        from app.crud_items import hard_delete_expired_soft_deletes_async
        from app.models import Item

        counts = await hard_delete_expired_soft_deletes_async(db_session)
        assert counts == {"items_deleted": 0, "user_undo_entries_deleted": 0}

        # Fixture recipe is still intact
        item = (await db_session.execute(select(Item).where(Item.id == test_recipe.id))).scalar_one_or_none()
        assert item is not None

    async def test_sweeps_expired_recipe_with_hidden_meal_entries(
        self, db_session, test_recipe, test_meal_entry,
    ):
        """Happy path: item soft-deleted + meal entry cascade-hidden + past the
        24h window → sweep removes both in a single transaction."""
        from app.crud_items import hard_delete_expired_soft_deletes_async
        from app.models import Item, MealEntry

        now = datetime.utcnow()
        test_recipe.deleted_at = now - timedelta(hours=25)
        test_meal_entry.soft_hidden_at = now - timedelta(hours=25)
        await db_session.commit()
        recipe_id = test_recipe.id
        entry_id = test_meal_entry.id

        counts = await hard_delete_expired_soft_deletes_async(db_session)
        assert counts["items_deleted"] == 1

        assert (await db_session.execute(select(Item).where(Item.id == recipe_id))).scalar_one_or_none() is None
        assert (await db_session.execute(select(MealEntry).where(MealEntry.id == entry_id))).scalar_one_or_none() is None

    async def test_leaves_non_expired_items_alone(self, db_session, test_recipe):
        """Recently soft-deleted items (within 24h) must survive — only items
        past the window get hard-deleted."""
        from app.crud_items import hard_delete_expired_soft_deletes_async
        from app.models import Item

        test_recipe.deleted_at = datetime.utcnow() - timedelta(hours=1)
        await db_session.commit()

        counts = await hard_delete_expired_soft_deletes_async(db_session)
        assert counts["items_deleted"] == 0

        item = (await db_session.execute(select(Item).where(Item.id == test_recipe.id))).scalar_one_or_none()
        assert item is not None
        assert item.deleted_at is not None  # still soft-deleted

    async def test_assertion_gate_fires_on_active_meal_entry(
        self, db_session, test_recipe, test_meal_entry,
    ):
        """If an expired item still has an ACTIVE (non-soft-hidden) meal_entry,
        the sweeper raises RuntimeError and rolls back — Eng Review #3 Issue 3.
        Prevents silently leaving orphan rows when soft-delete propagation
        breaks."""
        from app.crud_items import hard_delete_expired_soft_deletes_async
        from app.models import Item

        # Item is expired but its meal_entry is still active (propagation bug)
        test_recipe.deleted_at = datetime.utcnow() - timedelta(hours=25)
        # Do NOT set test_meal_entry.soft_hidden_at — it stays NULL (active)
        await db_session.commit()
        recipe_id = test_recipe.id  # capture before the helper rolls back

        with pytest.raises(RuntimeError, match="active meal_entries still reference"):
            await hard_delete_expired_soft_deletes_async(db_session)

        # Transaction rolled back — item still exists
        item = (await db_session.execute(select(Item).where(Item.id == recipe_id))).scalar_one_or_none()
        assert item is not None

    async def test_sweeps_user_undo_rows_past_grace(
        self, db_session, test_recipe, test_meal_entry,
    ):
        """User-undo rows whose 15s grace window has expired get hard-deleted.

        Parent item is still alive (undo path is independent of cascade-hide),
        so only the entry row is removed."""
        from app.crud_items import hard_delete_expired_soft_deletes_async
        from app.models import MealEntry

        test_meal_entry.soft_hidden_at = datetime.utcnow() - timedelta(seconds=30)
        test_meal_entry.undo_token = "deadbeef" * 4
        await db_session.commit()
        entry_id = test_meal_entry.id

        counts = await hard_delete_expired_soft_deletes_async(db_session)
        assert counts["user_undo_entries_deleted"] == 1

        still_there = (await db_session.execute(
            select(MealEntry).where(MealEntry.id == entry_id)
        )).scalar_one_or_none()
        assert still_there is None

    async def test_leaves_user_undo_rows_within_grace(
        self, db_session, test_recipe, test_meal_entry,
    ):
        """A user-undo row that's still inside the 15s grace window survives
        the sweep — the user must keep their undo opportunity.

        Without this regression test, a too-aggressive sweeper would silently
        erase undo windows and we'd never notice."""
        from app.crud_items import hard_delete_expired_soft_deletes_async
        from app.models import MealEntry

        test_meal_entry.soft_hidden_at = datetime.utcnow() - timedelta(seconds=5)
        test_meal_entry.undo_token = "feedface" * 4
        await db_session.commit()
        entry_id = test_meal_entry.id

        counts = await hard_delete_expired_soft_deletes_async(db_session)
        assert counts["user_undo_entries_deleted"] == 0

        still_there = (await db_session.execute(
            select(MealEntry).where(MealEntry.id == entry_id)
        )).scalar_one_or_none()
        assert still_there is not None
