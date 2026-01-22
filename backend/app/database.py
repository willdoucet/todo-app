from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL")

# Only create engine if DATABASE_URL is set (lazy initialization)
if DATABASE_URL:
    engine = create_async_engine(DATABASE_URL, echo=True)
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
