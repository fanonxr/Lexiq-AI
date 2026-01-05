"""Cleanup Celery tasks."""

import logging
from datetime import datetime, timedelta, timezone

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    name="integration_worker.tasks.cleanup.cleanup_old_sync_logs",
)
def cleanup_old_sync_logs() -> dict:
    """
    Clean up old sync logs (older than 30 days).
    
    This task is triggered by Celery Beat daily at 2:00 AM.
    """
    # TODO: Implement when sync logs table is added
    logger.info("Placeholder: Would clean up old sync logs")
    return {"deleted": 0}

