from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from .. import schemas, crud_calendar_events, crud_calendars
from ..models import CalendarEventSource
from ..database import get_db
from ..crud_app_settings import get_settings

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
    # Auto-set timezone from AppSettings for timed events without one
    if not event.all_day and event.start_time and not event.timezone:
        settings = await get_settings(db)
        event = event.model_copy(update={"timezone": settings.timezone})

    # If calendar_id is set, wire up integration fields and mark for push
    if event.calendar_id:
        cal = await crud_calendars.get_calendar(db, event.calendar_id)
        if not cal:
            raise HTTPException(status_code=400, detail="Calendar not found")
        event = event.model_copy(update={
            "source": CalendarEventSource.ICLOUD,
        })
        result = await crud_calendar_events.create_calendar_event(db=db, event=event)
        # Set integration fields that aren't in the schema
        await crud_calendar_events.set_integration_fields(
            db, result.id, cal.calendar_integration_id, cal.id, "PENDING_PUSH"
        )
        from ..tasks import push_event_to_icloud
        push_event_to_icloud.apply_async(args=[result.id], countdown=30)
        return await crud_calendar_events.get_calendar_event(db, result.id)

    return await crud_calendar_events.create_calendar_event(db=db, event=event)


@router.patch("/{event_id}", response_model=schemas.CalendarEvent)
async def update_calendar_event(
    event_id: int,
    event_update: schemas.CalendarEventUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a calendar event. MANUAL and ICLOUD events can be edited."""
    existing = await crud_calendar_events.get_calendar_event(db, event_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Calendar event not found")
    if existing.source == CalendarEventSource.GOOGLE:
        raise HTTPException(
            status_code=400,
            detail="Google Calendar events cannot be edited yet",
        )

    # Detect calendar_id transitions
    new_calendar_id = event_update.calendar_id if "calendar_id" in event_update.model_fields_set else None
    old_calendar_id = existing.calendar_id
    calendar_changed = "calendar_id" in event_update.model_fields_set and new_calendar_id != old_calendar_id

    if calendar_changed:
        if new_calendar_id is not None:
            new_cal = await crud_calendars.get_calendar(db, new_calendar_id)
            if not new_cal:
                raise HTTPException(status_code=400, detail="Calendar not found")

        if old_calendar_id is None and new_calendar_id is not None:
            # MANUAL → ICLOUD: push to iCloud
            new_cal = await crud_calendars.get_calendar(db, new_calendar_id)
            # Apply the field update (excluding calendar_id which we handle separately)
            result = await crud_calendar_events.update_calendar_event(db, event_id, event_update)
            await crud_calendar_events.set_integration_fields(
                db, event_id, new_cal.calendar_integration_id, new_calendar_id, "PENDING_PUSH",
                source=CalendarEventSource.ICLOUD,
            )
            from ..tasks import push_event_to_icloud
            push_event_to_icloud.apply_async(args=[event_id], countdown=30)
            return await crud_calendar_events.get_calendar_event(db, event_id)

        elif old_calendar_id is not None and new_calendar_id is None:
            # ICLOUD → MANUAL: delete from iCloud, keep locally
            external_id = existing.external_id
            integration_id = existing.calendar_integration_id
            result = await crud_calendar_events.update_calendar_event(db, event_id, event_update)
            await crud_calendar_events.set_integration_fields(
                db, event_id, None, None, None,
                source=CalendarEventSource.MANUAL,
                clear_external_id=True,
            )
            if external_id and integration_id:
                from ..tasks import push_delete_to_icloud
                push_delete_to_icloud.apply_async(
                    args=[external_id, integration_id], countdown=30
                )
            return await crud_calendar_events.get_calendar_event(db, event_id)

        elif old_calendar_id is not None and new_calendar_id is not None:
            # ICLOUD → ICLOUD: move between calendars
            new_cal = await crud_calendars.get_calendar(db, new_calendar_id)
            old_cal = await crud_calendars.get_calendar(db, old_calendar_id)
            if not old_cal or not new_cal:
                raise HTTPException(status_code=400, detail="Calendar not found")
            if old_cal.calendar_integration_id != new_cal.calendar_integration_id:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot move events between different iCloud accounts",
                )
            result = await crud_calendar_events.update_calendar_event(db, event_id, event_update)
            await crud_calendar_events.set_integration_fields(
                db, event_id, new_cal.calendar_integration_id, new_calendar_id, "PENDING_PUSH",
            )
            from ..tasks import move_event_on_icloud
            move_event_on_icloud.apply_async(
                args=[event_id, old_calendar_id, new_calendar_id], countdown=30
            )
            return await crud_calendar_events.get_calendar_event(db, event_id)

    # Standard update (no calendar change)
    result = await crud_calendar_events.update_calendar_event(db, event_id, event_update)
    # For ICLOUD events: set sync_status and queue push
    if existing.source == CalendarEventSource.ICLOUD:
        await crud_calendar_events.set_sync_status(db, event_id, "PENDING_PUSH")
        from ..tasks import push_event_to_icloud
        push_event_to_icloud.apply_async(args=[event_id], countdown=30)
        # Re-fetch after set_sync_status commit to avoid expired attributes
        result = await crud_calendar_events.get_calendar_event(db, event_id)
    return result


@router.delete("/{event_id}", response_model=schemas.CalendarEvent)
async def delete_calendar_event(event_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a calendar event. MANUAL and ICLOUD events can be deleted."""
    existing = await crud_calendar_events.get_calendar_event(db, event_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Calendar event not found")
    if existing.source == CalendarEventSource.GOOGLE:
        raise HTTPException(
            status_code=400,
            detail="Google Calendar events cannot be deleted yet",
        )
    # For ICLOUD events: save info needed to push delete to remote
    push_delete = (
        existing.source == CalendarEventSource.ICLOUD
        and existing.external_id
        and existing.calendar_integration_id
    )
    external_id = existing.external_id if push_delete else None
    integration_id = existing.calendar_integration_id if push_delete else None

    result = await crud_calendar_events.delete_calendar_event(db, event_id)

    if push_delete:
        from ..tasks import push_delete_to_icloud
        push_delete_to_icloud.apply_async(
            args=[external_id, integration_id], countdown=30
        )
    return result
