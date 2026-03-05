"""API endpoints for listing available calendars (for the event form dropdown)."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from .. import schemas, crud_calendars
from ..database import get_db

router = APIRouter(
    prefix="/calendars",
    tags=["calendars"],
)


@router.get("/", response_model=List[schemas.CalendarResponse])
async def list_calendars(db: AsyncSession = Depends(get_db)):
    """Get all calendars with family member and integration info for dropdown."""
    calendars = await crud_calendars.get_all_calendars(db)
    result = []
    for cal in calendars:
        result.append(
            schemas.CalendarResponse(
                id=cal.id,
                calendar_integration_id=cal.calendar_integration_id,
                calendar_url=cal.calendar_url,
                name=cal.name,
                color=cal.color,
                family_member_name=cal.integration.family_member.name if cal.integration and cal.integration.family_member else None,
                integration_email=cal.integration.email if cal.integration else None,
            )
        )
    return result
