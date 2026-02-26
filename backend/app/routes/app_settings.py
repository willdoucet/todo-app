from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from zoneinfo import available_timezones

from .. import schemas, crud_app_settings
from ..database import get_db

router = APIRouter(
    prefix="/app-settings",
    tags=["app-settings"],
)

# Pre-compute sorted timezone list once at import time
_COMMON_TIMEZONES = sorted(available_timezones())


@router.get("/", response_model=schemas.AppSettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)):
    settings = await crud_app_settings.get_settings(db)
    return settings


@router.patch("/", response_model=schemas.AppSettingsResponse)
async def update_settings(
    update: schemas.AppSettingsUpdate,
    db: AsyncSession = Depends(get_db),
):
    settings = await crud_app_settings.update_settings(db, update)
    return settings


@router.get("/timezones", response_model=list[str])
async def list_timezones():
    return _COMMON_TIMEZONES
