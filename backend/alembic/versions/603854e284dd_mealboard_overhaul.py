"""mealboard_overhaul

Revision ID: 603854e284dd
Revises: 4d4afd73e72a
Create Date: 2026-04-03

HAND-WRITTEN MIGRATION — do not autogenerate.
This migration:
  1. Creates meal_slot_types table with 4 default rows
  2. Creates food_items table
  3. Adds new columns to meal_plans
  4. Migrates existing category enum values to meal_slot_type_id
  5. Renames meal_plans → meal_entries
  6. Drops category column and mealcategory enum
  7. Creates meal_entry_participants junction table
  8. Adds aggregation fields + unique constraint to tasks
  9. Adds mealboard settings columns to app_settings
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '603854e284dd'
down_revision: Union[str, None] = '4d4afd73e72a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Create meal_slot_types table ──
    op.create_table(
        'meal_slot_types',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('color', sa.String(), nullable=True),
        sa.Column('icon', sa.String(), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('default_participants', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_meal_slot_types_id', 'meal_slot_types', ['id'])

    # Seed 4 default slot types
    meal_slot_types = sa.table(
        'meal_slot_types',
        sa.column('name', sa.String),
        sa.column('sort_order', sa.Integer),
        sa.column('color', sa.String),
        sa.column('icon', sa.String),
        sa.column('is_default', sa.Boolean),
        sa.column('is_active', sa.Boolean),
        sa.column('default_participants', sa.JSON),
    )
    op.bulk_insert(meal_slot_types, [
        {'name': 'Breakfast', 'sort_order': 1, 'color': '#F5A623', 'icon': '☀', 'is_default': True, 'is_active': True, 'default_participants': []},
        {'name': 'Lunch', 'sort_order': 2, 'color': '#6B8F71', 'icon': '🥪', 'is_default': True, 'is_active': True, 'default_participants': []},
        {'name': 'Dinner', 'sort_order': 3, 'color': '#E8927C', 'icon': '🍽', 'is_default': True, 'is_active': True, 'default_participants': []},
        {'name': 'Snack', 'sort_order': 4, 'color': '#B8A9C9', 'icon': '🍌', 'is_default': True, 'is_active': True, 'default_participants': []},
    ])

    # ── 2. Create food_items table ──
    op.create_table(
        'food_items',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('emoji', sa.String(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('is_favorite', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_food_items_id', 'food_items', ['id'])
    op.create_index('ix_food_items_name', 'food_items', ['name'], unique=True)

    # ── 3. Add new columns to meal_plans (before rename) ──
    op.add_column('meal_plans', sa.Column('meal_slot_type_id', sa.Integer(), nullable=True))
    op.add_column('meal_plans', sa.Column('food_item_id', sa.Integer(), nullable=True))
    op.add_column('meal_plans', sa.Column('item_type', sa.String(), nullable=True))
    op.add_column('meal_plans', sa.Column('servings', sa.Integer(), nullable=True))
    op.add_column('meal_plans', sa.Column('sort_order', sa.Integer(), server_default='0', nullable=False))
    op.add_column('meal_plans', sa.Column('shopping_sync_status', sa.String(), nullable=True))

    # ── 4. Migrate existing data ──
    # Map category enum → meal_slot_type_id
    op.execute("""
        UPDATE meal_plans SET meal_slot_type_id = CASE
            WHEN category = 'BREAKFAST' THEN (SELECT id FROM meal_slot_types WHERE name = 'Breakfast')
            WHEN category = 'LUNCH' THEN (SELECT id FROM meal_slot_types WHERE name = 'Lunch')
            WHEN category = 'DINNER' THEN (SELECT id FROM meal_slot_types WHERE name = 'Dinner')
        END
    """)

    # Set item_type based on recipe_id presence
    op.execute("""
        UPDATE meal_plans SET item_type = CASE
            WHEN recipe_id IS NOT NULL THEN 'recipe'
            ELSE 'custom'
        END
    """)

    # Make migrated columns NOT NULL now that data is populated
    op.alter_column('meal_plans', 'meal_slot_type_id', nullable=False)
    op.alter_column('meal_plans', 'item_type', nullable=False)

    # Add FK for meal_slot_type_id
    op.create_foreign_key(
        'fk_meal_plans_slot_type', 'meal_plans', 'meal_slot_types',
        ['meal_slot_type_id'], ['id'], ondelete='RESTRICT'
    )

    # ── 5. Rename meal_plans → meal_entries ──
    op.rename_table('meal_plans', 'meal_entries')
    op.execute("ALTER SEQUENCE meal_plans_id_seq RENAME TO meal_entries_id_seq")
    op.execute("ALTER INDEX IF EXISTS meal_plans_pkey RENAME TO meal_entries_pkey")
    op.execute("ALTER INDEX IF EXISTS ix_meal_plans_id RENAME TO ix_meal_entries_id")
    op.execute("ALTER INDEX IF EXISTS ix_meal_plans_date RENAME TO ix_meal_entries_date")
    op.execute("ALTER TABLE meal_entries RENAME CONSTRAINT meal_plans_recipe_id_fkey TO meal_entries_recipe_id_fkey")
    op.execute("ALTER TABLE meal_entries RENAME CONSTRAINT fk_meal_plans_slot_type TO fk_meal_entries_slot_type")

    # Add food_item_id FK (table is now meal_entries)
    op.create_foreign_key(
        'fk_meal_entries_food_item', 'meal_entries', 'food_items',
        ['food_item_id'], ['id'], ondelete='SET NULL'
    )

    # ── 6. Drop category column and mealcategory enum ──
    op.drop_column('meal_entries', 'category')
    op.execute("DROP TYPE IF EXISTS mealcategory")

    # ── 7. Create meal_entry_participants junction table ──
    op.create_table(
        'meal_entry_participants',
        sa.Column('meal_entry_id', sa.Integer(), sa.ForeignKey('meal_entries.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('family_member_id', sa.Integer(), sa.ForeignKey('family_members.id', ondelete='CASCADE'), primary_key=True),
    )

    # ── 8. Add aggregation fields + unique constraint to tasks ──
    op.add_column('tasks', sa.Column('source_meals', sa.JSON(), nullable=True))
    op.add_column('tasks', sa.Column('aggregation_key_name', sa.String(), nullable=True))
    op.add_column('tasks', sa.Column('aggregation_unit_group', sa.String(), nullable=True))
    op.create_unique_constraint(
        'uq_task_ingredient_aggregate', 'tasks',
        ['list_id', 'aggregation_key_name', 'aggregation_unit_group'],
    )

    # ── 9. Add mealboard settings to app_settings ──
    op.add_column('app_settings', sa.Column('week_start_day', sa.String(), server_default='monday', nullable=False))
    op.add_column('app_settings', sa.Column('measurement_system', sa.String(), server_default='imperial', nullable=False))
    op.add_column('app_settings', sa.Column('mealboard_shopping_list_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_app_settings_shopping_list', 'app_settings', 'lists',
        ['mealboard_shopping_list_id'], ['id'], ondelete='SET NULL'
    )


def downgrade() -> None:
    # ── 9. Remove mealboard settings ──
    op.drop_constraint('fk_app_settings_shopping_list', 'app_settings', type_='foreignkey')
    op.drop_column('app_settings', 'mealboard_shopping_list_id')
    op.drop_column('app_settings', 'measurement_system')
    op.drop_column('app_settings', 'week_start_day')

    # ── 8. Remove aggregation fields from tasks ──
    op.drop_constraint('uq_task_ingredient_aggregate', 'tasks', type_='unique')
    op.drop_column('tasks', 'aggregation_unit_group')
    op.drop_column('tasks', 'aggregation_key_name')
    op.drop_column('tasks', 'source_meals')

    # ── 7. Drop meal_entry_participants ──
    op.drop_table('meal_entry_participants')

    # ── 6. Re-create category column with enum ──
    mealcategory = sa.Enum('BREAKFAST', 'LUNCH', 'DINNER', name='mealcategory')
    mealcategory.create(op.get_bind())
    op.add_column('meal_entries', sa.Column('category', mealcategory, nullable=True))

    # ── 5. Rename meal_entries → meal_plans ──
    op.drop_constraint('fk_meal_entries_food_item', 'meal_entries', type_='foreignkey')
    op.execute("ALTER TABLE meal_entries RENAME CONSTRAINT fk_meal_entries_slot_type TO fk_meal_plans_slot_type")
    op.execute("ALTER TABLE meal_entries RENAME CONSTRAINT meal_entries_recipe_id_fkey TO meal_plans_recipe_id_fkey")
    op.execute("ALTER INDEX IF EXISTS ix_meal_entries_date RENAME TO ix_meal_plans_date")
    op.execute("ALTER INDEX IF EXISTS ix_meal_entries_id RENAME TO ix_meal_plans_id")
    op.execute("ALTER INDEX IF EXISTS meal_entries_pkey RENAME TO meal_plans_pkey")
    op.execute("ALTER SEQUENCE meal_entries_id_seq RENAME TO meal_plans_id_seq")
    op.rename_table('meal_entries', 'meal_plans')

    # ── 4. Migrate data back (CAST needed for PostgreSQL enum type) ──
    op.execute("""
        UPDATE meal_plans SET category = (CASE
            WHEN meal_slot_type_id = (SELECT id FROM meal_slot_types WHERE name = 'Breakfast') THEN 'BREAKFAST'
            WHEN meal_slot_type_id = (SELECT id FROM meal_slot_types WHERE name = 'Lunch') THEN 'LUNCH'
            WHEN meal_slot_type_id = (SELECT id FROM meal_slot_types WHERE name = 'Dinner') THEN 'DINNER'
        END)::mealcategory
    """)
    op.alter_column('meal_plans', 'category', nullable=False)

    # ── 3. Drop new columns ──
    op.drop_constraint('fk_meal_plans_slot_type', 'meal_plans', type_='foreignkey')
    op.drop_column('meal_plans', 'shopping_sync_status')
    op.drop_column('meal_plans', 'sort_order')
    op.drop_column('meal_plans', 'servings')
    op.drop_column('meal_plans', 'item_type')
    op.drop_column('meal_plans', 'food_item_id')
    op.drop_column('meal_plans', 'meal_slot_type_id')

    # ── 2. Drop food_items ──
    op.drop_table('food_items')

    # ── 1. Drop meal_slot_types ──
    op.drop_table('meal_slot_types')
