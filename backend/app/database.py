from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL")

# SQL echo is off by default (prod). Opt in for local debugging via
# SQLALCHEMY_ECHO=true — the M7 read guard adds a refresh-hash lookup per
# image load, so leaving echo on would flood prod stdout with per-image auth
# SQL and log refresh-token hash bytes. (TODOS.md P2, bundled into M7 PR1.)
SQLALCHEMY_ECHO = os.getenv("SQLALCHEMY_ECHO", "false").lower() == "true"

# Only create engine if DATABASE_URL is set (lazy initialization)
if DATABASE_URL:
    engine = create_async_engine(
        DATABASE_URL,
        echo=SQLALCHEMY_ECHO,
        pool_pre_ping=True,
        pool_recycle=1800,
    )
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
else:
    engine = None
    AsyncSessionLocal = None


async def get_db():
    if AsyncSessionLocal is None:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    async with AsyncSessionLocal() as session:
        yield session
