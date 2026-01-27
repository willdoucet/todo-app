from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from . import models, schemas


async def get_tasks(db: AsyncSession, skip: int = 0, limit: int = 10):
    stmt = (
        select(models.Task)
        .options(selectinload(models.Task.family_member))
        .offset(skip)
        .limit(limit)
        .order_by(models.Task.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_task(db: AsyncSession, task_id: int):
    stmt = (
        select(models.Task)
        .options(selectinload(models.Task.family_member))
        .where(models.Task.id == task_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_task(db: AsyncSession, task: schemas.TaskCreate):
    db_task = models.Task(**task.model_dump())
    db.add(db_task)
    await db.commit()
    return await get_task(db, db_task.id)


async def update_task(db: AsyncSession, task_id: int, task: schemas.TaskUpdate):
    stmt = (
        update(models.Task)
        .where(models.Task.id == task_id)
        .values(**task.model_dump(exclude_unset=True))
    )
    result = await db.execute(stmt)
    if result.rowcount == 0:
        return None
    await db.commit()

    return await get_task(db, task_id)


async def delete_task(db: AsyncSession, task_id: int):
    stmt = select(models.Task).where(models.Task.id == task_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    if task:
        await db.delete(task)
        await db.commit()
    return task
