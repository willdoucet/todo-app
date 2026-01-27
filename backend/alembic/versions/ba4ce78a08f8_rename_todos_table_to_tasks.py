"""rename_todos_table_to_tasks

Revision ID: ba4ce78a08f8
Revises: bf6cda275fa8
Create Date: 2026-01-26 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "ba4ce78a08f8"
down_revision: Union[str, Sequence[str], None] = "bf6cda275fa8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename the table
    op.rename_table("todos", "tasks")

    # Rename the index (optional but cleaner)
    op.execute("ALTER INDEX IF EXISTS ix_todos_id RENAME TO ix_tasks_id")
    op.execute("ALTER INDEX IF EXISTS ix_todos_title RENAME TO ix_tasks_title")


def downgrade() -> None:
    # Rename back
    op.rename_table("tasks", "todos")

    op.execute("ALTER INDEX IF EXISTS ix_tasks_id RENAME TO ix_todos_id")
    op.execute("ALTER INDEX IF EXISTS ix_tasks_title RENAME TO ix_todos_title")
