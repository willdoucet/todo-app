from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from . import models, schemas
from .utils.encryption import encrypt_password


async def get_integrations(
    db: AsyncSession, family_member_id: int = None
):
    """List all integrations, optionally filtered by family member."""
    stmt = (
        select(models.CalendarIntegration)
        .options(selectinload(models.CalendarIntegration.family_member), selectinload(models.CalendarIntegration.calendars))
    )
    if family_member_id is not None:
        stmt = stmt.where(
            models.CalendarIntegration.family_member_id == family_member_id
        )
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_integration(db: AsyncSession, integration_id: int):
    """Get a single integration by ID."""
    stmt = (
        select(models.CalendarIntegration)
        .options(selectinload(models.CalendarIntegration.family_member), selectinload(models.CalendarIntegration.calendars))
        .where(models.CalendarIntegration.id == integration_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_active_integrations(db: AsyncSession):
    """Get all integrations with ACTIVE status (for Celery beat sync)."""
    stmt = (
        select(models.CalendarIntegration)
        .where(
            models.CalendarIntegration.status == models.IntegrationStatus.ACTIVE
        )
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_integration(
    db: AsyncSession, integration: schemas.CalendarIntegrationCreate
):
    """Create a new integration with encrypted password and Calendar rows."""
    db_integration = models.CalendarIntegration(
        family_member_id=integration.family_member_id,
        provider="icloud",
        email=integration.email,
        encrypted_password=encrypt_password(integration.password),
        selected_calendars=integration.selected_calendars,
    )
    db.add(db_integration)
    await db.flush()  # Get the ID before creating Calendar rows

    # Create Calendar rows from calendar_details (preferred) or selected_calendars URLs
    cal_details = integration.calendar_details
    if cal_details:
        for detail in cal_details:
            cal = models.Calendar(
                calendar_integration_id=db_integration.id,
                calendar_url=detail["url"],
                name=detail.get("name", detail["url"].rstrip("/").rsplit("/", 1)[-1]),
                color=detail.get("color"),
            )
            db.add(cal)
    elif integration.selected_calendars:
        for cal_url in integration.selected_calendars:
            cal = models.Calendar(
                calendar_integration_id=db_integration.id,
                calendar_url=cal_url,
                name=cal_url.rstrip("/").rsplit("/", 1)[-1] or cal_url,
            )
            db.add(cal)

    await db.commit()
    return await get_integration(db, db_integration.id)


async def update_integration_status(
    db: AsyncSession,
    integration_id: int,
    status: models.IntegrationStatus,
    last_error: str = None,
):
    """Update integration status and optionally set error message."""
    integration = await get_integration(db, integration_id)
    if not integration:
        return None
    integration.status = status
    integration.last_error = last_error
    await db.commit()
    return await get_integration(db, integration_id)


async def update_integration_last_sync(db: AsyncSession, integration_id: int):
    """Update last_sync_at to current time."""
    from sqlalchemy import func

    integration = await get_integration(db, integration_id)
    if not integration:
        return None
    integration.last_sync_at = func.now()
    await db.commit()
    return await get_integration(db, integration_id)


async def delete_integration(db: AsyncSession, integration_id: int):
    """Delete integration and all its synced calendar events."""
    integration = await get_integration(db, integration_id)
    if not integration:
        return None
    # Delete all synced events for this integration
    await db.execute(
        delete(models.CalendarEvent).where(
            models.CalendarEvent.calendar_integration_id == integration_id
        )
    )
    await db.delete(integration)
    await db.commit()
    return integration
