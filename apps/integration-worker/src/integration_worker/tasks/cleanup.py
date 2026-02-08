"""Cleanup Celery tasks."""

import logging
from datetime import datetime, timedelta, timezone

import httpx
from celery import shared_task

from integration_worker.config import get_settings

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


@shared_task(
    name="integration_worker.tasks.cleanup.cleanup_orphaned_resources",
)
def cleanup_orphaned_resources() -> dict:
    """
    Trigger api-core orphan cleanup (Twilio subaccounts, phone number pool).

    Calls api-core POST /api/v1/jobs/cleanup-orphaned-resources with internal API key.
    Runs every 30 minutes via Celery Beat.
    """
    settings = get_settings()
    url = f"{settings.api_core.url.rstrip('/')}/api/v1/jobs/cleanup-orphaned-resources"
    headers = {}
    if settings.api_core.api_key:
        headers["X-Internal-API-Key"] = settings.api_core.api_key
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers or None)
            response.raise_for_status()
            result = response.json()
            logger.info("Orphan cleanup completed", extra=result)
            return result
    except httpx.HTTPStatusError as e:
        logger.warning(
            f"Orphan cleanup API returned {e.response.status_code}: {e.response.text}. Continuing."
        )
        return {
            "twilio_subaccounts_closed": 0,
            "pool_numbers_reclaimed": 0,
            "qdrant_collections_deleted": 0,
            "redis_conversation_keys_deleted": 0,
            "orphan_user_data_deleted": 0,
            "error": str(e),
        }
    except Exception as e:
        logger.warning(f"Orphan cleanup request failed: {e}. Continuing.", exc_info=True)
        return {
            "twilio_subaccounts_closed": 0,
            "pool_numbers_reclaimed": 0,
            "qdrant_collections_deleted": 0,
            "redis_conversation_keys_deleted": 0,
            "orphan_user_data_deleted": 0,
            "error": str(e),
        }

