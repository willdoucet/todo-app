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
