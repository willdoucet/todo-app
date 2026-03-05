from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from . import models, schemas


async def get_settings(db: AsyncSession) -> models.AppSettings:
    """Return the singleton settings row, creating it with defaults if missing."""
    stmt = select(models.AppSettings)
    result = await db.execute(stmt)
    settings = result.scalar_one_or_none()

    if settings is None:
        settings = models.AppSettings(timezone="UTC")
        db.add(settings)
        await db.commit()
        await db.refresh(settings)

    return settings


async def update_settings(
    db: AsyncSession, update: schemas.AppSettingsUpdate
) -> models.AppSettings:
    """Patch the singleton settings row."""
    settings = await get_settings(db)

    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)

    await db.commit()
    await db.refresh(settings)
    return settings
