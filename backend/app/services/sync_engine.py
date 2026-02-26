"""Two-way sync engine for iCloud Calendar integration.

Pull: remote iCloud events → local DB
Push: local edits → remote iCloud
Conflict: last-write-wins (compare last_modified_remote UTC vs updated_at UTC)

All functions are async (use AsyncSession). Called from Celery tasks via run_async bridge.

Local-only fields preserved during pull:
  - assigned_to (local assignment, not in iCloud)
  - calendar_integration_id (set once at creation)
  - id, created_at (immutable)

Fields updated from remote:
  - title, description, date, start_time, end_time, all_day
  - etag, last_modified_remote, sync_status
"""

import logging
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models
from ..crud_app_settings import get_settings
from ..utils.encryption import decrypt_password
from . import caldav_client

logger = logging.getLogger(__name__)

# Sync status constants
SYNCED = "SYNCED"
PENDING_PUSH = "PENDING_PUSH"


async def pull_from_icloud(db: AsyncSession, integration_id: int) -> dict:
    """Pull events from iCloud into local DB.

    Returns: {created: int, updated: int, deleted: int, skipped: int, errors: int}
    """
    # Load app settings for timezone
    settings = await get_settings(db)
    tz = ZoneInfo(settings.timezone) if settings.timezone != "UTC" else None

    # Load integration
    stmt = select(models.CalendarIntegration).where(
        models.CalendarIntegration.id == integration_id
    )
    result = await db.execute(stmt)
    integration = result.scalar_one_or_none()
    if not integration:
        raise ValueError(f"Integration {integration_id} not found")

    # Decrypt and connect
    password = decrypt_password(integration.encrypted_password)
    client, principal = caldav_client.connect_icloud(integration.email, password)

    # Calculate sync range
    today = date.today()
    start_date = today - timedelta(days=integration.sync_range_past_days)
    end_date = today + timedelta(days=integration.sync_range_future_days)

    stats = {"created": 0, "updated": 0, "deleted": 0, "skipped": 0, "errors": 0}

    # Track all remote UIDs we see (for detecting remote deletions)
    seen_external_ids = set()

    selected_cals = integration.selected_calendars or []
    for cal_url in selected_cals:
        try:
            calendar = caldav_client.get_calendar_by_url(principal, cal_url)
            remote_events = caldav_client.fetch_events(calendar, start_date, end_date, tz=tz)
        except Exception:
            logger.error(
                "Failed to fetch events from calendar %s", cal_url, exc_info=True
            )
            stats["errors"] += 1
            continue

        for remote in remote_events:
            external_id = remote["external_id"]
            seen_external_ids.add(external_id)

            try:
                await _sync_single_event(
                    db, integration, remote, stats
                )
            except Exception:
                logger.error(
                    "Failed to sync event external_id=%s", external_id, exc_info=True
                )
                stats["errors"] += 1

    # Detect remote deletions: local ICLOUD events for this integration
    # that are within the sync range but NOT in the remote fetch
    await _detect_remote_deletions(
        db, integration_id, seen_external_ids, start_date, end_date, stats
    )

    await db.commit()
    return stats


