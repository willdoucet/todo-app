"""Recreate uq_task_ingredient_aggregate with NULLS NOT DISTINCT.

Pantry-staple shopping items have ``aggregation_unit IS NULL``. Postgres treats
NULL as distinct in unique constraints by default, so two concurrent shopping
syncs for the same pantry ingredient can both observe "no row" in the FOR
UPDATE lookup and both INSERT — the unique constraint never fires and the
shopping list grows duplicate pantry rows.

Postgres 15+ supports ``UNIQUE NULLS NOT DISTINCT``, which makes a single NULL
collide with another NULL in the same bucket. Recreate the constraint with
that semantic so the aggregation bucket is enforced even for pantry staples.

Revision ID: d4e5f6a7b8c9
Revises: a1b2c3d4e5f3
Create Date: 2026-04-15
"""
from typing import Sequence, Union

from alembic import op


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: dedupe any pre-existing duplicate aggregation rows that the old
    # NULL-distinct constraint silently allowed. Pantry staples (NULL unit) are
    # the most common case, but the same logic applies to any bucket key.
    # Strategy: keep the row with the smallest id per bucket, merge the
    # `source_meals` JSONB arrays of the duplicates into it, then delete the
    # losers. Quantities aren't summed here — the periodic shopping sync will
    # rebuild them from the merged source_meals on the next run, and pantry
    # rows have base_qty=0 anyway.
    op.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                list_id,
                aggregation_source,
                aggregation_key_name,
                aggregation_unit,
                source_meals,
                ROW_NUMBER() OVER (
                    PARTITION BY list_id, aggregation_source, aggregation_key_name, aggregation_unit
                    ORDER BY id
                ) AS rn
            FROM tasks
            WHERE aggregation_source IS NOT NULL
        ),
        winners AS (
            SELECT id, list_id, aggregation_source, aggregation_key_name, aggregation_unit
            FROM ranked WHERE rn = 1
        ),
        losers AS (
            SELECT id, list_id, aggregation_source, aggregation_key_name, aggregation_unit, source_meals
            FROM ranked WHERE rn > 1
        ),
        merged AS (
            SELECT
                w.id AS winner_id,
                jsonb_agg(elem) AS extra_sources
            FROM winners w
            JOIN losers l
              ON l.list_id = w.list_id
             AND l.aggregation_source = w.aggregation_source
             AND COALESCE(l.aggregation_key_name, '') = COALESCE(w.aggregation_key_name, '')
             AND COALESCE(l.aggregation_unit, '') = COALESCE(w.aggregation_unit, ''),
            LATERAL json_array_elements(COALESCE(l.source_meals, '[]'::json)) AS elem
            GROUP BY w.id
        )
        UPDATE tasks t
        SET source_meals = ((COALESCE(t.source_meals, '[]'::json)::jsonb) || m.extra_sources)::json
        FROM merged m
        WHERE t.id = m.winner_id
        """
    )
    op.execute(
        """
        DELETE FROM tasks t
        USING (
            SELECT id FROM (
                SELECT
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY list_id, aggregation_source, aggregation_key_name, aggregation_unit
                        ORDER BY id
                    ) AS rn
                FROM tasks
                WHERE aggregation_source IS NOT NULL
            ) ranked
            WHERE rn > 1
        ) losers
        WHERE t.id = losers.id
        """
    )

    # Step 2: drop the over-broad full-table unique constraint and replace it
    # with a PARTIAL unique index scoped to aggregation rows only. The original
    # constraint covered every task in the table, which incorrectly tried to
    # deduplicate plain user-created tasks (where aggregation_* is NULL). Limit
    # the uniqueness to rows that actually participate in shopping aggregation,
    # and use NULLS NOT DISTINCT so pantry staples (NULL aggregation_unit) get
    # properly deduplicated within that scope.
    op.drop_constraint("uq_task_ingredient_aggregate", "tasks", type_="unique")
    op.execute(
        """
        CREATE UNIQUE INDEX uq_task_ingredient_aggregate
        ON tasks (list_id, aggregation_source, aggregation_key_name, aggregation_unit)
        NULLS NOT DISTINCT
        WHERE aggregation_source IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_task_ingredient_aggregate")
    op.create_unique_constraint(
        "uq_task_ingredient_aggregate",
        "tasks",
        ["list_id", "aggregation_source", "aggregation_key_name", "aggregation_unit"],
    )
