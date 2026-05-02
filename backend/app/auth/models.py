"""SQLAlchemy ORM models for the auth subsystem.

Two tables — ``users`` (singleton in v1; UNIQUE(email) is the only schema-
level constraint, the singleton invariant is enforced via advisory lock +
"no existing user" check inside the register handler) and ``refresh_tokens``
(append-only audit chain with ``successor_id`` pointers).

Imports ``Base`` from ``app.models`` so the new tables register with the
single shared metadata object that alembic autogenerate already sees.
``alembic/env.py`` imports this module purely so the metadata sweep
discovers the auth tables — no runtime side effect.
"""

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import relationship

from app.models import Base


class User(Base):
    """The single shared household account. v1 invariant: 0 or 1 rows."""

    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    email = Column(CITEXT(), nullable=False, unique=True)
    password_hash = Column(Text, nullable=False)
    # session_version: bumps on operator password rotation. Read on every
    # protected request; mismatch with token claim → 401. The cheap
    # alternative to a Redis revocation cache.
    session_version = Column(Integer, nullable=False, server_default=text("0"))
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    refresh_tokens = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class RefreshToken(Base):
    """One row per opaque refresh-token value ever issued for a user.

    State machine (per row):

        live  ──login-rotate or rotate──▶  superseded (60s grace)
              ──logout / pwd-rotation──▶  revoked
              ──30 days──▶                expired

    `successor_id` lets the rotation grace window resolve the live terminal
    of the chain when an already-rotated cookie arrives (Case B in the
    plan's refresh contract). The self-FK uses ``use_alter=True`` so
    alembic can create the table first and add the FK in a follow-up
    ALTER, avoiding the "FK references self before it exists" trap.
    """

    __tablename__ = "refresh_tokens"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,  # ix_refresh_tokens_user_id
    )
    # 32-byte sha256 digest. Plaintext token never persisted.
    token_hash = Column(LargeBinary, nullable=False)
    successor_id = Column(
        BigInteger,
        ForeignKey(
            "refresh_tokens.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_refresh_tokens_successor_id",
        ),
        nullable=True,
    )
    issued_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    expires_at = Column(DateTime(timezone=True), nullable=False)
    superseded_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="refresh_tokens")

    __table_args__ = (
        Index(
            "ix_refresh_tokens_token_hash",
            "token_hash",
            unique=True,
        ),
        # Partial index — debug/chain-inspection helper. Live traversal
        # follows PK lookups; this index keeps "find rows that supersede X"
        # cheap when manually walking the chain in psql.
        Index(
            "ix_refresh_tokens_successor_id",
            "successor_id",
            postgresql_where=text("successor_id IS NOT NULL"),
        ),
    )
