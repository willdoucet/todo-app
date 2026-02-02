from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from . import models, schemas


async def get_lists(db: AsyncSession, skip: int = 0, limit: int = 10):
    stmt = select(models.List).offset(skip).limit(limit).order_by(models.List.name)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_list(db: AsyncSession, list_id: int):
    stmt = select(models.List).where(models.List.id == list_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_list(db: AsyncSession, list: schemas.ListCreate):
    db_list = models.List(**list.model_dump())
    db.add(db_list)
    await db.commit()
    await db.refresh(db_list)
    return db_list


async def update_list(db: AsyncSession, list_id: int, list: schemas.ListUpdate):
    stmt = (
        update(models.List)
        .where(models.List.id == list_id)
        .values(**list.model_dump(exclude_unset=True))
    )
    result = await db.execute(stmt)
    if result.rowcount == 0:
        return None

    await db.commit()
    return await get_list(db, list_id)


async def delete_list(db: AsyncSession, list_id: int):
    stmt = delete(models.List).where(models.List.id == list_id)
    await db.execute(stmt)
    await db.commit()
