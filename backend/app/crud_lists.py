from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from . import models, schemas


async def get_lists(db: AsyncSession, skip: int = 0, limit: int = 100):
    stmt = (
        select(models.List)
        .options(selectinload(models.List.sections))
        .offset(skip).limit(limit)
        .order_by(models.List.name)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_list(db: AsyncSession, list_id: int):
    stmt = (
        select(models.List)
        .options(selectinload(models.List.sections))
        .where(models.List.id == list_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_list(db: AsyncSession, list: schemas.ListCreate):
    db_list = models.List(**list.model_dump())
    db.add(db_list)
    await db.commit()
    await db.refresh(db_list)
    return await get_list(db, db_list.id)


async def update_list(db: AsyncSession, list_id: int, list: schemas.ListUpdate):
    db_list = await get_list(db, list_id)
    if not db_list:
        return None

    update_data = list.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_list, field, value)

    await db.commit()
    return await get_list(db, list_id)


async def delete_list(db: AsyncSession, list_id: int):
    db_list = await get_list(db, list_id)
    if not db_list:
        return False

    # Block deletion of synced lists
    if db_list.calendar_integration_id is not None:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a synced list. Disconnect Reminders in Settings first.",
        )

    stmt = delete(models.List).where(models.List.id == list_id)
    await db.execute(stmt)
    await db.commit()
    return True
