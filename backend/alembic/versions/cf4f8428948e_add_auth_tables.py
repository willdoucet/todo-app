"""add auth tables

Revision ID: cf4f8428948e
Revises: f8a9b0c1d2e3
Create Date: 2026-05-02 20:41:29.511757

M3 prod-auth-backend-foundation. Creates the singleton ``users`` table and
the rotation-chain ``refresh_tokens`` table.

The CITEXT extension is created idempotently inside the upgrade (so the
migration is safe to run on a fresh database without an out-of-band
``CREATE EXTENSION``). Pre-flight check ran ``SELECT * FROM
pg_available_extensions WHERE name='citext'`` against the local Postgres 16
container before this migration was authored.

Downgrade drops both auth tables and their indexes but does NOT drop the
citext extension. The extension may be re-used by future tables and
leaving it installed is safer than breaking unrelated schema during a
rollback (Adversarial review).

Production rollback is code-only by default (redeploy the previous image)
and leaves auth tables/data in place. Run downgrade only when intentionally
abandoning M3 auth state after taking a backup.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'cf4f8428948e'
down_revision: Union[str, Sequence[str], None] = 'f8a9b0c1d2e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # CITEXT extension required by the users.email column. Idempotent —
    # safe to re-run on databases where the extension is already installed.
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('email', postgresql.CITEXT(), nullable=False),
        sa.Column('password_hash', sa.Text(), nullable=False),
        sa.Column('session_version', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
    )

    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('token_hash', sa.LargeBinary(), nullable=False),
        sa.Column('successor_id', sa.BigInteger(), nullable=True),
        sa.Column('issued_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('superseded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['users.id'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
    )

    # Self-referential FK on successor_id. Added via ALTER (not inside
    # create_table) because the table can't reference itself before it
    # exists. ``use_alter=True`` on the SQLAlchemy ForeignKey is what tells
    # the ORM-side metadata to defer this; for alembic migrations we make
    # the deferral explicit with op.create_foreign_key.
    op.create_foreign_key(
        'fk_refresh_tokens_successor_id',
        'refresh_tokens',
        'refresh_tokens',
        ['successor_id'],
        ['id'],
        ondelete='SET NULL',
    )

    op.create_index(
        'ix_refresh_tokens_successor_id',
        'refresh_tokens',
        ['successor_id'],
        unique=False,
        postgresql_where=sa.text('successor_id IS NOT NULL'),
    )
    op.create_index(
        'ix_refresh_tokens_token_hash',
        'refresh_tokens',
        ['token_hash'],
        unique=True,
    )
    op.create_index(
        op.f('ix_refresh_tokens_user_id'),
        'refresh_tokens',
        ['user_id'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema. Drops auth tables; LEAVES citext extension in place."""
    # Drop the self-FK first so the table can be dropped cleanly.
    op.drop_constraint(
        'fk_refresh_tokens_successor_id',
        'refresh_tokens',
        type_='foreignkey',
    )
    op.drop_index(op.f('ix_refresh_tokens_user_id'), table_name='refresh_tokens')
    op.drop_index('ix_refresh_tokens_token_hash', table_name='refresh_tokens')
    op.drop_index(
        'ix_refresh_tokens_successor_id',
        table_name='refresh_tokens',
        postgresql_where=sa.text('successor_id IS NOT NULL'),
    )
    op.drop_table('refresh_tokens')
    op.drop_table('users')
