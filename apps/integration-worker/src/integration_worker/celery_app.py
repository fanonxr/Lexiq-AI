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
        "integration_worker.tasks.usage_aggregation",
        "integration_worker.tasks.billing_cycle",
        "integration_worker.tasks.trial_monitoring",
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
    # Aggregate call minutes for all active subscriptions daily
    "aggregate-all-usage": {
        "task": "integration_worker.tasks.usage_aggregation.aggregate_all_active_subscriptions",
        "schedule": crontab(hour=3, minute=0),  # Daily at 3:00 AM
    },
    # Process billing cycle end for subscriptions ending today
    "process-billing-cycles": {
        "task": "integration_worker.tasks.billing_cycle.process_daily_billing_cycles",
        "schedule": crontab(hour=4, minute=0),  # Daily at 4:00 AM (after usage aggregation)
    },
    # Check all active trial subscriptions for usage limits
    "check-all-trials": {
        "task": "integration_worker.tasks.trial_monitoring.check_all_trials",
        "schedule": crontab(minute="*/15"),  # Every 15 minutes
    },
    # Clean up orphaned resources (Twilio subaccounts, pool numbers) every 30 minutes
    "cleanup-orphaned-resources": {
        "task": "integration_worker.tasks.cleanup.cleanup_orphaned_resources",
        "schedule": crontab(minute="*/30"),  # Every 30 minutes
    },
}

if __name__ == "__main__":
    app.start()

