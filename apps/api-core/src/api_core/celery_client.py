"""Celery client for sending tasks to integration-worker.

This module provides a Celery app instance that can send tasks to the integration-worker
without requiring the integration-worker package to be installed in api-core.
"""

try:
    from celery import Celery
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    Celery = None  # type: ignore

from api_core.config import get_settings

settings = get_settings()

# Create a minimal Celery app for sending tasks
# This doesn't need to include the task modules - it just sends tasks to the broker
if CELERY_AVAILABLE:
    celery_app = Celery(
        "api_core_celery_client",
        broker=settings.redis.url,
        backend=settings.redis.url,
    )

    # Configure the client
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        result_expires=3600,  # 1 hour
    )
else:
    celery_app = None  # type: ignore


def send_calendar_sync_task(
    integration_type: str,
    integration_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    """
    Send a calendar sync task to the integration-worker.
    
    Args:
        integration_type: "outlook" or "google"
        integration_id: Calendar integration ID
        start_date: Optional start date (ISO format)
        end_date: Optional end date (ISO format)
        
    Returns:
        Task ID
        
    Raises:
        ImportError: If Celery is not installed
        ValueError: If integration_type is not supported
        RuntimeError: If Celery app is not initialized
    """
    if not CELERY_AVAILABLE:
        raise ImportError(
            "Celery is not installed. Please install it with: pip install celery==5.3.0"
        )
    
    if celery_app is None:
        raise RuntimeError("Celery app is not initialized")
    
    if integration_type == "outlook":
        task_name = "integration_worker.tasks.calendar_sync.sync_outlook_calendar"
    elif integration_type == "google":
        task_name = "integration_worker.tasks.calendar_sync.sync_google_calendar"
    else:
        raise ValueError(f"Unsupported integration type: {integration_type}")
    
    # Send task by name (no import needed)
    task = celery_app.send_task(
        task_name,
        args=[integration_id],
        kwargs={
            "start_date": start_date,
            "end_date": end_date,
        },
    )
    
    return task.id


def send_usage_aggregation_task(
    user_id: str,
    period_start: str | None = None,
    period_end: str | None = None,
) -> str:
    """
    Send a usage aggregation task to the integration-worker.
    
    Aggregates call minutes for a user within a billing period.
    If period_start and period_end are not provided, the task will
    use the user's active subscription billing period.
    
    Args:
        user_id: User ID
        period_start: Optional billing period start date (ISO format)
        period_end: Optional billing period end date (ISO format)
        
    Returns:
        Task ID
        
    Raises:
        ImportError: If Celery is not installed
        RuntimeError: If Celery app is not initialized
    """
    if not CELERY_AVAILABLE:
        raise ImportError(
            "Celery is not installed. Please install it with: pip install celery==5.3.0"
        )
    
    if celery_app is None:
        raise RuntimeError("Celery app is not initialized")
    
    task_name = "integration_worker.tasks.usage_aggregation.aggregate_call_minutes_for_user"
    
    # Send task by name (no import needed)
    task = celery_app.send_task(
        task_name,
        args=[user_id],
        kwargs={
            "period_start": period_start,
            "period_end": period_end,
        },
    )
    
    return task.id


def send_trial_check_task(user_id: str) -> str:
    """
    Send a trial check task to the integration-worker.
    
    Checks if a user's trial subscription should end early due to usage limits.
    
    Args:
        user_id: User ID
        
    Returns:
        Task ID
        
    Raises:
        ImportError: If Celery is not installed
        RuntimeError: If Celery app is not initialized
    """
    if not CELERY_AVAILABLE:
        raise ImportError(
            "Celery is not installed. Please install it with: pip install celery==5.3.0"
        )
    
    if celery_app is None:
        raise RuntimeError("Celery app is not initialized")
    
    task_name = "integration_worker.tasks.trial_monitoring.check_trial_for_user"
    
    # Send task by name (no import needed)
    task = celery_app.send_task(
        task_name,
        args=[user_id],
    )
    
    return task.id

