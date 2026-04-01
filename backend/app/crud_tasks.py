from datetime import date, datetime, time, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from . import models, schemas


def _children_2_levels():
    """Eager-load children 2 levels deep."""
    return selectinload(models.Task.children).selectinload(models.Task.children)


async def get_tasks(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    list_id: int = None,
    start_date: date = None,
    end_date: date = None,
    assigned_to: int = None,
):
    stmt = (
        select(models.Task)
        .options(selectinload(models.Task.family_member))
        .options(selectinload(models.Task.list))
        .options(selectinload(models.Task.section))
        .options(_children_2_levels())
    )
    # Only return root-level tasks when fetching by list — children are nested via eager-load
    if list_id is not None:
        stmt = stmt.where(models.Task.list_id == list_id)
        stmt = stmt.where(models.Task.parent_id.is_(None))
    if start_date is not None:
        stmt = stmt.where(models.Task.due_date >= datetime.combine(start_date, time.min))
    if end_date is not None:
        stmt = stmt.where(models.Task.due_date <= datetime.combine(end_date, time(23, 59, 59)))
    if assigned_to is not None:
        stmt = stmt.where(models.Task.assigned_to == assigned_to)

    stmt = stmt.offset(skip).limit(limit).order_by(models.Task.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_task(db: AsyncSession, task_id: int):
    stmt = (
        select(models.Task)
        .options(selectinload(models.Task.family_member))
        .options(selectinload(models.Task.section))
        .options(_children_2_levels())
        .where(models.Task.id == task_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _validate_parent_id(db: AsyncSession, parent_id: int, list_id: int, task_id: int = None):
    """Validate parent is in same list and no cycle is created."""
    parent = await db.get(models.Task, parent_id)
    if not parent:
        raise HTTPException(status_code=400, detail="Parent task not found")
    if parent.list_id != list_id:
        raise HTTPException(status_code=400, detail="Parent task must be in the same list")

    # Cycle detection: walk ancestor chain
    if task_id is not None:
        current_id = parent_id
        for _ in range(50):
            if current_id == task_id:
                raise HTTPException(status_code=400, detail="Cycle detected in subtask hierarchy")
            ancestor = await db.get(models.Task, current_id)
            if ancestor is None or ancestor.parent_id is None:
                break
            current_id = ancestor.parent_id


async def _validate_section_id(db: AsyncSession, section_id: int, list_id: int):
    """Validate section belongs to the same list."""
    section = await db.get(models.Section, section_id)
    if not section:
        raise HTTPException(status_code=400, detail="Section not found")
    if section.list_id != list_id:
        raise HTTPException(status_code=400, detail="Section must belong to the same list")


async def create_task(db: AsyncSession, task: schemas.TaskCreate):
    data = task.model_dump()

    # Validate parent_id cross-list
    if data.get("parent_id"):
        await _validate_parent_id(db, data["parent_id"], data["list_id"])

    # Validate section_id cross-list
    if data.get("section_id"):
        await _validate_section_id(db, data["section_id"], data["list_id"])

    # If the list is synced, inherit sync metadata so the task pushes to iCloud
    task_list = await db.get(models.List, data["list_id"])
    if task_list and task_list.calendar_integration_id:
        data["calendar_integration_id"] = task_list.calendar_integration_id
        data["sync_status"] = "PENDING_PUSH"

    db_task = models.Task(**data)
    db.add(db_task)
    await db.commit()

    # Push new task to iCloud as VTODO
    if db_task.calendar_integration_id and db_task.sync_status == "PENDING_PUSH":
        try:
            from .tasks import push_task_to_icloud_task
            push_task_to_icloud_task.apply_async(args=[db_task.id], countdown=30)
        except (ImportError, ConnectionError, OSError):
            pass  # Celery not available — push will happen on next pull

    return await get_task(db, db_task.id)


async def update_task(db: AsyncSession, task_id: int, task: schemas.TaskUpdate):
    """Load-modify-save pattern with validation."""
    db_task = await get_task(db, task_id)
    if not db_task:
        return None

    update_data = task.model_dump(exclude_unset=True)
    effective_list_id = update_data.get("list_id", db_task.list_id)

    # Validate parent_id
    if "parent_id" in update_data and update_data["parent_id"] is not None:
        await _validate_parent_id(db, update_data["parent_id"], effective_list_id, task_id)

    # Validate section_id
    if "section_id" in update_data and update_data["section_id"] is not None:
        await _validate_section_id(db, update_data["section_id"], effective_list_id)

    # Auto-set completed_at
    if "completed" in update_data:
        if update_data["completed"] and not db_task.completed:
            update_data["completed_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
        elif not update_data["completed"] and db_task.completed:
            update_data["completed_at"] = None

    for field, value in update_data.items():
        setattr(db_task, field, value)

    # CRUD-level push trigger for synced tasks
    if db_task.external_id and db_task.calendar_integration_id:
        db_task.sync_status = "PENDING_PUSH"
        await db.commit()
        try:
            from .tasks import push_task_to_icloud_task
            push_task_to_icloud_task.apply_async(args=[task_id], countdown=30)
        except (ImportError, ConnectionError, OSError):
            pass  # Celery not available (e.g. in tests) — push will happen on next pull
    else:
        await db.commit()

    return await get_task(db, task_id)


async def delete_task(db: AsyncSession, task_id: int):
    stmt = (
        select(models.Task)
        .options(selectinload(models.Task.family_member))
        .where(models.Task.id == task_id)
    )
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    if task:
        # CRUD-level push trigger for synced task deletion
        external_id = task.external_id
        integration_id = task.calendar_integration_id
        await db.delete(task)
        await db.commit()
        if external_id and integration_id:
            try:
                from .tasks import push_task_delete_to_icloud_task
                push_task_delete_to_icloud_task.apply_async(
                    args=[external_id, integration_id], countdown=30
                )
            except (ImportError, ConnectionError, OSError):
                pass  # Celery not available — delete will be detected on next pull
    return task
