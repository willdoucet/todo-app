"""API endpoints for managing calendar integrations (iCloud, future: Google)."""

import asyncio
import logging
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from .. import schemas, crud_calendar_integrations, models
from ..database import get_db
from ..services import caldav_client

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/integrations",
    tags=["integrations"],
    responses={404: {"description": "Not found"}},
)


@router.post("/icloud/validate", response_model=List[schemas.ICloudCalendarInfo])
async def validate_icloud(
    payload: schemas.CalendarIntegrationCreate,
    db: AsyncSession = Depends(get_db),
):
    """Step 1 of connection flow: validate credentials and return available calendars.

    Does NOT store credentials. Returns calendar list with shared-calendar detection.
    """
    try:
        client, principal = await asyncio.to_thread(
            caldav_client.connect_icloud, payload.email, payload.password
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Could not connect to iCloud. Check your email and app-specific password. ({type(e).__name__})",
        )

    calendars = await asyncio.to_thread(caldav_client.list_calendars, principal)

    # Fetch events from each calendar for count + shared calendar detection
    today = date.today()
    start = today - timedelta(days=30)
    end = today + timedelta(days=90)

    result = []
    for cal_info in calendars:
        event_count = None
        already_synced_by = None
        try:
            calendar = await asyncio.to_thread(
                caldav_client.get_calendar_by_url, principal, cal_info["url"]
            )
            events = await asyncio.to_thread(
                caldav_client.fetch_events, calendar, start, end
            )
            event_count = len(events)

            # Check if any UIDs already exist locally (shared calendar detection)
            if events:
                external_ids = [e["external_id"] for e in events[:50]]
                stmt = (
                    select(
                        models.CalendarEvent.external_id,
                        models.FamilyMember.name,
                    )
                    .join(
                        models.CalendarIntegration,
                        models.CalendarEvent.calendar_integration_id
                        == models.CalendarIntegration.id,
                    )
                    .join(
                        models.FamilyMember,
                        models.CalendarIntegration.family_member_id
                        == models.FamilyMember.id,
                    )
                    .where(models.CalendarEvent.external_id.in_(external_ids))
                    .limit(1)
                )
                row = (await db.execute(stmt)).first()
                if row:
                    already_synced_by = row.name
        except Exception:
            logger.warning(
                "Failed to fetch events for calendar %s during validate",
                cal_info["name"],
                exc_info=True,
            )

        result.append(
            schemas.ICloudCalendarInfo(
                url=cal_info["url"],
                name=cal_info["name"],
                color=cal_info.get("color"),
                event_count=event_count,
                already_synced_by=already_synced_by,
            )
        )

    return result


@router.post(
    "/icloud/connect",
    response_model=schemas.CalendarIntegrationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def connect_icloud(
    payload: schemas.CalendarIntegrationCreate,
    db: AsyncSession = Depends(get_db),
):
    """Step 2 of connection flow: store credentials and trigger initial sync.

    Encrypts password, creates CalendarIntegration, dispatches Celery task.
    """
    # Validate credentials before storing
    try:
        await asyncio.to_thread(
            caldav_client.connect_icloud, payload.email, payload.password
        )
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Could not connect to iCloud. Check your credentials.",
        )

    # Create integration (password encrypted in CRUD layer)
    integration = await crud_calendar_integrations.create_integration(db, payload)

    # Set status to SYNCING and dispatch initial sync
    await crud_calendar_integrations.update_integration_status(
        db, integration.id, models.IntegrationStatus.SYNCING
    )

    from ..tasks import sync_single_integration

    sync_single_integration.delay(integration.id)

    return await crud_calendar_integrations.get_integration(db, integration.id)


@router.get("/", response_model=List[schemas.CalendarIntegrationResponse])
async def list_integrations(
    family_member_id: int = None,
    db: AsyncSession = Depends(get_db),
):
    """List all calendar integrations, optionally filtered by family member."""
    return await crud_calendar_integrations.get_integrations(db, family_member_id)


@router.get("/{integration_id}", response_model=schemas.CalendarIntegrationResponse)
async def get_integration(
    integration_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a single integration status."""
    integration = await crud_calendar_integrations.get_integration(db, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    return integration


@router.post("/{integration_id}/sync", response_model=schemas.CalendarIntegrationResponse)
async def trigger_sync(
    integration_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Trigger a manual 'Sync Now' for an integration."""
    integration = await crud_calendar_integrations.get_integration(db, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    await crud_calendar_integrations.update_integration_status(
        db, integration_id, models.IntegrationStatus.SYNCING
    )

    from ..tasks import sync_single_integration

    sync_single_integration.delay(integration_id)

    return await crud_calendar_integrations.get_integration(db, integration_id)


@router.delete("/{integration_id}", response_model=schemas.CalendarIntegrationResponse)
async def disconnect_integration(
    integration_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Disconnect: delete integration and all its synced events."""
    integration = await crud_calendar_integrations.get_integration(db, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    return await crud_calendar_integrations.delete_integration(db, integration_id)
