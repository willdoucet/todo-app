"""item_model_expand — Revision 1 of the Unified Item Model refactor (EXPAND phase).

Creates the new `items`, `recipe_details`, and `food_item_details` tables; backfills
from the existing `recipes` and `food_items` tables; adds a shadow `meal_entries.item_id`
column with a RESTRICT FK to items; and rewrites `Task.source_meals` JSON payloads to
use `item_id` instead of `recipe_id` / `food_item_id`. The old tables remain live for
the duration of the dual-write window (Rev 1 + Rev 2).

Pre-migration gates (see plan §0.2 lines 222-229):
    1. Run this migration against a pg_dump snapshot locally first.
    2. Verify pg_dump restore works on a disposable clone.
    3. Audit all readers of `meal_entries.item_type` column.
    4. Audit hardcoded recipe/food_item IDs.
    5. Stop Celery workers + beat BEFORE running upgrade() (ACCESS EXCLUSIVE locks).

Revision ID: a1b2c3d4e5f1
Revises: c0fab9bfd27a
Create Date: 2026-04-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f1'
down_revision: Union[str, Sequence[str], None] = 'c0fab9bfd27a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """EXPAND: create new schema, backfill, add shadow FK column, rewrite Task.source_meals."""
    bind = op.get_bind()

    # Acquire exclusive locks up front to prevent concurrent writes racing the backfill.
    # Stop Celery workers + beat before running this migration (pre-migration gate 5).
    op.execute("LOCK TABLE recipes IN ACCESS EXCLUSIVE MODE")
    op.execute("LOCK TABLE food_items IN ACCESS EXCLUSIVE MODE")
    op.execute("LOCK TABLE meal_entries IN ACCESS EXCLUSIVE MODE")
    op.execute("LOCK TABLE tasks IN ACCESS EXCLUSIVE MODE")  # Phase 6 rewrites Task.source_meals

    # Capture the food_item ID offset ONCE and bind it into every phase that needs it.
    # The earlier draft reconstructed the offset inside each SQL statement via
    # MAX(items.id) - COUNT(*) FILTER (...), which is only correct when food_items.id is dense
    # (no gaps). Production almost always has gaps from past deletes, so the reconstruction
    # silently overshoots and corrupts FK references. The dev DB already shows recipes
    # max=8 / count=7, so the bug would fire on day one. See Eng Review #2 (2026-04-13).
    food_id_offset = bind.execute(
        sa.text("SELECT COALESCE(MAX(id), 0) FROM recipes")
    ).scalar() or 0

    # -------------------------------------------------------------------------
    # Phase 0: Pre-flight duplicate-name audit
    # -------------------------------------------------------------------------
    # The new partial UNIQUE(name, item_type) index didn't exist on recipes before.
    # If recipes or food_items have duplicate names today, the index creation later in
    # this migration will fail with an obscure error. Detect it here with a clear message.
    duplicates = bind.execute(sa.text("""
        SELECT 'recipe' AS type, name, COUNT(*) AS cnt FROM recipes GROUP BY name HAVING COUNT(*) > 1
        UNION ALL
        SELECT 'food_item' AS type, name, COUNT(*) AS cnt FROM food_items GROUP BY name HAVING COUNT(*) > 1
    """)).fetchall()
    if duplicates:
        details = "; ".join(f"{t}: '{n}' ({c}x)" for t, n, c in duplicates)
        raise RuntimeError(
            f"Cannot migrate: duplicate names found that violate the new "
            f"UNIQUE(name, item_type) constraint. Resolve (rename or merge) these rows "
            f"before retrying: {details}"
        )

    # -------------------------------------------------------------------------
    # Phase 1: Create new tables + constraints + indexes + triggers
    # -------------------------------------------------------------------------
    op.create_table(
        'items',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('item_type', sa.Text(), nullable=False),
        sa.Column('icon_emoji', sa.Text(), nullable=True),
        sa.Column('icon_url', sa.Text(), nullable=True),
        sa.Column('tags', postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column('is_favorite', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('deleted_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.func.now()),
    )
    op.create_check_constraint(
        'items_item_type_check', 'items', "item_type IN ('recipe', 'food_item')"
    )
    op.create_check_constraint(
        'items_icon_xor_check', 'items',
        'NOT (icon_emoji IS NOT NULL AND icon_url IS NOT NULL)'
    )
    op.create_index('items_item_type_idx', 'items', ['item_type'])
    op.create_index(
        'items_is_favorite_idx', 'items', ['is_favorite'],
        postgresql_where=sa.text('is_favorite = true'),
    )
    op.create_index(
        'items_deleted_at_idx', 'items', ['deleted_at'],
        postgresql_where=sa.text('deleted_at IS NOT NULL'),
    )
    op.create_index(
        'items_name_type_uniq', 'items', ['name', 'item_type'],
        unique=True, postgresql_where=sa.text('deleted_at IS NULL'),
    )

    op.create_table(
        'recipe_details',
        sa.Column('item_id', sa.Integer(),
                  sa.ForeignKey('items.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('ingredients', postgresql.JSONB(), nullable=False,
                  server_default=sa.text("'[]'::jsonb")),
        sa.Column('instructions', sa.Text(), nullable=True),
        sa.Column('prep_time_minutes', sa.Integer(), nullable=True),
        sa.Column('cook_time_minutes', sa.Integer(), nullable=True),
        sa.Column('servings', sa.Integer(), nullable=True),
        sa.Column('image_url', sa.Text(), nullable=True),
    )
    op.create_index(
        'recipe_details_ingredients_gin', 'recipe_details', ['ingredients'],
        postgresql_using='gin',
    )

    op.create_table(
        'food_item_details',
        sa.Column('item_id', sa.Integer(),
                  sa.ForeignKey('items.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('category', sa.Text(), nullable=False, server_default='Other'),
        sa.Column('shopping_quantity', sa.Numeric(), nullable=False, server_default='1.0'),
        sa.Column('shopping_unit', sa.Text(), nullable=False, server_default='each'),
    )

    # updated_at propagation trigger: changes to recipe_details or food_item_details
    # bump items.updated_at so cache invalidation keyed on items.updated_at stays correct.
    op.execute("""
        CREATE OR REPLACE FUNCTION bump_item_updated_at() RETURNS TRIGGER AS $$
        BEGIN
            UPDATE items SET updated_at = now() WHERE id = COALESCE(NEW.item_id, OLD.item_id);
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER recipe_details_bump_parent
            AFTER INSERT OR UPDATE OR DELETE ON recipe_details
            FOR EACH ROW EXECUTE FUNCTION bump_item_updated_at();
    """)
    op.execute("""
        CREATE TRIGGER food_item_details_bump_parent
            AFTER INSERT OR UPDATE OR DELETE ON food_item_details
            FOR EACH ROW EXECUTE FUNCTION bump_item_updated_at();
    """)

    # -------------------------------------------------------------------------
    # Phase 2: Backfill items + recipe_details from existing recipes
    # -------------------------------------------------------------------------
    op.execute("""
        INSERT INTO items (id, name, item_type, icon_emoji, icon_url, tags, is_favorite, created_at, updated_at)
        SELECT
            id,
            name,
            'recipe',
            NULL,
            NULL,
            COALESCE(
                CASE
                    WHEN tags IS NULL THEN '[]'::jsonb
                    WHEN jsonb_typeof(tags::jsonb) = 'array' THEN tags::jsonb
                    ELSE '[]'::jsonb
                END,
                '[]'::jsonb
            ),
            COALESCE(is_favorite, false),
            created_at,
            COALESCE(updated_at, created_at)
        FROM recipes
    """)
    op.execute("""
        INSERT INTO recipe_details (item_id, description, ingredients, instructions, prep_time_minutes, cook_time_minutes, servings, image_url)
        SELECT
            id,
            description,
            COALESCE(
                CASE
                    WHEN ingredients IS NULL THEN '[]'::jsonb
                    WHEN jsonb_typeof(ingredients::jsonb) = 'array' THEN ingredients::jsonb
                    ELSE '[]'::jsonb
                END,
                '[]'::jsonb
            ),
            NULLIF(instructions, ''),
            prep_time_minutes,
            cook_time_minutes,
            servings,
            image_url
        FROM recipes
    """)

    # -------------------------------------------------------------------------
    # Phase 3: Backfill items + food_item_details from existing food_items
    # -------------------------------------------------------------------------
    # food_id_offset is captured once above (Eng Review #2 fix). NOTE: current food_items
    # column is `emoji`, NOT `icon_emoji` (verified against backend/app/models.py:224).
    op.execute(
        sa.text("""
            INSERT INTO items (id, name, item_type, icon_emoji, icon_url, tags, is_favorite, created_at, updated_at)
            SELECT
                f.id + :food_id_offset,
                f.name,
                'food_item',
                NULLIF(f.emoji, ''),
                NULL,
                '[]'::jsonb,
                COALESCE(f.is_favorite, false),
                f.created_at,
                COALESCE(f.updated_at, f.created_at)
            FROM food_items f
        """).bindparams(food_id_offset=food_id_offset)
    )
    op.execute(
        sa.text("""
            INSERT INTO food_item_details (item_id, category, shopping_quantity, shopping_unit)
            SELECT
                f.id + :food_id_offset,
                COALESCE(NULLIF(f.category, ''), 'Other'),
                COALESCE(f.shopping_quantity, 1.0),
                COALESCE(NULLIF(f.shopping_unit, ''), 'each')
            FROM food_items f
        """).bindparams(food_id_offset=food_id_offset)
    )

    # -------------------------------------------------------------------------
    # Phase 4: Resync the items sequence using pg_get_serial_sequence
    # -------------------------------------------------------------------------
    # Never hardcode 'items_id_seq' — use pg_get_serial_sequence so Alembic-renamed
    # sequences still work. See adversarial review dimension 7.
    op.execute("""
        SELECT setval(
            pg_get_serial_sequence('items', 'id'),
            (SELECT COALESCE(MAX(id), 1) FROM items)
        )
    """)

    # -------------------------------------------------------------------------
    # Phase 5: Add item_id shadow column to meal_entries and backfill
    # -------------------------------------------------------------------------
    # DO NOT drop recipe_id/food_item_id yet — Revision 3 drops them after the
    # dual-write window has validated correctness.
    op.add_column('meal_entries', sa.Column('item_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'meal_entries_item_id_fkey', 'meal_entries', 'items',
        ['item_id'], ['id'],
        ondelete='RESTRICT',  # Soft-delete is the supported deletion path. RESTRICT
                              # makes a direct DELETE FROM items fail loudly with an FK
                              # violation instead of silently wiping meal history.
    )
    op.create_index('meal_entries_item_id_idx', 'meal_entries', ['item_id'])

    # Add soft_hidden_at for Expansion B (soft-delete + undo toast). See plan line 203.
    op.add_column(
        'meal_entries', sa.Column('soft_hidden_at', sa.TIMESTAMP(), nullable=True)
    )
    op.create_index(
        'meal_entries_soft_hidden_at_idx', 'meal_entries', ['soft_hidden_at'],
        postgresql_where=sa.text('soft_hidden_at IS NOT NULL'),
    )

    # Backfill meal_entries.item_id from the old columns using the same captured ID offset.
    op.execute("""
        UPDATE meal_entries SET item_id = recipe_id WHERE recipe_id IS NOT NULL
    """)
    op.execute(
        sa.text("""
            UPDATE meal_entries
            SET item_id = food_item_id + :food_id_offset
            WHERE food_item_id IS NOT NULL
        """).bindparams(food_id_offset=food_id_offset)
    )

    # -------------------------------------------------------------------------
    # Phase 6: Rewrite Task.source_meals JSON to use item_id
    # -------------------------------------------------------------------------
    # shopping_sync.py stores source tracking as JSON inside Task.source_meals with
    # embedded recipe_id and food_item_id fields. Post-refactor these stale field names
    # reference tables that will no longer exist (post-Rev-3) and the food_item_id
    # values don't match the new offset-adjusted item IDs. Rewrite each entry atomically:
    #   {recipe_id: 7, food_item_id: null, source_kind: 'recipe_ingredient', ...}
    #     -> {item_id: 7, source_kind: 'recipe_ingredient', ...}
    #   {recipe_id: null, food_item_id: 3, source_kind: 'food_item', ...}
    #     -> {item_id: 3 + offset, source_kind: 'food_item', ...}
    #
    # NOTE: tasks.source_meals is typed as `json` in the existing schema (not jsonb —
    # see backend/app/models.py:111). The `jsonb_typeof()`, `jsonb_array_elements()`,
    # and `-` operators require jsonb, so we cast `source_meals::jsonb` everywhere.
    # SQLAlchemy's JSON column will accept a jsonb value assignment transparently.
    op.execute(
        sa.text("""
            UPDATE tasks
            SET source_meals = (
                SELECT jsonb_agg(
                    CASE
                        WHEN entry->>'source_kind' = 'recipe_ingredient' THEN
                            jsonb_build_object(
                                'meal_entry_id', entry->'meal_entry_id',
                                'source_kind', entry->>'source_kind',
                                'item_id', entry->'recipe_id'
                            ) || COALESCE(entry - 'recipe_id' - 'food_item_id' - 'meal_entry_id' - 'source_kind', '{}'::jsonb)
                        WHEN entry->>'source_kind' = 'food_item' THEN
                            jsonb_build_object(
                                'meal_entry_id', entry->'meal_entry_id',
                                'source_kind', entry->>'source_kind',
                                'item_id', to_jsonb((entry->>'food_item_id')::int + :food_id_offset)
                            ) || COALESCE(entry - 'recipe_id' - 'food_item_id' - 'meal_entry_id' - 'source_kind', '{}'::jsonb)
                        ELSE entry
                    END
                )
                FROM jsonb_array_elements(source_meals::jsonb) AS entry
            )
            WHERE source_meals IS NOT NULL AND jsonb_typeof(source_meals::jsonb) = 'array'
        """).bindparams(food_id_offset=food_id_offset)
    )

    # Phase 7 marker: after this migration, the application code MUST ship the
    # corresponding dual-write updates (see plan §0.3 Backend Refactor). Dual-write
    # to both schemas is active until Revision 3 drops the old tables.


def downgrade() -> None:
    """Full, round-trippable downgrade.

    NOT lossy during Revision 1 because the old tables and columns are still intact.
    Items created post-Revision-1 in the new schema that don't have corresponding rows
    in the old tables WILL be lost by this downgrade — which is acceptable because
    dual-write means they should exist in both schemas.
    """
    op.execute("LOCK TABLE recipes IN ACCESS EXCLUSIVE MODE")
    op.execute("LOCK TABLE food_items IN ACCESS EXCLUSIVE MODE")
    op.execute("LOCK TABLE meal_entries IN ACCESS EXCLUSIVE MODE")
    op.execute("LOCK TABLE tasks IN ACCESS EXCLUSIVE MODE")

    food_id_offset = op.get_bind().execute(
        sa.text("SELECT COALESCE(MAX(id), 0) FROM recipes")
    ).scalar() or 0

    # Reverse Phase 6 before dropping the new-schema-only references. Pre-refactor
    # shopping-sync code expects legacy `recipe_id` / `food_item_id` keys inside
    # Task.source_meals. Leaving `item_id` would make the schema look rolled back
    # while the JSON payload shape silently stayed on the new contract.
    # Cast source_meals::jsonb because the column type is json, not jsonb.
    op.execute(
        sa.text("""
            UPDATE tasks
            SET source_meals = (
                SELECT jsonb_agg(
                    CASE
                        WHEN entry->>'source_kind' = 'recipe_ingredient' AND entry ? 'item_id' THEN
                            jsonb_build_object(
                                'meal_entry_id', entry->'meal_entry_id',
                                'source_kind', entry->>'source_kind',
                                'recipe_id', entry->'item_id',
                                'food_item_id', to_jsonb(NULL::int)
                            ) || COALESCE(entry - 'item_id' - 'meal_entry_id' - 'source_kind', '{}'::jsonb)
                        WHEN entry->>'source_kind' = 'food_item' AND entry ? 'item_id' THEN
                            jsonb_build_object(
                                'meal_entry_id', entry->'meal_entry_id',
                                'source_kind', entry->>'source_kind',
                                'recipe_id', to_jsonb(NULL::int),
                                'food_item_id', to_jsonb((entry->>'item_id')::int - :food_id_offset)
                            ) || COALESCE(entry - 'item_id' - 'meal_entry_id' - 'source_kind', '{}'::jsonb)
                        ELSE entry
                    END
                )
                FROM jsonb_array_elements(source_meals::jsonb) AS entry
            )
            WHERE source_meals IS NOT NULL AND jsonb_typeof(source_meals::jsonb) = 'array'
        """).bindparams(food_id_offset=food_id_offset)
    )

    op.drop_index('meal_entries_soft_hidden_at_idx', table_name='meal_entries')
    op.drop_column('meal_entries', 'soft_hidden_at')

    op.drop_index('meal_entries_item_id_idx', table_name='meal_entries')
    op.drop_constraint('meal_entries_item_id_fkey', 'meal_entries', type_='foreignkey')
    op.drop_column('meal_entries', 'item_id')

    op.execute("DROP TRIGGER IF EXISTS food_item_details_bump_parent ON food_item_details")
    op.execute("DROP TRIGGER IF EXISTS recipe_details_bump_parent ON recipe_details")
    op.execute("DROP FUNCTION IF EXISTS bump_item_updated_at()")

    op.drop_index('recipe_details_ingredients_gin', table_name='recipe_details')
    op.drop_table('food_item_details')
    op.drop_table('recipe_details')

    op.drop_index('items_name_type_uniq', table_name='items')
    op.drop_index('items_deleted_at_idx', table_name='items')
    op.drop_index('items_is_favorite_idx', table_name='items')
    op.drop_index('items_item_type_idx', table_name='items')
    op.drop_table('items')
