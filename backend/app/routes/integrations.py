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

    # If no calendar_details provided but selected_calendars are, populate details
    # from the validate step's calendar listing (re-fetch since we just validated)
    if payload.selected_calendars and not payload.calendar_details:
        try:
            client, principal = await asyncio.to_thread(
                caldav_client.connect_icloud, payload.email, payload.password
            )
            all_cals = await asyncio.to_thread(caldav_client.list_calendars, principal)
            selected_set = set(payload.selected_calendars)
            payload.calendar_details = [
                {"url": c["url"], "name": c["name"], "color": c.get("color")}
                for c in all_cals if c["url"] in selected_set
            ]
        except Exception:
            pass  # Fall back to URL-based naming

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


# =============================================================================
# iCloud Reminders endpoints
# =============================================================================


@router.post(
    "/icloud/validate-reminders",
    response_model=List[schemas.ICloudReminderListInfo],
)
async def validate_reminders(
    payload: schemas.RemindersValidatePayload,
    db: AsyncSession = Depends(get_db),
):
    """Validate existing iCloud credentials and return available reminder lists.

    Reuses credentials from an existing integration — no password needed.
    """
    integration = await crud_calendar_integrations.get_integration(
        db, payload.integration_id
    )
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    from ..utils.encryption import decrypt_password

    password = decrypt_password(integration.encrypted_password)

    try:
        client, principal = await asyncio.to_thread(
            caldav_client.connect_icloud, integration.email, password
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Could not connect to iCloud. Credentials may have changed. ({type(e).__name__})",
        )

    reminder_lists = await asyncio.to_thread(
        caldav_client.list_reminder_lists, principal
    )

    result = []
    for cal_info in reminder_lists:
        task_count = None
        already_synced_by = None
        try:
            calendar = await asyncio.to_thread(
                caldav_client.get_calendar_by_url, principal, cal_info["url"]
            )
            todos = await asyncio.to_thread(caldav_client.fetch_todos, calendar)
            task_count = len(todos)

            # Check if already synced by another member
            if todos:
                external_ids = [t["external_id"] for t in todos[:50]]
                stmt = (
                    select(
                        models.Task.external_id,
                        models.FamilyMember.name,
                    )
                    .join(
                        models.CalendarIntegration,
                        models.Task.calendar_integration_id
                        == models.CalendarIntegration.id,
                    )
                    .join(
                        models.FamilyMember,
                        models.CalendarIntegration.family_member_id
                        == models.FamilyMember.id,
                    )
                    .where(models.Task.external_id.in_(external_ids))
                    .limit(1)
                )
                row = (await db.execute(stmt)).first()
                if row:
                    already_synced_by = row.name
        except Exception:
            logger.warning(
                "Failed to fetch todos for reminder list %s during validate",
                cal_info["name"],
                exc_info=True,
            )

        result.append(
            schemas.ICloudReminderListInfo(
                url=cal_info["url"],
                name=cal_info["name"],
                color=cal_info.get("color"),
                task_count=task_count,
                already_synced_by=already_synced_by,
            )
        )

    return result


@router.post(
    "/icloud/connect-reminders",
    response_model=schemas.CalendarIntegrationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def connect_reminders(
    payload: schemas.RemindersConnectPayload,
    db: AsyncSession = Depends(get_db),
):
    """Connect iCloud Reminders to an existing integration.

    Creates Calendar rows with is_todo=True and dispatches initial sync.
    """
    integration = await crud_calendar_integrations.get_integration(
        db, payload.integration_id
    )
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    from ..utils.encryption import decrypt_password

    password = decrypt_password(integration.encrypted_password)

    # Get calendar details for selected lists
    try:
        client, principal = await asyncio.to_thread(
            caldav_client.connect_icloud, integration.email, password
        )
        all_lists = await asyncio.to_thread(
            caldav_client.list_reminder_lists, principal
        )
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Could not connect to iCloud. Credentials may have changed.",
        )

    selected_set = set(payload.selected_lists)
    from ..crud_calendars import get_or_create_calendar

    for cal_info in all_lists:
        if cal_info["url"] in selected_set:
            cal_row = await get_or_create_calendar(
                db,
                integration.id,
                cal_info["url"],
                cal_info["name"],
                color=cal_info.get("color"),
            )
            # Mark as reminder list
            cal_row.is_todo = True
            await db.commit()

    # Set reminders_status to SYNCING and dispatch initial sync
    stmt = select(models.CalendarIntegration).where(
        models.CalendarIntegration.id == payload.integration_id
    )
    result = await db.execute(stmt)
    integ = result.scalar_one_or_none()
    if integ:
        integ.reminders_status = models.IntegrationStatus.SYNCING
        await db.commit()

    from ..tasks import sync_single_reminders_integration

    sync_single_reminders_integration.delay(payload.integration_id)

    return await crud_calendar_integrations.get_integration(db, payload.integration_id)


@router.post(
    "/{integration_id}/sync-reminders",
    response_model=schemas.CalendarIntegrationResponse,
)
async def trigger_reminders_sync(
    integration_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Trigger a manual 'Sync Now' for reminders."""
    integration = await crud_calendar_integrations.get_integration(db, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    # Set reminders_status to SYNCING
    stmt = select(models.CalendarIntegration).where(
        models.CalendarIntegration.id == integration_id
    )
    result = await db.execute(stmt)
    integ = result.scalar_one_or_none()
    if integ:
        integ.reminders_status = models.IntegrationStatus.SYNCING
        await db.commit()

    from ..tasks import sync_single_reminders_integration

    sync_single_reminders_integration.delay(integration_id)

    return await crud_calendar_integrations.get_integration(db, integration_id)


@router.delete("/{integration_id}/reminders")
async def disconnect_reminders(
    integration_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Disconnect reminders only: remove reminder Calendar rows and clear task sync metadata."""
    integration = await crud_calendar_integrations.get_integration(db, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    # Clear sync metadata on tasks (keep tasks and lists as local data)
    from sqlalchemy import update as sql_update

    stmt = (
        sql_update(models.Task)
        .where(models.Task.calendar_integration_id == integration_id)
        .values(
            external_id=None,
            etag=None,
            last_modified_remote=None,
            sync_status=None,
            calendar_integration_id=None,
        )
    )
    await db.execute(stmt)

    # Clear sync metadata on lists
    stmt = (
        sql_update(models.List)
        .where(models.List.calendar_integration_id == integration_id)
        .values(
            external_id=None,
            calendar_integration_id=None,
        )
    )
    await db.execute(stmt)

    # Delete reminder Calendar rows (is_todo=True)
    from sqlalchemy import delete as sql_delete

    stmt = sql_delete(models.Calendar).where(
        models.Calendar.calendar_integration_id == integration_id,
        models.Calendar.is_todo == True,
    )
    await db.execute(stmt)

    # Clear reminders status fields
    stmt = select(models.CalendarIntegration).where(
        models.CalendarIntegration.id == integration_id
    )
    result = await db.execute(stmt)
    integ = result.scalar_one_or_none()
    if integ:
        integ.reminders_status = None
        integ.reminders_last_error = None
        integ.reminders_last_sync_at = None

    await db.commit()

    return {"detail": "Reminders disconnected. Tasks and lists remain as local data."}
