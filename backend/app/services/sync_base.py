"""Shared sync helpers used by both calendar and reminders sync engines."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .. import models
from ..utils.encryption import decrypt_password
from . import caldav_client

logger = logging.getLogger(__name__)

# Sync status constants
SYNCED = "SYNCED"
PENDING_PUSH = "PENDING_PUSH"


async def load_integration_with_credentials(db: AsyncSession, integration_id: int):
    """Load integration, decrypt password, connect to iCloud.

    Returns: (integration, client, principal)
    """
    stmt = (
        select(models.CalendarIntegration)
        .options(selectinload(models.CalendarIntegration.calendars))
        .where(models.CalendarIntegration.id == integration_id)
    )
    result = await db.execute(stmt)
    integration = result.scalar_one_or_none()
    if not integration:
        raise ValueError(f"Integration {integration_id} not found")

    password = decrypt_password(integration.encrypted_password)
    client, principal = caldav_client.connect_icloud(integration.email, password)
    return integration, client, principal


async def update_sync_status(
    db: AsyncSession,
    integration_id: int,
    status: models.IntegrationStatus,
    error: str | None = None,
    field_prefix: str = "",
):
    """Update integration sync status fields.

    field_prefix: "" for calendar status, "reminders_" for reminders status.
    """
    stmt = select(models.CalendarIntegration).where(
        models.CalendarIntegration.id == integration_id
    )
    result = await db.execute(stmt)
    integration = result.scalar_one_or_none()
    if not integration:
        return

    if field_prefix == "reminders_":
        integration.reminders_status = status
        if error is not None:
            integration.reminders_last_error = error
        elif status == models.IntegrationStatus.ACTIVE:
            integration.reminders_last_error = None
    else:
        integration.status = status
        if error is not None:
            integration.last_error = error
        elif status == models.IntegrationStatus.ACTIVE:
            integration.last_error = None

    await db.commit()


async def get_calendar_rows(
    db: AsyncSession,
    integration: models.CalendarIntegration,
    is_todo: bool = False,
) -> list[models.Calendar]:
    """Get Calendar rows for an integration, filtered by is_todo flag."""
    stmt = select(models.Calendar).where(
        models.Calendar.calendar_integration_id == integration.id,
        models.Calendar.is_todo == is_todo,
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()

    if rows:
        return list(rows)

    # Only do legacy fallback for event calendars (not reminders)
    if not is_todo:
        from ..crud_calendars import get_or_create_calendar
        selected_cals = integration.selected_calendars or []
        new_rows = []
        for cal_url in selected_cals:
            name = cal_url.rstrip("/").rsplit("/", 1)[-1] or cal_url
            row = await get_or_create_calendar(db, integration.id, cal_url, name)
            new_rows.append(row)
        return new_rows

    return []
