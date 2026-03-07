"""remap_family_member_colors

Revision ID: d1e2f3a4b5c6
Revises: b2c3d4e5f6a7
Create Date: 2026-03-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Old palette → new Soft Contemporary palette
COLOR_MAP = {
    '#EF4444': '#D4695A',  # red → Soft Red
    '#F97316': '#D4915A',  # orange → Apricot
    '#10B981': '#5E9E6B',  # green → Sage
    '#14B8A6': '#4A9E9E',  # teal → Teal
    '#3B82F6': '#5A80B0',  # blue → Steel Blue
    '#6366F1': '#8A60B0',  # indigo → Lavender
    '#8B5CF6': '#8A60B0',  # purple → Lavender
    '#EC4899': '#B06085',  # pink → Rose
    '#D97452': '#D4695A',  # terracotta → Soft Red
}

DEFAULT_COLOR = '#5A80B0'  # Steel Blue fallback for NULLs


def upgrade() -> None:
    for old, new in COLOR_MAP.items():
        op.execute(
            f"UPDATE family_members SET color = '{new}' WHERE UPPER(color) = '{old.upper()}'"
        )
    op.execute(
        f"UPDATE family_members SET color = '{DEFAULT_COLOR}' WHERE color IS NULL"
    )


def downgrade() -> None:
    # Reverse mapping (best-effort; indigo/purple both mapped to lavender)
    reverse_map = {v: k for k, v in COLOR_MAP.items()}
    for new, old in reverse_map.items():
        op.execute(
            f"UPDATE family_members SET color = '{old}' WHERE UPPER(color) = '{new.upper()}'"
        )
