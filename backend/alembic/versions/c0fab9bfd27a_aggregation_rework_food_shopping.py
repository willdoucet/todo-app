"""aggregation_rework_food_shopping

Adds new aggregation bucket columns to tasks, shopping fields to food_items,
synced_to_list_id provenance to meal_entries. Migrates existing auto-generated
shopping rows to the new aggregation schema.

Revision ID: c0fab9bfd27a
Revises: 603854e284dd
Create Date: 2026-04-05 23:29:59.809309

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c0fab9bfd27a'
down_revision: Union[str, Sequence[str], None] = '603854e284dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Unit group → default base unit mapping for data migration
_GROUP_BASE_UNIT = {"weight": "g", "volume": "ml"}
# Unit group → default aggregation unit if source_meals doesn't have one
_GROUP_DEFAULT_UNIT = {"weight": "g", "volume": "ml", "count": "each"}


def upgrade() -> None:
    """Upgrade schema."""
    # -- food_items: add shopping fields with server defaults for existing rows --
    op.add_column('food_items', sa.Column(
        'shopping_quantity', sa.Float(), nullable=False, server_default='1.0'
    ))
    op.add_column('food_items', sa.Column(
        'shopping_unit', sa.String(), nullable=False, server_default='each'
    ))

    # -- meal_entries: add synced_to_list_id provenance column --
    op.add_column('meal_entries', sa.Column('synced_to_list_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_meal_entries_synced_to_list', 'meal_entries', 'lists',
        ['synced_to_list_id'], ['id'], ondelete='SET NULL'
    )

    # -- tasks: add new aggregation columns --
    op.add_column('tasks', sa.Column('aggregation_source', sa.String(), nullable=True))
    op.add_column('tasks', sa.Column('aggregation_unit', sa.String(), nullable=True))
    op.add_column('tasks', sa.Column('aggregation_base_unit', sa.String(), nullable=True))
    op.add_column('tasks', sa.Column('aggregation_base_quantity', sa.Float(), nullable=True))

    # -- tasks: replace unique constraint --
    op.drop_constraint('uq_task_ingredient_aggregate', 'tasks', type_='unique')
    op.create_unique_constraint(
        'uq_task_ingredient_aggregate', 'tasks',
        ['list_id', 'aggregation_source', 'aggregation_key_name', 'aggregation_unit']
    )

    # -- DATA MIGRATION --
    conn = op.get_bind()

    # 1. Backfill synced_to_list_id for existing synced meal entries
    #    Set to current AppSettings.mealboard_shopping_list_id where status='synced'
    settings_row = conn.execute(
        sa.text("SELECT mealboard_shopping_list_id FROM app_settings LIMIT 1")
    ).fetchone()

    if settings_row and settings_row[0] is not None:
        linked_list_id = settings_row[0]
        conn.execute(sa.text(
            "UPDATE meal_entries SET synced_to_list_id = :list_id "
            "WHERE shopping_sync_status = 'synced'"
        ), {"list_id": linked_list_id})

    # 2. Migrate existing auto-generated shopping rows (tasks with source_meals IS NOT NULL)
    auto_rows = conn.execute(sa.text(
        "SELECT id, source_meals, aggregation_key_name, aggregation_unit_group "
        "FROM tasks WHERE source_meals IS NOT NULL"
    )).fetchall()

    for row in auto_rows:
        task_id = row[0]
        source_meals = row[1]  # JSON array
        key_name = row[2]
        unit_group = row[3]

        # Determine aggregation_unit from source_meals or fallback
        agg_unit = None
        if source_meals and len(source_meals) > 0:
            first_entry = source_meals[0]
            base_unit = first_entry.get("base_unit")
            if base_unit:
                agg_unit = base_unit  # Use the actual stored unit
        if not agg_unit and unit_group:
            agg_unit = _GROUP_DEFAULT_UNIT.get(unit_group)

        # Determine base_unit
        agg_base_unit = _GROUP_BASE_UNIT.get(unit_group, agg_unit)

        # Calculate base_quantity from source_meals
        total_base_qty = 0.0
        if source_meals:
            total_base_qty = sum(s.get("quantity", 0) for s in source_meals)

        # Rewrite source_meals to new JSON shape
        new_source_meals = []
        for entry in (source_meals or []):
            meal_entry_id = entry.get("meal_entry_id")
            # Look up recipe_id from meal_entry
            me_row = conn.execute(sa.text(
                "SELECT recipe_id FROM meal_entries WHERE id = :id"
            ), {"id": meal_entry_id}).fetchone()
            recipe_id = me_row[0] if me_row else None

            new_entry = {
                "meal_entry_id": meal_entry_id,
                "source_kind": "recipe_ingredient",
                "recipe_id": recipe_id,
                "ingredient_name": key_name,
                "quantity": entry.get("quantity", 0),
                "unit": entry.get("base_unit"),
            }
            new_source_meals.append(new_entry)

        import json
        conn.execute(sa.text(
            "UPDATE tasks SET "
            "aggregation_source = 'mealboard_auto', "
            "aggregation_unit = :agg_unit, "
            "aggregation_base_unit = :agg_base_unit, "
            "aggregation_base_quantity = :agg_base_qty, "
            "source_meals = :source_meals "
            "WHERE id = :task_id"
        ), {
            "agg_unit": agg_unit,
            "agg_base_unit": agg_base_unit,
            "agg_base_qty": total_base_qty,
            "source_meals": json.dumps(new_source_meals),
            "task_id": task_id,
        })


def downgrade() -> None:
    """Downgrade schema."""
    # -- tasks: restore old unique constraint --
    op.drop_constraint('uq_task_ingredient_aggregate', 'tasks', type_='unique')
    op.create_unique_constraint(
        'uq_task_ingredient_aggregate', 'tasks',
        ['list_id', 'aggregation_key_name', 'aggregation_unit_group']
    )

    # -- tasks: drop new columns --
    op.drop_column('tasks', 'aggregation_base_quantity')
    op.drop_column('tasks', 'aggregation_base_unit')
    op.drop_column('tasks', 'aggregation_unit')
    op.drop_column('tasks', 'aggregation_source')

    # -- meal_entries: drop synced_to_list_id --
    op.drop_constraint('fk_meal_entries_synced_to_list', 'meal_entries', type_='foreignkey')
    op.drop_column('meal_entries', 'synced_to_list_id')

    # -- food_items: drop shopping fields --
    op.drop_column('food_items', 'shopping_unit')
    op.drop_column('food_items', 'shopping_quantity')
