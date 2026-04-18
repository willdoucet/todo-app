import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "family_hub",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Per-task time limits. extract_recipe_from_url is I/O-heavy (HTTP fetch +
    # LLM call), so we cap it at 120s hard / 110s soft. The soft limit gives
    # the task a chance to raise SoftTimeLimitExceeded and mark itself failed
    # with a clean error before the hard kill.
    task_annotations={
        "app.tasks.extract_recipe_from_url": {
            "time_limit": 120,
            "soft_time_limit": 110,
        },
    },
    beat_schedule={
        "sync-icloud-calendars": {
            "task": "app.tasks.sync_all_icloud_integrations",
            "schedule": 600.0,  # Every 10 minutes
        },
        "sync-icloud-reminders": {
            "task": "app.tasks.sync_all_reminders",
            "schedule": 600.0,  # Every 10 minutes
        },
        "hard-delete-expired-soft-deletes": {
            "task": "app.tasks.hard_delete_expired_soft_deletes",
            "schedule": 3600.0,  # Every hour — sweeps items with deleted_at > 24h
        },
    },
)
