"""Add nullable source_url to recipe_details.

Tracks the URL that an imported recipe was extracted from. Nullable so existing
recipes (manually created before the AI import feature) stay valid with NULL
source_url, and the "View Original" link in the detail view renders only when
the column is populated.

Revision ID: e5a6b7c8d9e0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5a6b7c8d9e0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "recipe_details",
        sa.Column("source_url", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("recipe_details", "source_url")
