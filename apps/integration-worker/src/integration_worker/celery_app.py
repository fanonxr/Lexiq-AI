"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab

from integration_worker.config import get_settings

settings = get_settings()

# Create Celery app
app = Celery(
    "integration_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "integration_worker.tasks.calendar_sync",
        "integration_worker.tasks.token_refresh",
        "integration_worker.tasks.webhook_processing",
        "integration_worker.tasks.webhook_management",
        "integration_worker.tasks.cleanup",
    ],
)

# Celery configuration
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,  # 1 hour
)

# Celery Beat schedule (periodic tasks)
app.conf.beat_schedule = {
    # Sync all active calendar integrations every 15 minutes
    "sync-all-calendars": {
        "task": "integration_worker.tasks.calendar_sync.sync_all_calendars",
        "schedule": crontab(minute="*/15"),  # Every 15 minutes
    },
    # Refresh expiring tokens every hour
    "refresh-expiring-tokens": {
        "task": "integration_worker.tasks.token_refresh.refresh_expiring_tokens",
        "schedule": crontab(minute=0),  # Every hour at :00
    },
    # Renew expiring webhook subscriptions every 6 hours
    "renew-expiring-subscriptions": {
        "task": "integration_worker.tasks.webhook_management.renew_expiring_subscriptions",
        "schedule": crontab(minute=0, hour="*/6"),  # Every 6 hours
    },
    # Clean up old sync logs daily
    "cleanup-sync-logs": {
        "task": "integration_worker.tasks.cleanup.cleanup_old_sync_logs",
        "schedule": crontab(hour=2, minute=0),  # Daily at 2:00 AM
    },
}

if __name__ == "__main__":
    app.start()

