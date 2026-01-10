"""Celery tasks for monitoring free trial subscriptions."""

import asyncio
import logging
from datetime import datetime

from celery import shared_task

logger = logging.getLogger(__name__)

try:
    from api_core.database.session import get_session
    from api_core.services.trial_service import get_trial_service
except ImportError as e:
    logger.error(
        f"Failed to import api_core modules: {e}. "
        "Ensure api-core is in PYTHONPATH or installed as a package."
    )


@shared_task(
    bind=True,
    name="integration_worker.tasks.trial_monitoring.check_all_trials",
    max_retries=3,
    default_retry_delay=60,
)
def check_all_trials(self) -> dict:
    """
    Check all active trial subscriptions and end trials that meet conditions.

    This task runs periodically to check if any trial subscriptions should end early
    due to usage limits (e.g., 200 minutes reached).

    The 3-day time limit is handled automatically by Stripe, but we need to monitor
    usage-based limits.

    Returns:
        Dictionary with counts: {"checked": N, "ended": M}
    """
    try:

        async def _run_check():
            async with get_session() as session:
                trial_service = get_trial_service(session)
                result = await trial_service.check_all_active_trials()
                return result

        result = asyncio.run(_run_check())
        logger.info(
            f"Trial monitoring completed: checked {result['checked']} trials, "
            f"ended {result['ended']} trials"
        )
        return result

    except Exception as e:
        logger.error(f"Error in trial monitoring task: {e}", exc_info=True)
        # Retry on failure
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    name="integration_worker.tasks.trial_monitoring.check_trial_for_user",
    max_retries=3,
    default_retry_delay=60,
)
def check_trial_for_user(self, user_id: str) -> dict:
    """
    Check trial conditions for a specific user's subscription.

    This task is triggered after usage aggregation to check if the user
    has reached the trial usage limit.

    Args:
        user_id: User ID to check

    Returns:
        Dictionary with result: {"checked": bool, "ended": bool, "reason": str}
    """
    try:

        async def _run_check():
            async with get_session() as session:
                from api_core.repositories.billing_repository import BillingRepository

                billing_repo = BillingRepository(session)
                subscription = await billing_repo.subscriptions.get_by_user_id(user_id)

                if not subscription or subscription.status != "trialing":
                    return {"checked": False, "ended": False, "reason": "no_trial_subscription"}

                trial_service = get_trial_service(session)
                should_end, reason = await trial_service.check_trial_conditions(subscription.id)

                if should_end:
                    await trial_service.end_trial_early(subscription.id, reason=reason or "unknown")
                    return {"checked": True, "ended": True, "reason": reason}

                return {"checked": True, "ended": False, "reason": None}

        result = asyncio.run(_run_check())
        logger.info(f"Trial check for user {user_id}: {result}")
        return result

    except Exception as e:
        logger.error(f"Error checking trial for user {user_id}: {e}", exc_info=True)
        # Retry on failure
        raise self.retry(exc=e)