async def _sync_single_event(
    db: AsyncSession,
    integration: models.CalendarIntegration,
    remote: dict,
    stats: dict,
) -> None:
    """Sync a single remote event into the local DB."""
    external_id = remote["external_id"]

    # Look up existing local event
    stmt = select(models.CalendarEvent).where(
        models.CalendarEvent.external_id == external_id,
        models.CalendarEvent.calendar_integration_id == integration.id,
    )
    result = await db.execute(stmt)
    local_event = result.scalar_one_or_none()

    if local_event is None:
        # New event — create locally
        db_event = models.CalendarEvent(
            title=remote["title"],
            description=remote["description"],
            date=remote["date"],
            start_time=remote["start_time"],
            end_time=remote["end_time"],
            all_day=remote["all_day"],
            source=models.CalendarEventSource.ICLOUD,
            external_id=external_id,
            assigned_to=integration.family_member_id,
            etag=remote.get("etag"),
            last_modified_remote=remote.get("last_modified_remote"),
            sync_status=SYNCED,
            calendar_integration_id=integration.id,
        )
        db.add(db_event)
        stats["created"] += 1
        return

    # Existing event — check if we need to update
    if local_event.sync_status == PENDING_PUSH:
        # Local has pending changes — conflict resolution
        _resolve_conflict(local_event, remote, stats)
        return

    # Compare remote modification time with local
    remote_modified = remote.get("last_modified_remote")
    local_modified = local_event.last_modified_remote

    if remote_modified and local_modified and remote_modified <= local_modified:
        # Remote hasn't changed since last sync
        # But update etag if it changed
        if remote.get("etag") and remote["etag"] != local_event.etag:
            local_event.etag = remote["etag"]
        stats["skipped"] += 1
        return

    # Remote is newer (or no timestamps to compare) — update local fields
    _update_local_from_remote(local_event, remote)
    stats["updated"] += 1


def _update_local_from_remote(local_event: models.CalendarEvent, remote: dict) -> None:
    """Update local event fields from remote data.

    PRESERVES local-only fields: assigned_to, calendar_integration_id, id, created_at
    """
    local_event.title = remote["title"]
    local_event.description = remote["description"]
    local_event.date = remote["date"]
    local_event.start_time = remote["start_time"]
    local_event.end_time = remote["end_time"]
    local_event.all_day = remote["all_day"]
    local_event.etag = remote.get("etag")
    local_event.last_modified_remote = remote.get("last_modified_remote")
    local_event.sync_status = SYNCED


def _resolve_conflict(
    local_event: models.CalendarEvent, remote: dict, stats: dict
) -> None:
    """Resolve conflict when both local and remote have changed.

    Strategy: last-write-wins based on timestamps.
    """
    remote_modified = remote.get("last_modified_remote")
    local_modified = local_event.updated_at

    # Convert local updated_at to UTC for comparison (it's stored as naive UTC)
    if local_modified and remote_modified:
        if remote_modified > local_modified:
            # Remote wins — overwrite local (but preserve assigned_to)
            logger.warning(
                "Sync conflict for event '%s' (external_id=%s): "
                "remote wins (remote=%s > local=%s)",
                local_event.title,
                local_event.external_id,
                remote_modified,
                local_modified,
            )
            _update_local_from_remote(local_event, remote)
            stats["updated"] += 1
        else:
            # Local wins — keep local changes, will be pushed
            logger.warning(
                "Sync conflict for event '%s' (external_id=%s): "
                "local wins (local=%s >= remote=%s), keeping PENDING_PUSH",
                local_event.title,
                local_event.external_id,
                local_modified,
                remote_modified,
            )
            stats["skipped"] += 1
    else:
        # No timestamps to compare — remote wins (safe default)
        _update_local_from_remote(local_event, remote)
        stats["updated"] += 1


async def _detect_remote_deletions(
    db: AsyncSession,
    integration_id: int,
    seen_external_ids: set,
    start_date: date,
    end_date: date,
    stats: dict,
) -> None:
    """Delete local events that were removed from iCloud.

    Only considers events within the sync range — events outside the range
    are kept (they just aged out of the sync window, not necessarily deleted).
    """
    stmt = select(models.CalendarEvent).where(
        models.CalendarEvent.calendar_integration_id == integration_id,
        models.CalendarEvent.source == models.CalendarEventSource.ICLOUD,
        models.CalendarEvent.date >= start_date,
        models.CalendarEvent.date <= end_date,
    )
    result = await db.execute(stmt)
    local_events = result.scalars().all()

    for event in local_events:
        if event.external_id and event.external_id not in seen_external_ids:
            # Don't delete events that have pending local changes
            if event.sync_status == PENDING_PUSH:
                logger.info(
                    "Remote deleted event '%s' but has PENDING_PUSH, keeping",
                    event.title,
                )
                continue
            logger.info(
                "Remote deletion detected for event '%s' (external_id=%s)",
                event.title,
                event.external_id,
            )
            await db.delete(event)
            stats["deleted"] += 1


