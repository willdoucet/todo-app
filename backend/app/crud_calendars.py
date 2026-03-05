from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from . import models


async def get_all_calendars(db: AsyncSession):
    """Get all calendars with their integration and family member info."""
    stmt = (
        select(models.Calendar)
        .options(
            selectinload(models.Calendar.integration).selectinload(
                models.CalendarIntegration.family_member
            )
        )
        .order_by(models.Calendar.name)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_calendar(db: AsyncSession, calendar_id: int):
    """Get a single calendar by ID."""
    stmt = (
        select(models.Calendar)
        .options(
            selectinload(models.Calendar.integration).selectinload(
                models.CalendarIntegration.family_member
            )
        )
        .where(models.Calendar.id == calendar_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_or_create_calendar(
    db: AsyncSession,
    integration_id: int,
    url: str,
    name: str,
    color: str | None = None,
):
    """Get an existing calendar or create a new one. Used by sync engine."""
    stmt = select(models.Calendar).where(
        models.Calendar.calendar_integration_id == integration_id,
        models.Calendar.calendar_url == url,
    )
    result = await db.execute(stmt)
    cal = result.scalar_one_or_none()

    if cal:
        # Update name and color if they changed
        if cal.name != name:
            cal.name = name
        if cal.color != color:
            cal.color = color
        return cal

    cal = models.Calendar(
        calendar_integration_id=integration_id,
        calendar_url=url,
        name=name,
        color=color,
    )
    db.add(cal)
    await db.flush()
    return cal


async def get_calendars_for_integration(db: AsyncSession, integration_id: int):
    """Get all calendars for an integration."""
    stmt = (
        select(models.Calendar)
        .where(models.Calendar.calendar_integration_id == integration_id)
        .order_by(models.Calendar.name)
    )
    result = await db.execute(stmt)
    return result.scalars().all()
