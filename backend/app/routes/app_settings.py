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
    update_data = update.model_dump(exclude_unset=True)

    # If mealboard_shopping_list_id is changing, route through the atomic
    # domain service (handles swap/unlink/link with side effects).
    if "mealboard_shopping_list_id" in update_data:
        new_list_id = update_data.pop("mealboard_shopping_list_id")
        from ..services.shopping_sync import change_mealboard_list
        await change_mealboard_list(db, new_list_id)

    # Apply remaining fields via generic CRUD (stateless mutations)
    if update_data:
        remaining_update = schemas.AppSettingsUpdate(**update_data)
        await crud_app_settings.update_settings(db, remaining_update)

    # Return fresh settings
    settings = await crud_app_settings.get_settings(db)
    return settings


@router.get("/timezones", response_model=list[str])
async def list_timezones():
    return _COMMON_TIMEZONES
