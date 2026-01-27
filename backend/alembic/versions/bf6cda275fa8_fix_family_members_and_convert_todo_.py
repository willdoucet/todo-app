"""fix_family_members_and_convert_todo_assigned_to_fk

Revision ID: bf6cda275fa8
Revises: 7747b0506845
Create Date: 2026-01-23 20:49:29.819328

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "bf6cda275fa8"
down_revision: Union[str, Sequence[str], None] = "7747b0506845"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ============================================================
    # PART 1: Fix family_members table structure
    # ============================================================

    # Add new columns
    op.add_column("family_members", sa.Column("name", sa.String(), nullable=True))
    op.add_column(
        "family_members",
        sa.Column("is_system", sa.Boolean(), server_default="false", nullable=False),
    )

    # Drop old indexes
    op.drop_index("ix_family_members_first_name", table_name="family_members")
    op.drop_index("ix_family_members_last_name", table_name="family_members")

    # Drop old columns
    op.drop_column("family_members", "first_name")
    op.drop_column("family_members", "last_name")

    # Create index on name
    op.create_index("ix_family_members_name", "family_members", ["name"], unique=True)

    # ============================================================
    # PART 2: Drop unused responsibilities table
    # ============================================================
    op.drop_index("ix_responsibilities_name", table_name="responsibilities")
    op.drop_index("ix_responsibilities_id", table_name="responsibilities")
    op.drop_table("responsibilities")

    # ============================================================
    # PART 3: Seed family_members with initial data
    # ============================================================

    # Insert seed data
    op.execute(
        """
        INSERT INTO family_members (name, is_system, created_at) VALUES
        ('Everyone', true, NOW()),
        ('Will', false, NOW()),
        ('Celine', false, NOW())
    """
    )

    # Now make name NOT NULL (after data is inserted)
    op.alter_column("family_members", "name", nullable=False)

    # ============================================================
    # PART 4: Convert todos.assigned_to from enum to FK
    # ============================================================

    # Add temporary integer column
    op.add_column("todos", sa.Column("assigned_to_new", sa.Integer(), nullable=True))

    # Migrate data: map enum values to family_member IDs
    op.execute(
        """
        UPDATE todos 
        SET assigned_to_new = (
            SELECT id FROM family_members 
            WHERE family_members.name = CASE todos.assigned_to::text
                WHEN 'ALL' THEN 'Everyone'
                WHEN 'WILL' THEN 'Will'
                WHEN 'CELINE' THEN 'Celine'
            END
        )
    """
    )

    # Make the new column NOT NULL
    op.alter_column("todos", "assigned_to_new", nullable=False)

    # Drop old enum column
    op.drop_column("todos", "assigned_to")

    # Rename new column
    op.alter_column("todos", "assigned_to_new", new_column_name="assigned_to")

    # Add foreign key constraint
    op.create_foreign_key(
        "fk_todos_assigned_to_family_members",
        "todos",
        "family_members",
        ["assigned_to"],
        ["id"],
    )

    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS assignedto")


def downgrade() -> None:
    # This is a complex migration - downgrade would be tricky
    # For now, raise an error to prevent accidental downgrade
    raise NotImplementedError(
        "Downgrade not supported for this migration. " "Restore from backup if needed."
    )
