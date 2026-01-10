"""Trial monitoring and management service."""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api_core.config import get_settings
from api_core.database.models import Subscription, UsageRecord
from api_core.exceptions import NotFoundError, ValidationError
from api_core.repositories.billing_repository import BillingRepository
from api_core.services.stripe_service import StripeService, get_stripe_service

logger = logging.getLogger(__name__)


class TrialService:
    """Service for monitoring and managing free trial subscriptions."""

    def __init__(self, session: AsyncSession):
        """
        Initialize trial service.

        Args:
            session: Database session
        """
        self.session = session
        self.repository = BillingRepository(session)
        self.settings = get_settings()

    async def check_trial_conditions(
        self, subscription_id: str
    ) -> tuple[bool, Optional[str]]:
        """
        Check if trial should end based on time or usage limits.

        Args:
            subscription_id: Local subscription ID

        Returns:
            Tuple of (should_end_trial, reason) where:
            - should_end_trial: True if trial should end
            - reason: Reason for ending trial (None if not ending)
        """
        # Get subscription with plan eagerly loaded
        result = await self.session.execute(
            select(Subscription)
            .options(selectinload(Subscription.plan))
            .where(Subscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            raise NotFoundError(f"Subscription {subscription_id} not found")

        # Only check trials
        if subscription.status != "trialing":
            return False, None

        # Check if trial has ended (time-based)
        now = datetime.utcnow()
        if subscription.trial_end and subscription.trial_end <= now:
            return True, "trial_period_expired"

        # Check usage limit (200 minutes)
        if subscription.trial_start:
            # Get total minutes used during trial period
            trial_end = subscription.trial_end or now
            usage_records = await self.repository.usage_records.get_by_user_and_feature(
                subscription.user_id,
                "call_minutes",
                subscription.trial_start,
                trial_end,
            )
            total_minutes = sum(record.quantity for record in usage_records)

            max_minutes = self.settings.billing.trial_max_minutes
            if total_minutes >= max_minutes:
                return True, f"usage_limit_reached_{total_minutes}_minutes"

        return False, None

    async def end_trial_early(
        self, subscription_id: str, reason: str = "usage_limit_reached"
    ) -> None:
        """
        End trial early for a subscription.

        Updates Stripe subscription to end trial immediately and charges the customer.

        Args:
            subscription_id: Local subscription ID
            reason: Reason for ending trial early

        Raises:
            NotFoundError: If subscription not found
            ValidationError: If subscription is not in trial or Stripe operation fails
        """
        # Get subscription
        result = await self.session.execute(
            select(Subscription)
            .options(selectinload(Subscription.plan))
            .where(Subscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            raise NotFoundError(f"Subscription {subscription_id} not found")

        if subscription.status != "trialing":
            raise ValidationError(
                f"Subscription {subscription_id} is not in trial status "
                f"(status: {subscription.status})"
            )

        # End trial in Stripe if subscription has Stripe ID
        if (
            subscription.payment_provider == "stripe"
            and subscription.payment_provider_subscription_id
        ):
            try:
                stripe_service = get_stripe_service(self.session)
                await stripe_service.end_trial_early(
                    subscription.payment_provider_subscription_id, reason=reason
                )
                logger.info(
                    f"Ended trial early in Stripe for subscription {subscription_id}. "
                    f"Reason: {reason}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to end trial early in Stripe for subscription {subscription_id}: {e}"
                )
                raise ValidationError(f"Failed to end trial early in Stripe: {str(e)}") from e

        # Update local subscription
        # The trial_end will be updated by Stripe webhook, but we can update status immediately
        # Note: The webhook will handle the full update, but we can mark it as ending
        now = datetime.utcnow()
        await self.repository.subscriptions.update(
            subscription_id,
            trial_end=now,  # Set trial_end to now
            status="active",  # Change status to active (Stripe will charge)
        )

        logger.info(
            f"Ended trial early for subscription {subscription_id}. "
            f"Reason: {reason}. Status updated to active."
        )

    async def check_all_active_trials(self) -> dict[str, int]:
        """
        Check all active trial subscriptions for conditions that should end the trial.

        Returns:
            Dictionary with counts: {"checked": N, "ended": M}
        """
        # Get all trialing subscriptions
        result = await self.session.execute(
            select(Subscription)
            .options(selectinload(Subscription.plan))
            .where(Subscription.status == "trialing")
        )
        trialing_subscriptions = result.scalars().all()

        checked = 0
        ended = 0

        for subscription in trialing_subscriptions:
            try:
                checked += 1
                should_end, reason = await self.check_trial_conditions(subscription.id)

                if should_end:
                    await self.end_trial_early(subscription.id, reason=reason or "unknown")
                    ended += 1
                    logger.info(
                        f"Ended trial for subscription {subscription.id}. Reason: {reason}"
                    )
            except Exception as e:
                logger.error(
                    f"Error checking trial conditions for subscription {subscription.id}: {e}",
                    exc_info=True,
                )
                # Continue with other subscriptions

        return {"checked": checked, "ended": ended}


def get_trial_service(session: AsyncSession) -> TrialService:
    """
    Factory function to create TrialService instance.

    Args:
        session: Database session

    Returns:
        TrialService instance
    """
    return TrialService(session)
