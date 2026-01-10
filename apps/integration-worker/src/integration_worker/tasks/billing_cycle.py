"""Billing cycle management Celery tasks."""

import logging
from datetime import datetime, timedelta
from typing import Optional

from celery import shared_task
from sqlalchemy import select

from integration_worker.database.session import get_session
from integration_worker.utils.async_helpers import run_async

logger = logging.getLogger(__name__)

# Import models and services from api-core (shared database)
try:
    import sys

    # Add api-core to path if not already there
    api_core_path = "/app/api-core/src"
    if api_core_path not in sys.path:
        sys.path.insert(0, api_core_path)

    # Import models directly
    from api_core.database.models import Subscription

    # Import services (will use our session)
    from api_core.services.billing_service import BillingService

except ImportError as e:
    raise ImportError(
        f"Cannot import api_core modules: {e}. "
        "Ensure api-core is in PYTHONPATH or installed as a package."
    )


@shared_task(
    bind=True,
    name="integration_worker.tasks.billing_cycle.process_billing_cycle_end",
    max_retries=3,
    default_retry_delay=300,  # 5 minutes - billing operations can take longer
)
def process_billing_cycle_end(self, days_ahead: int = 1) -> dict:
    """
    Process subscriptions that have reached end of billing period.

    This task:
    - Finds subscriptions ending within the specified days
    - Generates invoices with overage charges
    - Renews subscriptions for the next period

    Args:
        days_ahead: Number of days ahead to look for ending subscriptions (default: 1)

    Returns:
        Dictionary with processed count and errors
    """
    try:
        async def _run_billing_cycle():
            async with get_session() as session:
                # Find subscriptions ending within the specified timeframe
                now = datetime.utcnow()
                cutoff_date = now + timedelta(days=days_ahead)

                stmt = select(Subscription).where(
                    Subscription.status == "active",
                    Subscription.current_period_end <= cutoff_date,
                    Subscription.cancel_at_period_end == False,
                )
                result = await session.execute(stmt)
                subscriptions = result.scalars().all()

                billing_service = BillingService(session)
                processed = 0
                errors = 0

                for subscription in subscriptions:
                    try:
                        # Check if subscription period has actually ended
                        if subscription.current_period_end > now:
                            # Not yet ended, skip (will be processed on the actual end date)
                            logger.debug(
                                f"Subscription {subscription.id} not yet ended, skipping"
                            )
                            continue

                        logger.info(
                            f"Processing billing cycle end for subscription {subscription.id} "
                            f"(user: {subscription.user_id}, period: "
                            f"{subscription.current_period_start} to {subscription.current_period_end})"
                        )

                        # Generate invoice with overage
                        invoice = await billing_service.generate_billing_invoice(
                            subscription.id,
                            subscription.current_period_start,
                            subscription.current_period_end,
                        )

                        logger.info(
                            f"Generated invoice {invoice.id} for subscription {subscription.id}: "
                            f"${invoice.amount}"
                        )

                        # Note: Stripe handles automatic charging for subscriptions
                        # If subscription has payment_provider_subscription_id, Stripe will
                        # automatically charge the customer. We just need to ensure the invoice
                        # is created and synced.

                        # Renew subscription for next period
                        renewed = await billing_service.renew_subscription(subscription.id)

                        # Get updated subscription to see new period
                        updated_subscription = await session.get(Subscription, subscription.id)
                        await session.refresh(updated_subscription)

                        logger.info(
                            f"Renewed subscription {subscription.id} for user {subscription.user_id}. "
                            f"New period: {updated_subscription.current_period_start} to "
                            f"{updated_subscription.current_period_end}"
                        )

                        processed += 1

                    except Exception as e:
                        logger.error(
                            f"Error processing billing cycle for subscription {subscription.id}: {e}",
                            exc_info=True,
                        )
                        errors += 1

                return {
                    "processed": processed,
                    "errors": errors,
                    "total_found": len(subscriptions),
                }

        result = run_async(_run_billing_cycle())

        logger.info(
            f"Processed billing cycle for {result['processed']} subscriptions "
            f"({result['errors']} errors, {result['total_found']} total found)"
        )

        return result

    except Exception as exc:
        logger.error(
            f"Error in process_billing_cycle_end: {exc}",
            exc_info=True,
        )
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=300 * (2 ** self.request.retries))


@shared_task(
    name="integration_worker.tasks.billing_cycle.process_daily_billing_cycles",
)
def process_daily_billing_cycles() -> dict:
    """
    Process billing cycles for all subscriptions ending today.

    This task is triggered by Celery Beat daily to process subscriptions
    that have reached the end of their billing period.

    Returns:
        Dictionary with processed count and errors
    """
    return process_billing_cycle_end(days_ahead=1)
