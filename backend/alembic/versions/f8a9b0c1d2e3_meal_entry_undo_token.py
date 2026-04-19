"""Add undo_token column to meal_entries for user-initiated soft-delete + undo.

Partial index on (undo_token) WHERE undo_token IS NOT NULL keeps the lookup
fast for the undo endpoint without bloating writes on the 99%+ of rows that
don't carry a token.

`soft_hidden_at` now has two writers:
    - cascade-hide from item delete (undo_token IS NULL)  — existing behavior
    - user-initiated 5s undo window (undo_token IS NOT NULL) — new

See the ASCII state-machine diagram at the top of crud_meal_entries.py.

Revision ID: f8a9b0c1d2e3
Revises: e5a6b7c8d9e0
Create Date: 2026-04-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f8a9b0c1d2e3"
down_revision: Union[str, Sequence[str], None] = "e5a6b7c8d9e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "meal_entries",
        sa.Column("undo_token", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "meal_entries_undo_token_idx",
        "meal_entries",
        ["undo_token"],
        postgresql_where=sa.text("undo_token IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("meal_entries_undo_token_idx", table_name="meal_entries")
    op.drop_column("meal_entries", "undo_token")