async def push_to_icloud(db: AsyncSession, event_id: int) -> dict:
    """Push a single local change to iCloud.

    Returns: {action: "updated" | "created" | "noop", external_id: str | None}
    """
    # Load app settings for timezone
    settings = await get_settings(db)
    tz = ZoneInfo(settings.timezone) if settings.timezone != "UTC" else None

    stmt = (
        select(models.CalendarEvent)
        .where(models.CalendarEvent.id == event_id)
    )
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()
    if not event:
        raise ValueError(f"Event {event_id} not found")

    if event.sync_status != PENDING_PUSH:
        return {"action": "noop", "external_id": event.external_id}

    if not event.calendar_integration_id:
        logger.warning("Event %d has no integration, cannot push", event_id)
        return {"action": "noop", "external_id": None}

    # Load integration
    stmt = select(models.CalendarIntegration).where(
        models.CalendarIntegration.id == event.calendar_integration_id
    )
    result = await db.execute(stmt)
    integration = result.scalar_one_or_none()
    if not integration:
        raise ValueError(f"Integration {event.calendar_integration_id} not found")

    # Connect to iCloud
    password = decrypt_password(integration.encrypted_password)
    client, principal = caldav_client.connect_icloud(integration.email, password)

    # Use the first selected calendar for push (or the calendar the event came from)
    selected_cals = integration.selected_calendars or []
    if not selected_cals:
        raise ValueError("No calendars selected for integration")
    calendar = caldav_client.get_calendar_by_url(principal, selected_cals[0])

    event_data = {
        "title": event.title,
        "description": event.description,
        "date": event.date,
        "start_time": event.start_time,
        "end_time": event.end_time,
        "all_day": event.all_day,
        "external_id": event.external_id,
    }

    if event.external_id:
        # Update existing remote event
        caldav_client.update_remote_event(calendar, event.external_id, event_data, tz=tz)
        event.sync_status = SYNCED
        await db.commit()
        return {"action": "updated", "external_id": event.external_id}
    else:
        # Create new remote event
        uid = caldav_client.create_remote_event(calendar, event_data, tz=tz)
        event.external_id = uid
        event.sync_status = SYNCED
        await db.commit()
        return {"action": "created", "external_id": uid}


async def push_delete_to_icloud(
    db: AsyncSession, external_id: str, integration_id: int
) -> dict:
    """Push a delete to iCloud when user deletes a synced event locally.

    The local event is already gone — this just removes the remote copy.
    Returns: {action: "deleted"}
    """
    # Load integration
    stmt = select(models.CalendarIntegration).where(
        models.CalendarIntegration.id == integration_id
    )
    result = await db.execute(stmt)
    integration = result.scalar_one_or_none()
    if not integration:
        raise ValueError(f"Integration {integration_id} not found")

    password = decrypt_password(integration.encrypted_password)
    client, principal = caldav_client.connect_icloud(integration.email, password)

    # Try each selected calendar to find and delete the event
    selected_cals = integration.selected_calendars or []
    for cal_url in selected_cals:
        try:
            calendar = caldav_client.get_calendar_by_url(principal, cal_url)
            caldav_client.delete_remote_event(calendar, external_id)
            logger.info(
                "Deleted remote event external_id=%s from calendar %s",
                external_id,
                cal_url,
            )
            return {"action": "deleted"}
        except Exception:
            continue  # Event might be in a different calendar

    logger.warning(
        "Could not find remote event external_id=%s in any selected calendar",
        external_id,
    )
    return {"action": "not_found"}
