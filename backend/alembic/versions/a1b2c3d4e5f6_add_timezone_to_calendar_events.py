"""add_timezone_to_calendar_events

Revision ID: a1b2c3d4e5f6
Revises: f70b63a57ef3
Create Date: 2026-03-02 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f70b63a57ef3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add timezone column to calendar_events and backfill timed events."""
    op.add_column('calendar_events', sa.Column('timezone', sa.String(), nullable=True))

    # Backfill timed events with current AppSettings timezone
    op.execute("""
        UPDATE calendar_events
        SET timezone = (SELECT timezone FROM app_settings LIMIT 1)
        WHERE all_day = false AND start_time IS NOT NULL
    """)


def downgrade() -> None:
    """Remove timezone column from calendar_events."""
    op.drop_column('calendar_events', 'timezone')
