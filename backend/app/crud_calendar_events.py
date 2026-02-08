from datetime import date

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from . import models, schemas


async def get_calendar_events(
    db: AsyncSession,
    start_date: date,
    end_date: date,
    assigned_to: int = None,
):
    """Get calendar events for a date range, optionally filtered by member."""
    stmt = (
        select(models.CalendarEvent)
        .options(selectinload(models.CalendarEvent.family_member))
        .where(models.CalendarEvent.date >= start_date)
        .where(models.CalendarEvent.date <= end_date)
    )
    if assigned_to is not None:
        stmt = stmt.where(models.CalendarEvent.assigned_to == assigned_to)
    stmt = stmt.order_by(models.CalendarEvent.date, models.CalendarEvent.start_time)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_calendar_event(db: AsyncSession, event_id: int):
    """Get a single calendar event by ID."""
    stmt = (
        select(models.CalendarEvent)
        .options(selectinload(models.CalendarEvent.family_member))
        .where(models.CalendarEvent.id == event_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_calendar_event(
    db: AsyncSession, event: schemas.CalendarEventCreate
):
    """Create a new calendar event."""
    db_event = models.CalendarEvent(**event.model_dump())
    db.add(db_event)
    await db.commit()
    return await get_calendar_event(db, db_event.id)


async def update_calendar_event(
    db: AsyncSession, event_id: int, event: schemas.CalendarEventUpdate
):
    """Update an existing calendar event."""
    stmt = (
        update(models.CalendarEvent)
        .where(models.CalendarEvent.id == event_id)
        .values(**event.model_dump(exclude_unset=True))
    )
    result = await db.execute(stmt)
    if result.rowcount == 0:
        return None
    await db.commit()
    return await get_calendar_event(db, event_id)


async def delete_calendar_event(db: AsyncSession, event_id: int):
    """Delete a calendar event."""
    event = await get_calendar_event(db, event_id)
    if event:
        await db.delete(event)
        await db.commit()
    return event
