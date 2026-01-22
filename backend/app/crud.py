from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from . import models, schemas


async def get_todos(db: AsyncSession, skip: int = 0, limit: int = 10):
    stmt = (
        select(models.Todo)
        .offset(skip)
        .limit(limit)
        .order_by(models.Todo.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_todo(db: AsyncSession, todo_id: int):
    stmt = select(models.Todo).where(models.Todo.id == todo_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_todo(db: AsyncSession, todo: schemas.TodoCreate):
    db_todo = models.Todo(**todo.model_dump())
    db.add(db_todo)
    await db.commit()
    await db.refresh(db_todo)
    return db_todo


async def update_todo(db: AsyncSession, todo_id: int, todo: schemas.TodoUpdate):
    stmt = (
        update(models.Todo)
        .where(models.Todo.id == todo_id)
        .values(**todo.model_dump(exclude_unset=True))
        .returning(models.Todo)
    )
    result = await db.execute(stmt)
    updated_todo = result.scalar_one_or_none()
    if updated_todo:
        await db.commit()
        await db.refresh(updated_todo)
    return updated_todo


async def delete_todo(db: AsyncSession, todo_id: int):
    stmt = select(models.Todo).where(models.Todo.id == todo_id)
    result = await db.execute(stmt)
    todo = result.scalar_one_or_none()
    if todo:
        await db.delete(todo)
        await db.commit()
    return todo
