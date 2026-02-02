"""add_lists_table

Revision ID: 7c14f1caab65
Revises: 5500b4fc0d01
Create Date: 2026-01-31 05:45:06.272364

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7c14f1caab65"
down_revision: Union[str, Sequence[str], None] = "5500b4fc0d01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create lists table
    op.create_table(
        "lists",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("color", sa.String(), nullable=True),
        sa.Column("icon", sa.String(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_lists_id"), "lists", ["id"], unique=False)
    op.create_index(op.f("ix_lists_name"), "lists", ["name"], unique=False)

    # Add list_id column to tasks (nullable initially)
    op.add_column("tasks", sa.Column("list_id", sa.Integer(), nullable=True))

    # Create default "General" list and migrate existing tasks
    op.execute("INSERT INTO lists (name) VALUES ('General')")
    op.execute(
        "UPDATE tasks SET list_id = (SELECT id FROM lists WHERE name = 'General' LIMIT 1)"
    )

    # Make list_id NOT NULL and add foreign key
    op.alter_column("tasks", "list_id", nullable=False)
    op.create_foreign_key(None, "tasks", "lists", ["list_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint(None, "tasks", type_="foreignkey")
    op.drop_column("tasks", "list_id")
    op.drop_index(op.f("ix_lists_name"), table_name="lists")
    op.drop_index(op.f("ix_lists_id"), table_name="lists")
    op.drop_table("lists")
