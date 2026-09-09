"""add assets table (M7 object-storage manifest)

Revision ID: b7e2c9a4f1d8
Revises: cf4f8428948e
Create Date: 2026-09-08

Manifest for uploaded objects. Keyed by the logical `{subdir}/{uuid}.{ext}`
path, which doubles as the R2 object key and the tail of `/uploads/{key}`.
`referenced` starts false at upload and flips true when an entity adopts the
key; the (referenced, created_at) index powers the abandoned-upload sweep.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7e2c9a4f1d8"
down_revision: Union[str, Sequence[str], None] = "cf4f8428948e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("content_type", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "referenced",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_index(
        "ix_assets_referenced_created_at",
        "assets",
        ["referenced", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_assets_referenced_created_at", table_name="assets")
    op.drop_table("assets")
