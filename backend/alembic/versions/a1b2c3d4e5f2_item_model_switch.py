"""item_model_switch — Revision 2 of the Unified Item Model refactor (SWITCH phase).

This revision is a NO-OP at the schema level. Its purpose is documentary: it marks a
named point in the Alembic revision graph where the application read path has been
flipped from the old (`recipes` / `food_items`) schema to the new (`items` + details)
schema. Dual-write on the write path continues through this revision and is only
stopped at Revision 3.

Rollback posture: `alembic downgrade a1b2c3d4e5f1` is the instruction to revert BOTH
the schema state AND the application code revert that flipped reads. The backend code
revert must be shipped in the rollback PR.

Revision ID: a1b2c3d4e5f2
Revises: a1b2c3d4e5f1
Create Date: 2026-04-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f2'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """SWITCH: no schema change. Signals the application read-flip point."""
    pass


def downgrade() -> None:
    """No-op: the schema hasn't changed. Rolling back Revision 2 means reverting the
    application-code change that flipped reads. Alembic downgrade is a signal, not the
    mechanism.
    """
    pass
