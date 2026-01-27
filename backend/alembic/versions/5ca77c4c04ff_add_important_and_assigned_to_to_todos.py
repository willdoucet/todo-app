"""add important and assigned_to to todos

Revision ID: 5ca77c4c04ff
Revises: 5a5959f151fa
Create Date: 2026-01-22 19:29:37.722256

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5ca77c4c04ff'
down_revision: Union[str, Sequence[str], None] = '5a5959f151fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create the enum type using raw SQL with IF NOT EXISTS (works reliably with asyncpg)
    op.execute("CREATE TYPE assignedto AS ENUM ('WILL', 'CELINE', 'ALL')")
    
    # Add columns with server_default for existing rows
    assignedto_enum = sa.Enum('WILL', 'CELINE', 'ALL', name='assignedto', create_type=False)
    op.add_column('todos', sa.Column('assigned_to', assignedto_enum, nullable=False, server_default='ALL'))
    op.add_column('todos', sa.Column('important', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('todos', 'important')
    op.drop_column('todos', 'assigned_to')
    
    # Drop the enum type
    sa.Enum(name='assignedto').drop(op.get_bind(), checkfirst=True)
