import asyncio
import logging

from .celery_app import celery_app
from .database import AsyncSessionLocal

logger = logging.getLogger(__name__)


def run_async(coro):
    """Run an async function from synchronous Celery task.

    Each call gets a fresh event loop. We must dispose the shared engine's
    connection pool before closing the loop, otherwise asyncpg connections
    from this loop leak into the next call and trigger
    "Future attached to a different loop".
    """
    from .database import engine

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        if engine is not None:
            loop.run_until_complete(engine.dispose())
        loop.close()


@celery_app.task(name="app.tasks.health_check")
def health_check():
    """Simple task to verify Celery is working."""
    logger.info("Celery health check: OK")
    return {"status": "ok"}


@celery_app.task(name="app.tasks.sync_all_icloud_integrations")
def sync_all_icloud_integrations():
    """Periodic task (every 10 min): sync all active iCloud integrations."""
    from . import models

    async def _sync_all():
        from .services.sync_engine import pull_from_icloud

        async with AsyncSessionLocal() as db:
            from sqlalchemy import select

            stmt = select(models.CalendarIntegration).where(
                models.CalendarIntegration.status == models.IntegrationStatus.ACTIVE
            )
            result = await db.execute(stmt)
            integrations = result.scalars().all()

        results = {}
        for integration in integrations:
            try:
                async with AsyncSessionLocal() as db:
                    stats = await pull_from_icloud(db, integration.id)
                    # Update last_sync_at
                    from sqlalchemy import select as sel, func

                    stmt = sel(models.CalendarIntegration).where(
                        models.CalendarIntegration.id == integration.id
                    )
                    res = await db.execute(stmt)
                    integ = res.scalar_one_or_none()
                    if integ:
                        integ.last_sync_at = func.now()
                        integ.status = models.IntegrationStatus.ACTIVE
                        integ.last_error = None
                        await db.commit()

                results[integration.id] = stats
                logger.info(
                    "Synced integration %d (%s): %s",
                    integration.id,
                    integration.email,
                    stats,
                )
            except Exception as e:
                logger.error(
                    "Failed to sync integration %d: %s",
                    integration.id,
                    str(e),
                    exc_info=True,
                )
                # Set status to ERROR
                try:
                    async with AsyncSessionLocal() as db:
                        stmt = sel(models.CalendarIntegration).where(
                            models.CalendarIntegration.id == integration.id
                        )
                        res = await db.execute(stmt)
                        integ = res.scalar_one_or_none()
                        if integ:
                            integ.status = models.IntegrationStatus.ERROR
                            integ.last_error = str(e)[:500]
                            await db.commit()
                except Exception:
                    logger.error(
                        "Failed to set error status for integration %d",
                        integration.id,
                        exc_info=True,
                    )
                results[integration.id] = {"error": str(e)}

        return results

    return run_async(_sync_all())


