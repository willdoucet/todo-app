"""Multi-category responsibilities

Revision ID: c8f3a1b2d4e5
Revises: d4046930b2e2
Create Date: 2026-02-08

Changes:
- responsibilities: category (single enum) → categories (array of strings)
- responsibility_completions: add category column, update unique constraint
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "c8f3a1b2d4e5"
down_revision = "d4046930b2e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- responsibilities table ---

    # 1. Add new categories column (nullable temporarily for migration)
    op.add_column(
        "responsibilities",
        sa.Column("categories", postgresql.ARRAY(sa.String()), nullable=True),
    )

    # 2. Migrate data: wrap single category value into an array
    op.execute(
        "UPDATE responsibilities SET categories = ARRAY[category::text]"
    )

    # 3. Make categories NOT NULL now that data is migrated
    op.alter_column("responsibilities", "categories", nullable=False)

    # 4. Drop old category column (and its enum type)
    op.drop_column("responsibilities", "category")

    # --- responsibility_completions table ---

    # 5. Add category column to completions (nullable temporarily)
    op.add_column(
        "responsibility_completions",
        sa.Column("category", sa.String(), nullable=True),
    )

    # 6. Backfill: set category from parent responsibility's first category
    op.execute(
        """
        UPDATE responsibility_completions rc
        SET category = r.categories[1]
        FROM responsibilities r
        WHERE rc.responsibility_id = r.id
        """
    )

    # 7. For any orphan completions (shouldn't exist but be safe), default to MORNING
    op.execute(
        "UPDATE responsibility_completions SET category = 'MORNING' WHERE category IS NULL"
    )

    # 8. Make category NOT NULL
    op.alter_column("responsibility_completions", "category", nullable=False)

    # 9. Drop old unique constraint and create new one with category
    op.drop_constraint(
        "uq_responsibility_completion_date", "responsibility_completions", type_="unique"
    )
    op.create_unique_constraint(
        "uq_responsibility_completion_date_category",
        "responsibility_completions",
        ["responsibility_id", "completion_date", "category"],
    )

    # 10. Clean up the old enum type (PostgreSQL keeps it around after dropping the column)
    op.execute("DROP TYPE IF EXISTS responsibilitycategory")


def downgrade() -> None:
    # Recreate the enum type
    responsibilitycategory = postgresql.ENUM(
        "MORNING", "AFTERNOON", "EVENING", "CHORE",
        name="responsibilitycategory",
        create_type=True,
    )
    responsibilitycategory.create(op.get_bind(), checkfirst=True)

    # Add back single category column
    op.add_column(
        "responsibilities",
        sa.Column("category", responsibilitycategory, nullable=True),
    )

    # Migrate: take first element of categories array
    op.execute(
        "UPDATE responsibilities SET category = categories[1]::responsibilitycategory"
    )
    op.alter_column("responsibilities", "category", nullable=False)

    # Drop categories array column
    op.drop_column("responsibilities", "categories")

    # Revert completions constraint
    op.drop_constraint(
        "uq_responsibility_completion_date_category",
        "responsibility_completions",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_responsibility_completion_date",
        "responsibility_completions",
        ["responsibility_id", "completion_date"],
    )

    # Drop category from completions
    op.drop_column("responsibility_completions", "category")
