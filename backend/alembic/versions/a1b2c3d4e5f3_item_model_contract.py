"""item_model_contract — Revision 3 of the Unified Item Model refactor (CONTRACT phase).

Drops the old `recipes` and `food_items` tables (after archiving them as read-only
snapshots) and drops the `meal_entries.recipe_id` / `food_item_id` / `item_type`
shadow columns. Adds the `item_id IS NOT NULL OR custom_meal_name IS NOT NULL`
check constraint to enforce the new invariant.

Pre-deploy gates (see plan §0.2 Rev 3 + §0.6):
    1. Rev 1 and Rev 2 have soaked for ≥24h each in production.
    2. Dual-write drift audit has ≥24 consecutive clean runs.
    3. pre-drop audit of meal_entries.item_type readers is complete.
    4. pg_dump backup of production is in hand and verified via disposable-clone restore.
    5. Celery workers + beat stopped before running upgrade().

Downgrade posture: lossy — items created post-Rev-3 with no instructions populated
round-trip through `COALESCE(instructions, '')` to satisfy the legacy NOT NULL constraint
(Eng Review #3 Issue 5). Rollback to Rev 2 recreates the old tables and shadow columns
but production break-glass should prefer a fresh pg_dump restore.

Revision ID: a1b2c3d4e5f3
Revises: a1b2c3d4e5f2
Create Date: 2026-04-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f3'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """CONTRACT: archive old tables, drop shadow columns, drop old tables."""
    op.execute("LOCK TABLE recipes IN ACCESS EXCLUSIVE MODE")
    op.execute("LOCK TABLE food_items IN ACCESS EXCLUSIVE MODE")
    op.execute("LOCK TABLE meal_entries IN ACCESS EXCLUSIVE MODE")

    bind = op.get_bind()

    # -------------------------------------------------------------------------
    # Phase 0: Pre-flight orphan audit for the new NOT-NULL-OR check constraint
    # -------------------------------------------------------------------------
    # The new `item_id IS NOT NULL OR custom_meal_name IS NOT NULL` check would
    # fail to create if any meal_entry is currently orphaned (no item_id AND
    # no custom_meal_name). This can happen with leftover test data, partial
    # restores, or a prior bug that dropped a recipe without soft-hiding its
    # meal entries. Detect it here with a clear message, matching the
    # duplicate-name audit pattern from Rev 1.
    orphans = bind.execute(sa.text("""
        SELECT id, date, item_type
        FROM meal_entries
        WHERE item_id IS NULL
          AND (custom_meal_name IS NULL OR custom_meal_name = '')
    """)).fetchall()
    if orphans:
        details = "; ".join(f"id={r[0]} date={r[1]} item_type={r[2]}" for r in orphans[:10])
        more = f" ({len(orphans) - 10} more)" if len(orphans) > 10 else ""
        raise RuntimeError(
            f"Cannot contract meal_entries: {len(orphans)} orphan row(s) violate the "
            f"new `item_id IS NOT NULL OR custom_meal_name IS NOT NULL` invariant. "
            f"Either delete these rows or set a custom_meal_name before retrying. "
            f"Orphans: {details}{more}"
        )

    # -------------------------------------------------------------------------
    # Phase 1: Archive the legacy tables (Eng Review #2 Low fix)
    # -------------------------------------------------------------------------
    # Read-only safety nets for the 30-day window after Rev 3 ships. If a post-Rev-3
    # schema bug surfaces, we can recover from these in seconds without restoring from
    # pg_dump (which is a multi-minute outage with full DB replacement). Cleanup ships
    # as Rev 4 (or a follow-up Alembic revision) ~30 days after Rev 3 promotes cleanly.
    #
    # DROP IF EXISTS guards against re-upgrade after a downgrade: Rev 3's downgrade
    # deliberately leaves the archives in place (they're data snapshots, not schema
    # state), so a subsequent re-upgrade would collide on CREATE TABLE. In a real
    # rollback-and-retry scenario, a fresh snapshot is the right behavior anyway.
    op.execute("DROP TABLE IF EXISTS recipes_archived CASCADE")
    op.execute("DROP TABLE IF EXISTS food_items_archived CASCADE")
    op.execute("CREATE TABLE recipes_archived AS SELECT * FROM recipes")
    op.execute("CREATE TABLE food_items_archived AS SELECT * FROM food_items")
    op.execute("REVOKE INSERT, UPDATE, DELETE ON recipes_archived FROM PUBLIC")
    op.execute("REVOKE INSERT, UPDATE, DELETE ON food_items_archived FROM PUBLIC")
    op.execute(
        "COMMENT ON TABLE recipes_archived IS "
        "'Frozen pre-Rev-3 snapshot. Drop after 30-day soak (Rev 4).'"
    )
    op.execute(
        "COMMENT ON TABLE food_items_archived IS "
        "'Frozen pre-Rev-3 snapshot. Drop after 30-day soak (Rev 4).'"
    )

    # -------------------------------------------------------------------------
    # Phase 2: Drop shadow columns from meal_entries
    # -------------------------------------------------------------------------
    # NB: The meal_entries.item_type column audit (pre-migration gate 3) must be
    # complete before this runs — any remaining reader will crash post-Rev-3.
    #
    # NOTE: the FK constraint names come from inspection of the live DB, not the
    # plan's assumed names. The `recipes`-side FK is `meal_entries_recipe_id_fkey`
    # (autogenerated by an earlier Alembic revision), but the `food_items`-side FK
    # is `fk_meal_entries_food_item` (hand-named in a prior migration). The downgrade
    # below recreates them with the same names so upgrade-after-downgrade still works.
    op.drop_constraint('meal_entries_recipe_id_fkey', 'meal_entries', type_='foreignkey')
    op.drop_constraint('fk_meal_entries_food_item', 'meal_entries', type_='foreignkey')
    op.drop_column('meal_entries', 'recipe_id')
    op.drop_column('meal_entries', 'food_item_id')
    op.drop_column('meal_entries', 'item_type')

    # -------------------------------------------------------------------------
    # Phase 3: Enforce the new invariant on meal_entries
    # -------------------------------------------------------------------------
    # Every meal_entry must have either an item_id (referring to a real Item) OR a
    # custom_meal_name (one-off ad-hoc meal). This replaces the old
    # `(recipe_id IS NOT NULL) XOR (food_item_id IS NOT NULL) XOR (item_type='custom')`
    # invariant that was enforced in application code.
    op.create_check_constraint(
        'meal_entries_item_or_custom_check',
        'meal_entries',
        'item_id IS NOT NULL OR custom_meal_name IS NOT NULL',
    )

    # -------------------------------------------------------------------------
    # Phase 4: Drop old tables
    # -------------------------------------------------------------------------
    op.drop_table('recipes')
    op.drop_table('food_items')


def downgrade() -> None:
    """Lossy downgrade from Revision 3 back to the Revision 2 dual-schema state.

    This recreates the old tables and shadow columns so Rev-2-era code can run again,
    but production break-glass recovery should still prefer restoring the verified
    pre-Rev-3 backup. The archived tables created during upgrade() exist for forensic
    comparison and targeted data recovery during the soak window, not as a hot online
    rollback path.

    Eng Review #3 Issue 5: the legacy `recipes.instructions` column is NOT NULL, but
    `recipe_details.instructions` is nullable in the new schema. Items created post-
    refactor with no instructions populated would violate the NOT NULL constraint on
    the lossy downgrade INSERT and abort the break-glass restore. COALESCE to empty
    string instead.
    """
    op.execute("LOCK TABLE meal_entries IN ACCESS EXCLUSIVE MODE")

    # -------------------------------------------------------------------------
    # Phase 1: Recreate the old tables (schemas must match the pre-Rev-1 state)
    # -------------------------------------------------------------------------
    op.create_table(
        'recipes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('ingredients', postgresql.JSONB(), nullable=True),
        sa.Column('instructions', sa.Text(), nullable=False),
        sa.Column('prep_time_minutes', sa.Integer(), nullable=True),
        sa.Column('cook_time_minutes', sa.Integer(), nullable=True),
        sa.Column('servings', sa.Integer(), nullable=True),
        sa.Column('image_url', sa.Text(), nullable=True),
        sa.Column('is_favorite', sa.Boolean(), nullable=True),
        sa.Column('tags', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
    )
    op.create_index('ix_recipes_name', 'recipes', ['name'])

    op.create_table(
        'food_items',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('emoji', sa.Text(), nullable=True),
        sa.Column('category', sa.Text(), nullable=True),
        sa.Column('is_favorite', sa.Boolean(), nullable=True),
        sa.Column('shopping_quantity', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('shopping_unit', sa.Text(), nullable=False, server_default='each'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
    )
    op.create_index('ix_food_items_name', 'food_items', ['name'], unique=True)

    # -------------------------------------------------------------------------
    # Phase 2: Backfill old tables from the new items + details tables
    # -------------------------------------------------------------------------
    # COALESCE(rd.instructions, '') satisfies the legacy NOT NULL constraint.
    op.execute("""
        INSERT INTO recipes (
            id, name, description, ingredients, instructions, prep_time_minutes,
            cook_time_minutes, servings, image_url, tags, is_favorite, created_at, updated_at
        )
        SELECT
            i.id,
            i.name,
            rd.description,
            rd.ingredients,
            COALESCE(rd.instructions, ''),
            rd.prep_time_minutes,
            rd.cook_time_minutes,
            rd.servings,
            rd.image_url,
            i.tags,
            i.is_favorite,
            i.created_at,
            i.updated_at
        FROM items i
        JOIN recipe_details rd ON rd.item_id = i.id
        WHERE i.item_type = 'recipe' AND i.deleted_at IS NULL
    """)
    op.execute("""
        INSERT INTO food_items (
            id, name, emoji, category, is_favorite, shopping_quantity, shopping_unit,
            created_at, updated_at
        )
        SELECT
            i.id,
            i.name,
            i.icon_emoji,
            fd.category,
            i.is_favorite,
            fd.shopping_quantity,
            fd.shopping_unit,
            i.created_at,
            i.updated_at
        FROM items i
        JOIN food_item_details fd ON fd.item_id = i.id
        WHERE i.item_type = 'food_item' AND i.deleted_at IS NULL
    """)

    # -------------------------------------------------------------------------
    # Phase 3: Drop the check constraint before re-adding the shadow columns
    # -------------------------------------------------------------------------
    op.drop_constraint('meal_entries_item_or_custom_check', 'meal_entries', type_='check')

    # -------------------------------------------------------------------------
    # Phase 4: Recreate meal_entries shadow columns
    # -------------------------------------------------------------------------
    op.add_column('meal_entries', sa.Column('recipe_id', sa.Integer(), nullable=True))
    op.add_column('meal_entries', sa.Column('food_item_id', sa.Integer(), nullable=True))
    op.add_column('meal_entries', sa.Column('item_type', sa.Text(), nullable=True))
    op.create_foreign_key(
        'meal_entries_recipe_id_fkey', 'meal_entries', 'recipes',
        ['recipe_id'], ['id'], ondelete='SET NULL',
    )
    op.create_foreign_key(
        'fk_meal_entries_food_item', 'meal_entries', 'food_items',
        ['food_item_id'], ['id'], ondelete='SET NULL',
    )

    # -------------------------------------------------------------------------
    # Phase 5: Backfill the old columns from item_id + items.item_type
    # -------------------------------------------------------------------------
    op.execute("""
        UPDATE meal_entries SET recipe_id = item_id, item_type = 'recipe'
        FROM items
        WHERE meal_entries.item_id = items.id AND items.item_type = 'recipe'
    """)
    op.execute("""
        UPDATE meal_entries SET food_item_id = item_id, item_type = 'food_item'
        FROM items
        WHERE meal_entries.item_id = items.id AND items.item_type = 'food_item'
    """)
    # Custom meals keep item_type = 'custom' (no item_id reference)
    op.execute("""
        UPDATE meal_entries SET item_type = 'custom'
        WHERE item_id IS NULL AND custom_meal_name IS NOT NULL
    """)

    # NB: meal_entries.item_type is re-declared as nullable here because the downgrade
    # can't enforce NOT NULL until after the backfill completes. If a stricter invariant
    # is needed in the Rev 2 dual-schema state, it can be enforced in application code.
