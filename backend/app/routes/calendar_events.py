from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from .. import schemas, crud_calendar_events
from ..models import CalendarEventSource
from ..database import get_db

router = APIRouter(
    prefix="/calendar-events",
    tags=["calendar-events"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=List[schemas.CalendarEvent])
async def get_calendar_events(
    start_date: date,
    end_date: date,
    assigned_to: int = None,
    db: AsyncSession = Depends(get_db),
):
    """Get calendar events for a date range. Required: start_date, end_date."""
    return await crud_calendar_events.get_calendar_events(
        db, start_date=start_date, end_date=end_date, assigned_to=assigned_to
    )


@router.get("/{event_id}", response_model=schemas.CalendarEvent)
async def get_calendar_event(event_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single calendar event by ID."""
    event = await crud_calendar_events.get_calendar_event(db, event_id=event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Calendar event not found")
    return event


@router.post("/", response_model=schemas.CalendarEvent, status_code=status.HTTP_201_CREATED)
async def create_calendar_event(
    event: schemas.CalendarEventCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new calendar event."""
    return await crud_calendar_events.create_calendar_event(db=db, event=event)


@router.patch("/{event_id}", response_model=schemas.CalendarEvent)
async def update_calendar_event(
    event_id: int,
    event_update: schemas.CalendarEventUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a calendar event. Only MANUAL events can be edited."""
    existing = await crud_calendar_events.get_calendar_event(db, event_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Calendar event not found")
    if existing.source != CalendarEventSource.MANUAL:
        raise HTTPException(
            status_code=400,
            detail="Only manually created events can be edited",
        )
    return await crud_calendar_events.update_calendar_event(db, event_id, event_update)


@router.delete("/{event_id}", response_model=schemas.CalendarEvent)
async def delete_calendar_event(event_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a calendar event. Only MANUAL events can be deleted."""
    existing = await crud_calendar_events.get_calendar_event(db, event_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Calendar event not found")
    if existing.source != CalendarEventSource.MANUAL:
        raise HTTPException(
            status_code=400,
            detail="Only manually created events can be deleted",
        )
    return await crud_calendar_events.delete_calendar_event(db, event_id)