@celery_app.task(
    name="app.tasks.sync_single_integration",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def sync_single_integration(self, integration_id: int):
    """Sync a single integration. Used for initial sync + manual 'Sync Now'."""
    from . import models

    async def _sync():
        from .services.sync_engine import pull_from_icloud
        from sqlalchemy import select, func

        # Set status to SYNCING
        async with AsyncSessionLocal() as db:
            stmt = select(models.CalendarIntegration).where(
                models.CalendarIntegration.id == integration_id
            )
            result = await db.execute(stmt)
            integration = result.scalar_one_or_none()
            if not integration:
                return {"error": "integration_not_found"}
            integration.status = models.IntegrationStatus.SYNCING
            await db.commit()

        try:
            async with AsyncSessionLocal() as db:
                stats = await pull_from_icloud(db, integration_id)

            # Update status to ACTIVE + last_sync_at
            async with AsyncSessionLocal() as db:
                stmt = select(models.CalendarIntegration).where(
                    models.CalendarIntegration.id == integration_id
                )
                result = await db.execute(stmt)
                integration = result.scalar_one_or_none()
                if integration:
                    integration.status = models.IntegrationStatus.ACTIVE
                    integration.last_sync_at = func.now()
                    integration.last_error = None
                    await db.commit()

            logger.info("Single sync for integration %d: %s", integration_id, stats)
            return stats
        except Exception as e:
            # Set status to ERROR
            async with AsyncSessionLocal() as db:
                stmt = select(models.CalendarIntegration).where(
                    models.CalendarIntegration.id == integration_id
                )
                result = await db.execute(stmt)
                integration = result.scalar_one_or_none()
                if integration:
                    integration.status = models.IntegrationStatus.ERROR
                    integration.last_error = str(e)[:500]
                    await db.commit()

            logger.error(
                "Failed to sync integration %d: %s",
                integration_id,
                str(e),
                exc_info=True,
            )
            raise self.retry(exc=e)

    return run_async(_sync())


@celery_app.task(
    name="app.tasks.push_event_to_icloud",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
)
def push_event_to_icloud(self, event_id: int):
    """Push a single event change to iCloud.

    Called when user edits/creates an ICLOUD event locally.
    Retries with exponential backoff (10s, 20s, 40s).
    """

    async def _push():
        from .services.sync_engine import push_to_icloud

        async with AsyncSessionLocal() as db:
            return await push_to_icloud(db, event_id)

    try:
        result = run_async(_push())
        logger.info("Pushed event %d to iCloud: %s", event_id, result)
        return result
    except Exception as e:
        logger.error(
            "Failed to push event %d: %s", event_id, str(e), exc_info=True
        )
        raise self.retry(exc=e, countdown=self.default_retry_delay * (2 ** self.request.retries))


@celery_app.task(name="app.tasks.push_delete_to_icloud")
def push_delete_to_icloud(external_id: str, integration_id: int):
    """Push a delete to iCloud when user deletes a synced event."""

    async def _push_delete():
        from .services.sync_engine import push_delete_to_icloud as _push_del

        async with AsyncSessionLocal() as db:
            return await _push_del(db, external_id, integration_id)

    try:
        result = run_async(_push_delete())
        logger.info(
            "Pushed delete for external_id=%s: %s", external_id, result
        )
        return result
    except Exception as e:
        logger.error(
            "Failed to push delete for external_id=%s: %s",
            external_id,
            str(e),
            exc_info=True,
        )
        return {"error": str(e)}


@celery_app.task(
    name="app.tasks.move_event_on_icloud",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
)
def move_event_on_icloud(self, event_id: int, old_calendar_id: int, new_calendar_id: int):
    """Move an event between calendars on the same iCloud account.

    Retries with exponential backoff (10s, 20s, 40s).
    """

    async def _move():
        from .services.sync_engine import move_event_on_icloud as _move_fn

        async with AsyncSessionLocal() as db:
            return await _move_fn(db, event_id, old_calendar_id, new_calendar_id)

    try:
        result = run_async(_move())
        logger.info("Moved event %d: %s", event_id, result)
        return result
    except Exception as e:
        logger.error(
            "Failed to move event %d: %s", event_id, str(e), exc_info=True
        )
        raise self.retry(exc=e, countdown=self.default_retry_delay * (2 ** self.request.retries))


# =============================================================================
# Reminders sync tasks
# =============================================================================


@celery_app.task(name="app.tasks.sync_all_reminders")
def sync_all_reminders():
    """Periodic task: sync all integrations that have reminder lists."""
    from . import models

    async def _sync_all():
        from .services.reminders_sync_engine import pull_reminders_from_icloud
        from .services.sync_base import update_sync_status
        from sqlalchemy import select, func

        async with AsyncSessionLocal() as db:
            # Find integrations that have reminder Calendar rows (is_todo=True)
            stmt = (
                select(models.CalendarIntegration)
                .where(models.CalendarIntegration.reminders_status.isnot(None))
            )
            result = await db.execute(stmt)
            integrations = result.scalars().all()

        results = {}
        for integration in integrations:
            try:
                async with AsyncSessionLocal() as db:
                    stats = await pull_reminders_from_icloud(db, integration.id)
                    # Update reminders sync status
                    stmt = select(models.CalendarIntegration).where(
                        models.CalendarIntegration.id == integration.id
                    )
                    res = await db.execute(stmt)
                    integ = res.scalar_one_or_none()
                    if integ:
                        integ.reminders_status = models.IntegrationStatus.ACTIVE
                        integ.reminders_last_sync_at = func.now()
                        integ.reminders_last_error = None
                        await db.commit()

                results[integration.id] = stats
                logger.info(
                    "Synced reminders for integration %d: %s",
                    integration.id,
                    stats,
                )
            except Exception as e:
                logger.error(
                    "Failed to sync reminders for integration %d: %s",
                    integration.id,
                    str(e),
                    exc_info=True,
                )
                try:
                    async with AsyncSessionLocal() as db:
                        stmt = select(models.CalendarIntegration).where(
                            models.CalendarIntegration.id == integration.id
                        )
                        res = await db.execute(stmt)
                        integ = res.scalar_one_or_none()
                        if integ:
                            integ.reminders_status = models.IntegrationStatus.ERROR
                            integ.reminders_last_error = str(e)[:500]
                            await db.commit()
                except Exception:
                    pass
                results[integration.id] = {"error": str(e)}

        return results

    return run_async(_sync_all())


@celery_app.task(
    name="app.tasks.sync_single_reminders_integration",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def sync_single_reminders_integration(self, integration_id: int):
    """Sync reminders for a single integration. Used for initial + manual sync."""
    from . import models

    async def _sync():
        from .services.reminders_sync_engine import pull_reminders_from_icloud
        from sqlalchemy import select, func

        # Set reminders_status to SYNCING
        async with AsyncSessionLocal() as db:
            stmt = select(models.CalendarIntegration).where(
                models.CalendarIntegration.id == integration_id
            )
            result = await db.execute(stmt)
            integration = result.scalar_one_or_none()
            if not integration:
                return {"error": "integration_not_found"}
            integration.reminders_status = models.IntegrationStatus.SYNCING
            await db.commit()

        try:
            async with AsyncSessionLocal() as db:
                stats = await pull_reminders_from_icloud(db, integration_id)

            # Update status to ACTIVE
            async with AsyncSessionLocal() as db:
                stmt = select(models.CalendarIntegration).where(
                    models.CalendarIntegration.id == integration_id
                )
                result = await db.execute(stmt)
                integration = result.scalar_one_or_none()
                if integration:
                    integration.reminders_status = models.IntegrationStatus.ACTIVE
                    integration.reminders_last_sync_at = func.now()
                    integration.reminders_last_error = None
                    await db.commit()

            logger.info("Single reminders sync for integration %d: %s", integration_id, stats)
            return stats
        except Exception as e:
            async with AsyncSessionLocal() as db:
                stmt = select(models.CalendarIntegration).where(
                    models.CalendarIntegration.id == integration_id
                )
                result = await db.execute(stmt)
                integration = result.scalar_one_or_none()
                if integration:
                    integration.reminders_status = models.IntegrationStatus.ERROR
                    integration.reminders_last_error = str(e)[:500]
                    await db.commit()

            logger.error(
                "Failed to sync reminders for integration %d: %s",
                integration_id,
                str(e),
                exc_info=True,
            )
            raise self.retry(exc=e)

    return run_async(_sync())


@celery_app.task(
    name="app.tasks.push_task_to_icloud_task",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
)
def push_task_to_icloud_task(self, task_id: int):
    """Push a single task change to iCloud as VTODO."""

    async def _push():
        from .services.reminders_sync_engine import push_task_to_icloud

        async with AsyncSessionLocal() as db:
            return await push_task_to_icloud(db, task_id)

    try:
        result = run_async(_push())
        logger.info("Pushed task %d to iCloud: %s", task_id, result)
        return result
    except Exception as e:
        logger.error(
            "Failed to push task %d: %s", task_id, str(e), exc_info=True
        )
        raise self.retry(exc=e, countdown=self.default_retry_delay * (2 ** self.request.retries))


@celery_app.task(
    name="app.tasks.push_task_delete_to_icloud_task",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
)
def push_task_delete_to_icloud_task(self, external_id: str, integration_id: int):
    """Push a task delete to iCloud (remove VTODO). Retries on failure."""

    async def _push_delete():
        from .services.reminders_sync_engine import push_task_delete_to_icloud

        async with AsyncSessionLocal() as db:
            return await push_task_delete_to_icloud(db, external_id, integration_id)

    try:
        result = run_async(_push_delete())
        logger.info("Pushed task delete for external_id=%s: %s", external_id, result)
        return result
    except Exception as e:
        logger.error(
            "Failed to push task delete for external_id=%s: %s",
            external_id,
            str(e),
            exc_info=True,
        )
        raise self.retry(exc=e, countdown=self.default_retry_delay * (2 ** self.request.retries))


@celery_app.task(name="app.tasks.delete_events_for_integration")
def delete_events_for_integration(integration_id: int):
    """Delete all local events for a disconnected integration."""
    from . import models
    from sqlalchemy import delete

    async def _delete():
        async with AsyncSessionLocal() as db:
            stmt = delete(models.CalendarEvent).where(
                models.CalendarEvent.calendar_integration_id == integration_id
            )
            result = await db.execute(stmt)
            await db.commit()
            return {"deleted": result.rowcount}

    result = run_async(_delete())
    logger.info("Deleted events for integration %d: %s", integration_id, result)
    return result


# =============================================================================
# Shopping List Sync Tasks
# =============================================================================


@celery_app.task(
    name="app.tasks.sync_shopping_list_add",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
)
def sync_shopping_list_add(self, meal_entry_id: int):
    """Sync a meal entry's ingredients to the linked shopping list.

    Called after a meal entry is created. Aggregates ingredients with
    existing shopping items using the aggregation key + unique constraint.
    """
    from .services.shopping_sync import sync_meal_to_shopping_list
    from sqlalchemy import update
    from . import models

    async def _sync():
        async with AsyncSessionLocal() as db:
            await sync_meal_to_shopping_list(db, meal_entry_id)

    try:
        run_async(_sync())
        logger.info("Shopping sync (add) complete for meal entry %d", meal_entry_id)
    except Exception as e:
        logger.error(
            "Shopping sync (add) failed for meal entry %d: %s",
            meal_entry_id, str(e), exc_info=True,
        )
        # On final retry failure, mark the meal entry as "failed"
        if self.request.retries >= self.max_retries:
            async def _mark_failed():
                async with AsyncSessionLocal() as db:
                    await db.execute(
                        update(models.MealEntry)
                        .where(models.MealEntry.id == meal_entry_id)
                        .values(shopping_sync_status="failed")
                    )
                    await db.commit()
            try:
                run_async(_mark_failed())
            except Exception:
                logger.error("Failed to mark meal entry %d as sync failed", meal_entry_id)
        raise self.retry(exc=e, countdown=self.default_retry_delay * (2 ** self.request.retries))


@celery_app.task(
    name="app.tasks.sync_shopping_list_remove",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
)
def sync_shopping_list_remove(self, meal_entry_id: int, synced_to_list_id: int | None = None):
    """Remove a meal entry's contributions from the shopping list.

    Uses synced_to_list_id (provenance) to target the correct list.
    If None, no-op (meal was never synced or already cleaned up).
    """
    from .services.shopping_sync import remove_meal_from_shopping_list

    if synced_to_list_id is None:
        logger.info(
            "Shopping sync (remove) for meal entry %d — no synced_to_list_id, no-op",
            meal_entry_id,
        )
        return

    async def _remove():
        async with AsyncSessionLocal() as db:
            await remove_meal_from_shopping_list(db, meal_entry_id, target_list_id=synced_to_list_id)

    try:
        run_async(_remove())
        logger.info("Shopping sync (remove) complete for meal entry %d from list %d", meal_entry_id, synced_to_list_id)
    except Exception as e:
        logger.error(
            "Shopping sync (remove) failed for meal entry %d: %s",
            meal_entry_id, str(e), exc_info=True,
        )
        raise self.retry(exc=e, countdown=self.default_retry_delay * (2 ** self.request.retries))


# =============================================================================
# Chunk 6 — Soft-delete hard-delete sweeper (Expansion B)
# =============================================================================

@celery_app.task(
    name="app.tasks.hard_delete_expired_soft_deletes",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,  # cap exponential backoff at 10 minutes
    retry_jitter=True,
    max_retries=3,
)
def hard_delete_expired_soft_deletes(self):
    """Hourly sweeper that permanently removes items whose soft-delete window
    has expired (items.deleted_at older than 24 hours).

    Thin wrapper around `crud_items.hard_delete_expired_soft_deletes_async()`.
    The real cascade-in-code + assertion-gate logic lives there so tests can
    await it directly with their own db_session fixture.

    Failure handling: Celery autoretry kicks in for any exception (3 retries
    with exponential backoff). After exhaustion the task fails and Celery's
    next beat tick re-dispatches a fresh attempt at the next hour. A persistent
    failure logs `HARD_DELETE_SWEEP_DEAD_LETTER` so an operator can grep logs
    for the zombie-state condition (the assertion-gate from
    crud_items.hard_delete_expired_soft_deletes_async).
    """
    from .crud_items import hard_delete_expired_soft_deletes_async

    async def _sweep():
        async with AsyncSessionLocal() as db:
            return await hard_delete_expired_soft_deletes_async(db)

    try:
        deleted_count = run_async(_sweep())
        if deleted_count:
            logger.info(
                "Hard-delete sweep: removed %d expired soft-deleted items",
                deleted_count,
            )
        return {"deleted_count": deleted_count}
    except Exception as e:
        attempt = self.request.retries + 1
        if attempt > self.max_retries:
            logger.error(
                "HARD_DELETE_SWEEP_DEAD_LETTER attempts=%d error=%s",
                attempt, str(e), exc_info=True,
            )
        else:
            logger.warning(
                "Hard-delete sweep attempt %d/%d failed: %s",
                attempt, self.max_retries + 1, str(e),
            )
        raise
