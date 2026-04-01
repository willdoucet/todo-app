"""Two-way sync engine for iCloud Reminders (VTODO) integration.

Pull: remote iCloud VTODOs → local Tasks
Push: local task edits → remote iCloud VTODOs
Conflict: last-write-wins (same as calendar sync)

Key differences from calendar sync:
- No date-range windowing — fetch all incomplete + completed in last 30 days
- Lists auto-created (always new, never merge with existing local lists)
- Subtask parent resolution via RELATED-TO → parent_external_id → parent_id FK (two-pass)
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models
from . import caldav_client
from .sync_base import SYNCED, PENDING_PUSH, load_integration_with_credentials, get_calendar_rows

logger = logging.getLogger(__name__)


async def pull_reminders_from_icloud(db: AsyncSession, integration_id: int) -> dict:
    """Pull VTODOs from iCloud into local Tasks.

    Returns: {created: int, updated: int, deleted: int, skipped: int, errors: int}
    """
    integration, client, principal = await load_integration_with_credentials(
        db, integration_id
    )

    stats = {"created": 0, "updated": 0, "deleted": 0, "skipped": 0, "errors": 0}
    seen_external_ids = set()

    cal_rows = await get_calendar_rows(db, integration, is_todo=True)
    for cal_row in cal_rows:
        try:
            calendar = caldav_client.get_calendar_by_url(principal, cal_row.calendar_url)
            remote_todos = caldav_client.fetch_todos(calendar)

            # Update Calendar name/color from iCloud metadata
            try:
                reminder_lists = caldav_client.list_reminder_lists(principal)
                cal_info = next(
                    (c for c in reminder_lists if c["url"] == cal_row.calendar_url),
                    None,
                )
                if cal_info:
                    if cal_info["name"] and cal_info["name"] != cal_row.name:
                        cal_row.name = cal_info["name"]
                    if cal_info.get("color") != cal_row.color:
                        cal_row.color = cal_info.get("color")
            except Exception:
                pass

        except Exception:
            logger.error(
                "Failed to fetch todos from reminder list %s",
                cal_row.calendar_url,
                exc_info=True,
            )
            stats["errors"] += 1
            continue

        # Ensure a local List exists for this reminder list
        local_list = await _ensure_list_for_calendar(
            db, integration, cal_row
        )

        # Two-pass sync: first create/update all tasks, then resolve parent links
        tasks_needing_parent = []

        for remote in remote_todos:
            external_id = remote["external_id"]
            seen_external_ids.add(external_id)

            try:
                parent_ext_id = remote.pop("parent_external_id", None)
                task = await _sync_single_todo(
                    db, integration, remote, local_list, stats
                )
                if parent_ext_id and task:
                    tasks_needing_parent.append((task, parent_ext_id))
            except Exception:
                logger.error(
                    "Failed to sync todo external_id=%s",
                    external_id,
                    exc_info=True,
                )
                stats["errors"] += 1

        # Second pass: resolve parent_id from parent_external_id
        for task, parent_ext_id in tasks_needing_parent:
            try:
                stmt = select(models.Task).where(
                    models.Task.external_id == parent_ext_id,
                    models.Task.calendar_integration_id == integration.id,
                )
                result = await db.execute(stmt)
                parent = result.scalar_one_or_none()
                if parent and task.parent_id != parent.id:
                    task.parent_id = parent.id
            except Exception:
                logger.warning(
                    "Failed to resolve parent %s for task %s",
                    parent_ext_id,
                    task.external_id,
                )

    # Detect remote deletions
    await _detect_remote_todo_deletions(
        db, integration_id, seen_external_ids, stats
    )

    await db.commit()
    return stats


async def _ensure_list_for_calendar(
    db: AsyncSession,
    integration: models.CalendarIntegration,
    cal_row: models.Calendar,
) -> models.List:
    """Ensure a local List exists for a synced reminder list."""
    # Check if list already exists by external_id
    stmt = select(models.List).where(
        models.List.external_id == cal_row.calendar_url,
        models.List.calendar_integration_id == integration.id,
    )
    result = await db.execute(stmt)
    local_list = result.scalar_one_or_none()

    if local_list:
        # Update name if changed
        if cal_row.name and local_list.name != cal_row.name:
            local_list.name = cal_row.name
        return local_list

    # Create new list
    local_list = models.List(
        name=cal_row.name or "Reminders",
        color=cal_row.color,
        external_id=cal_row.calendar_url,
        calendar_integration_id=integration.id,
    )
    db.add(local_list)
    await db.flush()
    return local_list


async def _sync_single_todo(
    db: AsyncSession,
    integration: models.CalendarIntegration,
    remote: dict,
    local_list: models.List,
    stats: dict,
) -> models.Task | None:
    """Sync a single remote VTODO into the local DB. Returns the task."""
    external_id = remote["external_id"]

    # Look up existing local task
    stmt = select(models.Task).where(
        models.Task.external_id == external_id,
        models.Task.calendar_integration_id == integration.id,
    )
    result = await db.execute(stmt)
    local_task = result.scalar_one_or_none()

    if local_task is None:
        # New task — create locally
        db_task = models.Task(
            title=remote["title"],
            description=remote.get("description"),
            due_date=remote.get("due_date"),
            priority=remote.get("priority", 0),
            completed=remote.get("completed", False),
            completed_at=remote.get("completed_at"),
            assigned_to=integration.family_member_id,
            list_id=local_list.id,
            external_id=external_id,
            etag=remote.get("etag"),
            last_modified_remote=remote.get("last_modified_remote"),
            sync_status=SYNCED,
            calendar_integration_id=integration.id,
        )
        db.add(db_task)
        await db.flush()
        stats["created"] += 1
        return db_task

    # Existing task — check if we need to update
    if local_task.sync_status == PENDING_PUSH:
        _resolve_conflict(local_task, remote, stats)
        return local_task

    # Compare modification times
    remote_modified = remote.get("last_modified_remote")
    local_modified = local_task.last_modified_remote

    if remote_modified and local_modified and remote_modified <= local_modified:
        if remote.get("etag") and remote["etag"] != local_task.etag:
            local_task.etag = remote["etag"]
        stats["skipped"] += 1
        return local_task

    # Remote is newer — update local fields
    _update_local_task_from_remote(local_task, remote)
    stats["updated"] += 1
    return local_task


def _update_local_task_from_remote(local_task: models.Task, remote: dict) -> None:
    """Update local task fields from remote VTODO data."""
    local_task.title = remote["title"]
    local_task.description = remote.get("description")
    local_task.due_date = remote.get("due_date")
    local_task.priority = remote.get("priority", 0)
    local_task.completed = remote.get("completed", False)
    local_task.completed_at = remote.get("completed_at")
    local_task.etag = remote.get("etag")
    local_task.last_modified_remote = remote.get("last_modified_remote")
    local_task.sync_status = SYNCED


def _resolve_conflict(local_task: models.Task, remote: dict, stats: dict) -> None:
    """Resolve conflict — last-write-wins."""
    remote_modified = remote.get("last_modified_remote")
    local_modified = local_task.updated_at

    if local_modified and remote_modified:
        if remote_modified > local_modified:
            _update_local_task_from_remote(local_task, remote)
            stats["updated"] += 1
        else:
            stats["skipped"] += 1
    else:
        _update_local_task_from_remote(local_task, remote)
        stats["updated"] += 1


async def _detect_remote_todo_deletions(
    db: AsyncSession,
    integration_id: int,
    seen_external_ids: set,
    stats: dict,
) -> None:
    """Delete local tasks that were removed from iCloud Reminders."""
    stmt = select(models.Task).where(
        models.Task.calendar_integration_id == integration_id,
        models.Task.external_id.isnot(None),
    )
    result = await db.execute(stmt)
    local_tasks = result.scalars().all()

    for task in local_tasks:
        if task.external_id and task.external_id not in seen_external_ids:
            if task.sync_status == PENDING_PUSH:
                logger.info(
                    "Remote deleted task '%s' but has PENDING_PUSH, keeping",
                    task.title,
                )
                continue
            logger.info(
                "Remote deletion detected for task '%s' (external_id=%s)",
                task.title,
                task.external_id,
            )
            await db.delete(task)
            stats["deleted"] += 1


async def push_task_to_icloud(db: AsyncSession, task_id: int) -> dict:
    """Push a single local task change to iCloud as VTODO.

    Returns: {action: "updated" | "created" | "noop", external_id: str | None}
    """
    stmt = select(models.Task).where(models.Task.id == task_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    if not task:
        raise ValueError(f"Task {task_id} not found")

    if task.sync_status != PENDING_PUSH:
        return {"action": "noop", "external_id": task.external_id}

    if not task.calendar_integration_id:
        logger.warning("Task %d has no integration, cannot push", task_id)
        return {"action": "noop", "external_id": None}

    integration, client, principal = await load_integration_with_credentials(
        db, task.calendar_integration_id
    )

    # Find the reminder list for this task's list
    target_cal_url = None
    if task.list_id:
        stmt = select(models.List).where(models.List.id == task.list_id)
        result = await db.execute(stmt)
        task_list = result.scalar_one_or_none()
        if task_list and task_list.external_id:
            target_cal_url = task_list.external_id

    if not target_cal_url:
        # Fall back to Calendar rows
        cal_rows = await get_calendar_rows(db, integration, is_todo=True)
        if cal_rows:
            target_cal_url = cal_rows[0].calendar_url

    if not target_cal_url:
        raise ValueError("No reminder list available for push")

    # Get parent external_id for RELATED-TO
    parent_external_id = None
    if task.parent_id:
        parent = await db.get(models.Task, task.parent_id)
        if parent:
            parent_external_id = parent.external_id

    task_data = {
        "title": task.title,
        "description": task.description,
        "due_date": task.due_date,
        "priority": task.priority,
        "completed": task.completed,
        "completed_at": task.completed_at,
        "external_id": task.external_id,
        "parent_external_id": parent_external_id,
    }

    calendar = caldav_client.get_calendar_by_url(principal, target_cal_url)

    if task.external_id:
        # Update existing
        try:
            caldav_client.update_remote_todo(calendar, task.external_id, task_data)
            task.sync_status = SYNCED
            await db.commit()
            return {"action": "updated", "external_id": task.external_id}
        except Exception:
            # Try all reminder calendars
            cal_rows = await get_calendar_rows(db, integration, is_todo=True)
            for cal_row in cal_rows:
                if cal_row.calendar_url == target_cal_url:
                    continue
                try:
                    cal = caldav_client.get_calendar_by_url(principal, cal_row.calendar_url)
                    caldav_client.update_remote_todo(cal, task.external_id, task_data)
                    task.sync_status = SYNCED
                    await db.commit()
                    return {"action": "updated", "external_id": task.external_id}
                except Exception:
                    continue
            raise ValueError(
                f"Could not find todo UID={task.external_id} in any reminder list"
            )
    else:
        # Create new
        uid = caldav_client.create_remote_todo(calendar, task_data)
        task.external_id = uid
        task.sync_status = SYNCED
        await db.commit()
        return {"action": "created", "external_id": uid}


async def push_task_delete_to_icloud(
    db: AsyncSession, external_id: str, integration_id: int
) -> dict:
    """Push a delete to iCloud when user deletes a synced task locally."""
    integration, client, principal = await load_integration_with_credentials(
        db, integration_id
    )

    cal_rows = await get_calendar_rows(db, integration, is_todo=True)

    for cal_row in cal_rows:
        try:
            calendar = caldav_client.get_calendar_by_url(principal, cal_row.calendar_url)
            caldav_client.delete_remote_todo(calendar, external_id)
            logger.info(
                "Deleted remote todo external_id=%s from list %s",
                external_id,
                cal_row.calendar_url,
            )
            return {"action": "deleted"}
        except Exception:
            continue

    logger.warning(
        "Could not find remote todo external_id=%s in any reminder list",
        external_id,
    )
    return {"action": "not_found"}
