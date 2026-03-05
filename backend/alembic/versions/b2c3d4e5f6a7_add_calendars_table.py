"""add calendars table and calendar_id to calendar_events

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create calendars table
    op.create_table(
        'calendars',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('calendar_integration_id', sa.Integer(), nullable=False),
        sa.Column('calendar_url', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('color', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['calendar_integration_id'], ['calendar_integrations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('calendar_integration_id', 'calendar_url', name='uq_calendar_integration_url'),
    )
    op.create_index(op.f('ix_calendars_id'), 'calendars', ['id'], unique=False)

    # 2. Add calendar_id FK to calendar_events
    op.add_column('calendar_events', sa.Column('calendar_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_calendar_events_calendar_id',
        'calendar_events',
        'calendars',
        ['calendar_id'],
        ['id'],
        ondelete='SET NULL',
    )

    # 3. Data migration: create Calendar rows from selected_calendars JSON
    conn = op.get_bind()
    integrations = conn.execute(
        sa.text("SELECT id, selected_calendars FROM calendar_integrations WHERE selected_calendars IS NOT NULL")
    ).fetchall()

    for integ in integrations:
        cal_urls = integ.selected_calendars
        if not cal_urls or not isinstance(cal_urls, list):
            continue
        for cal_url in cal_urls:
            # Use last path segment as placeholder name
            name = cal_url.rstrip('/').rsplit('/', 1)[-1] or cal_url
            conn.execute(
                sa.text(
                    "INSERT INTO calendars (calendar_integration_id, calendar_url, name) "
                    "VALUES (:integ_id, :url, :name) ON CONFLICT DO NOTHING"
                ),
                {"integ_id": integ.id, "url": cal_url, "name": name},
            )

    # 4. Assign existing events to the first Calendar of their integration
    conn.execute(
        sa.text(
            "UPDATE calendar_events ce "
            "SET calendar_id = ("
            "  SELECT c.id FROM calendars c "
            "  WHERE c.calendar_integration_id = ce.calendar_integration_id "
            "  ORDER BY c.id LIMIT 1"
            ") "
            "WHERE ce.calendar_integration_id IS NOT NULL AND ce.calendar_id IS NULL"
        )
    )


def downgrade() -> None:
    op.drop_constraint('fk_calendar_events_calendar_id', 'calendar_events', type_='foreignkey')
    op.drop_column('calendar_events', 'calendar_id')
    op.drop_index(op.f('ix_calendars_id'), table_name='calendars')
    op.drop_table('calendars')
