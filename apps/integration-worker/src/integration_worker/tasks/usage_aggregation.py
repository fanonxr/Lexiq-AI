"""Usage aggregation Celery tasks for billing."""

import logging
from datetime import datetime, timedelta
from typing import Optional

from celery import shared_task
from sqlalchemy import select

from integration_worker.database.session import get_session
from integration_worker.utils.async_helpers import run_async

logger = logging.getLogger(__name__)

# Import models from api-core (shared database)
# Import inside functions to avoid config initialization issues
try:
    import sys
    import os

    # Add api-core to path if not already there
    api_core_path = "/app/api-core/src"
    if api_core_path not in sys.path:
        sys.path.insert(0, api_core_path)

    # Import models directly
    from api_core.database.models import Call, UsageRecord, Subscription

except ImportError as e:
    raise ImportError(
        f"Cannot import api_core models: {e}. "
        "Ensure api-core is in PYTHONPATH or installed as a package."
    )


@shared_task(
    bind=True,
    name="integration_worker.tasks.usage_aggregation.aggregate_call_minutes_for_user",
    max_retries=3,
    default_retry_delay=60,
)
def aggregate_call_minutes_for_user(
    self,
    user_id: str,
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
) -> dict:
    """
    Aggregate call minutes for a user in a billing period.

    This task aggregates all completed calls for a user within a specific
    billing period and creates/updates a UsageRecord.

    Args:
        user_id: User ID
        period_start: Billing period start date (ISO format, optional)
        period_end: Billing period end date (ISO format, optional)

    Returns:
        Dictionary with total_minutes and status
    """
    try:
        # Parse dates if provided
        start = datetime.fromisoformat(period_start) if period_start else None
        end = datetime.fromisoformat(period_end) if period_end else None

        async def _run_aggregation():
            async with get_session() as session:
                # If period not provided, get from user's active subscription
                if not start or not end:
                    # Get user's active subscription
                    sub_stmt = select(Subscription).where(
                        Subscription.user_id == user_id,
                        Subscription.status == "active",
                    ).order_by(Subscription.created_at.desc())
                    sub_result = await session.execute(sub_stmt)
                    subscription = sub_result.scalar_one_or_none()

                    if not subscription:
                        logger.warning(
                            f"No active subscription found for user {user_id}, "
                            "cannot determine billing period"
                        )
                        return {"total_minutes": 0, "status": "no_subscription"}

                    period_start_dt = subscription.current_period_start
                    period_end_dt = subscription.current_period_end
                else:
                    period_start_dt = start
                    period_end_dt = end

                # Get all completed calls in period
                stmt = select(Call).where(
                    Call.user_id == user_id,
                    Call.status == "completed",
                    Call.ended_at >= period_start_dt,
                    Call.ended_at < period_end_dt,
                    Call.duration_seconds.isnot(None),
                )
                result = await session.execute(stmt)
                calls = result.scalars().all()

                # Calculate total minutes (round up)
                total_seconds = sum(call.duration_seconds or 0 for call in calls)
                total_minutes = (total_seconds + 59) // 60  # Round up

                # Create or update usage record
                usage_stmt = select(UsageRecord).where(
                    UsageRecord.user_id == user_id,
                    UsageRecord.feature == "call_minutes",
                    UsageRecord.period_start == period_start_dt,
                    UsageRecord.period_end == period_end_dt,
                )
                usage_result = await session.execute(usage_stmt)
                usage_record = usage_result.scalar_one_or_none()

                if usage_record:
                    usage_record.quantity = total_minutes
                    logger.debug(
                        f"Updated usage record {usage_record.id} for user {user_id}: "
                        f"{total_minutes} minutes"
                    )
                else:
                    usage_record = UsageRecord(
                        user_id=user_id,
                        feature="call_minutes",
                        quantity=total_minutes,
                        unit="minutes",
                        period_start=period_start_dt,
                        period_end=period_end_dt,
                    )
                    session.add(usage_record)
                    logger.debug(
                        f"Created usage record for user {user_id}: {total_minutes} minutes"
                    )

                await session.commit()
                logger.info(
                    f"Aggregated {total_minutes} minutes for user {user_id} "
                    f"({period_start_dt} to {period_end_dt})"
                )
                
                # Check if user is on trial and should end trial early
                # This is done after aggregation so we have accurate usage data
                try:
                    from integration_worker.tasks.trial_monitoring import check_trial_for_user
                    # Trigger trial check asynchronously (don't wait for result)
                    check_trial_for_user.delay(user_id)
                    logger.debug(f"Triggered trial check for user {user_id} after usage aggregation")
                except Exception as e:
                    # Don't fail aggregation if trial check fails
                    logger.warning(f"Failed to trigger trial check for user {user_id}: {e}")
                
                return {
                    "total_minutes": total_minutes,
                    "status": "success",
                    "user_id": user_id,
                    "period_start": period_start_dt.isoformat(),
                    "period_end": period_end_dt.isoformat(),
                }

        result = run_async(_run_aggregation())
        return result

    except Exception as exc:
        logger.error(
            f"Error aggregating call minutes for user {user_id}: {exc}",
            exc_info=True,
        )
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(
    name="integration_worker.tasks.usage_aggregation.aggregate_all_active_subscriptions",
)
def aggregate_all_active_subscriptions() -> dict:
    """
    Aggregate minutes for all active subscriptions.

    This task is triggered by Celery Beat daily to ensure all usage
    records are up to date for billing purposes.

    Returns:
        Dictionary with aggregated count and errors
    """
    async def _run_aggregation_all():
        async with get_session() as session:
            # Get all active subscriptions
            stmt = select(Subscription).where(Subscription.status == "active")
            result = await session.execute(stmt)
            subscriptions = result.scalars().all()

            aggregated = 0
            errors = 0

            for subscription in subscriptions:
                try:
                    # Trigger async task for each subscription
                    aggregate_call_minutes_for_user.delay(
                        str(subscription.user_id),
                        period_start=subscription.current_period_start.isoformat(),
                        period_end=subscription.current_period_end.isoformat(),
                    )
                    aggregated += 1
                except Exception as e:
                    logger.error(
                        f"Failed to trigger aggregation for user {subscription.user_id}: {e}",
                        exc_info=True,
                    )
                    errors += 1

            return {"aggregated": aggregated, "errors": errors}

    result = run_async(_run_aggregation_all())

    logger.info(
        f"Triggered aggregation for {result['aggregated']} subscriptions "
        f"({result['errors']} errors)"
    )

    return result
