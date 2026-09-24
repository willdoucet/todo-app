"""add job_heartbeats table (M8 item 15)

Revision ID: 1b6b462491fa
Revises: b7e2c9a4f1d8
Create Date: 2026-09-23

One row per Celery beat_schedule task name: when it last succeeded, and whether the latest
attempt to record a success failed (so /healthz and the Settings card can tell "the recorder
is broken" from "the worker is dead"). Written by the worker's task_postrun handler with
INSERT ... ON CONFLICT (task_name), so redelivery is idempotent. Staleness is derived per
request in app.job_health, never stored.

Additive and reversible: a new table no existing code reads, so the previous image keeps
working against it (release_command safety), and downgrade() drops it. The timestamps are
timestamptz, unlike the legacy naive columns (REVIEW_CHECKLIST → PostgreSQL).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1b6b462491fa"
down_revision: Union[str, Sequence[str], None] = "b7e2c9a4f1d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "job_heartbeats",
        sa.Column("task_name", sa.Text(), nullable=False),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "error_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("task_name"),
    )


def downgrade() -> None:
    op.drop_table("job_heartbeats")
