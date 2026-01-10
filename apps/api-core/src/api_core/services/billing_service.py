"""Billing and subscription service with business logic."""

import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api_core.database.models import Invoice, Plan, Subscription, UsageRecord, User
from api_core.exceptions import ConflictError, NotFoundError, ValidationError
from api_core.models.billing import (
    InvoiceItem,
    InvoiceResponse,
    PlanResponse,
    SubscriptionResponse,
    UsageLimitCheckResponse,
    UsageRecordResponse,
    UsageSummaryResponse,
)
from api_core.repositories.billing_repository import BillingRepository
from api_core.services.stripe_service import StripeService, get_stripe_service

logger = logging.getLogger(__name__)


def _get_plan_minutes_data(plan) -> tuple[int, Decimal]:
    """
    Get included_minutes and overage_rate_per_minute from Plan.
    
    Uses new columns if available, falls back to features_json for backward compatibility.
    
    Args:
        plan: Plan model instance
        
    Returns:
        Tuple of (included_minutes: int, overage_rate_per_minute: Decimal)
    """
    included_minutes = 0
    overage_rate = Decimal("0.00")
    
    # Try new columns first
    if hasattr(plan, "included_minutes") and plan.included_minutes is not None:
        included_minutes = plan.included_minutes
    if hasattr(plan, "overage_rate_per_minute") and plan.overage_rate_per_minute is not None:
        overage_rate = Decimal(str(plan.overage_rate_per_minute))
    
    # Fallback to features_json if columns are NULL
    if (included_minutes == 0 and overage_rate == Decimal("0.00")) and plan.features_json:
        try:
            features = json.loads(plan.features_json) if isinstance(plan.features_json, str) else plan.features_json
            if features:
                if included_minutes == 0 and "included_minutes" in features:
                    included_minutes = features.get("included_minutes") or 0
                if overage_rate == Decimal("0.00") and "overage_rate_per_minute" in features:
                    overage_rate_val = features.get("overage_rate_per_minute")
                    if overage_rate_val is not None:
                        overage_rate = Decimal(str(overage_rate_val))
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(f"Failed to parse features_json for plan {plan.id}: {e}")
    
    return included_minutes, overage_rate


class BillingService:
    """Service for billing and subscription management operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize billing service.

        Args:
            session: Database session
        """
        self.repository = BillingRepository(session)

    # ==================== Plan Methods ====================

    def _plan_to_response(self, plan: Plan) -> PlanResponse:
        """
        Convert SQLAlchemy Plan model to Pydantic PlanResponse.

        Args:
            plan: Plan database model

        Returns:
            PlanResponse Pydantic model
        """
        features = None
        if plan.features_json:
            try:
                features = json.loads(plan.features_json)
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Invalid JSON in plan features for plan {plan.id}")

        # Get minutes data (with fallback to features_json)
        included_minutes, overage_rate = _get_plan_minutes_data(plan)
        
        return PlanResponse(
            id=plan.id,
            name=plan.name,
            display_name=plan.display_name,
            description=plan.description,
            price_monthly=float(plan.price_monthly) if plan.price_monthly else None,
            price_yearly=float(plan.price_yearly) if plan.price_yearly else None,
            currency=plan.currency,
            features=features,
            max_calls_per_month=plan.max_calls_per_month,
            max_users=plan.max_users,
            max_storage_gb=plan.max_storage_gb,
            included_minutes=included_minutes if included_minutes > 0 else None,
            overage_rate_per_minute=float(overage_rate) if overage_rate > Decimal("0.00") else None,
            is_active=plan.is_active,
            is_public=plan.is_public,
            created_at=plan.created_at.isoformat() if plan.created_at else "",
            updated_at=plan.updated_at.isoformat() if plan.updated_at else "",
        )

    async def get_plan_by_id(self, plan_id: str) -> PlanResponse:
        """
        Get plan by ID.

        Args:
            plan_id: Plan ID

        Returns:
            PlanResponse

        Raises:
            NotFoundError: If plan not found
        """
        plan = await self.repository.plans.get_by_id(plan_id)
        if not plan:
            raise NotFoundError(f"Plan with ID {plan_id} not found")

        return self._plan_to_response(plan)

    async def get_active_plans(self) -> List[PlanResponse]:
        """
        Get all active public plans.

        Returns:
            List of PlanResponse
        """
        plans = await self.repository.plans.get_active_plans()
        return [self._plan_to_response(plan) for plan in plans]

    # ==================== Subscription Methods ====================

    def _subscription_to_response(
        self, subscription: Subscription, include_plan: bool = False
    ) -> SubscriptionResponse:
        """
        Convert SQLAlchemy Subscription model to Pydantic SubscriptionResponse.

        Args:
            subscription: Subscription database model
            include_plan: Whether to include plan details

        Returns:
            SubscriptionResponse Pydantic model
        """
        plan_response = None
        if include_plan:
            # Try to get plan from relationship first
            if subscription.plan:
                plan_response = self._plan_to_response(subscription.plan)
            # Fallback: load plan by plan_id if relationship not loaded
            elif subscription.plan_id:
                # Note: This is a sync operation, but we're in a sync context
                # In practice, the plan should be eagerly loaded, but this is a safety net
                logger.warning(
                    f"Plan relationship not loaded for subscription {subscription.id}, "
                    f"plan_id={subscription.plan_id}. This should not happen with eager loading."
                )
                # We can't load it here synchronously, so plan_response will be None
                # The caller should ensure plan is eagerly loaded

        return SubscriptionResponse(
            id=subscription.id,
            user_id=subscription.user_id,
            plan_id=subscription.plan_id,
            plan=plan_response,
            status=subscription.status,
            billing_cycle=subscription.billing_cycle,
            current_period_start=subscription.current_period_start.isoformat()
            if subscription.current_period_start
            else "",
            current_period_end=subscription.current_period_end.isoformat()
            if subscription.current_period_end
            else "",
            payment_provider=subscription.payment_provider,
            payment_method_id=subscription.payment_method_id,
            canceled_at=subscription.canceled_at.isoformat() if subscription.canceled_at else None,
            cancel_at_period_end=subscription.cancel_at_period_end,
            trial_start=subscription.trial_start.isoformat() if subscription.trial_start else None,
            trial_end=subscription.trial_end.isoformat() if subscription.trial_end else None,
            created_at=subscription.created_at.isoformat() if subscription.created_at else "",
            updated_at=subscription.updated_at.isoformat() if subscription.updated_at else "",
        )

    async def sync_subscription_from_stripe(
        self, subscription_id: str
    ) -> Optional[SubscriptionResponse]:
        """
        Sync subscription data from Stripe to update missing information.

        Args:
            subscription_id: Local subscription ID

        Returns:
            Updated SubscriptionResponse or None if not found

        Raises:
            ValidationError: If Stripe sync fails
        """
        # Get subscription with plan eagerly loaded
        result = await self.repository.session.execute(
            select(Subscription)
            .options(selectinload(Subscription.plan))
            .where(Subscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()
        if not subscription:
            return None

        # Only sync if subscription has Stripe ID
        if (
            subscription.payment_provider != "stripe"
            or not subscription.payment_provider_subscription_id
        ):
            logger.debug(f"Subscription {subscription_id} is not a Stripe subscription, skipping sync")
            return self._subscription_to_response(subscription, include_plan=True)

        try:
            stripe_service = get_stripe_service(self.repository.session)
            stripe_subscription = await stripe_service.get_subscription(
                subscription.payment_provider_subscription_id
            )

            # Extract data from Stripe subscription
            period_start = datetime.fromtimestamp(
                stripe_subscription.get("current_period_start", 0), tz=None
            )
            period_end = datetime.fromtimestamp(
                stripe_subscription.get("current_period_end", 0), tz=None
            )

            trial_start = None
            trial_end = None
            if stripe_subscription.get("trial_start"):
                trial_start = datetime.fromtimestamp(
                    stripe_subscription.get("trial_start", 0), tz=None
                )
            if stripe_subscription.get("trial_end"):
                trial_end = datetime.fromtimestamp(
                    stripe_subscription.get("trial_end", 0), tz=None
                )

            # Extract plan_id from Stripe metadata if missing locally
            plan_id = subscription.plan_id
            stripe_metadata = stripe_subscription.get("metadata", {})
            if not plan_id and stripe_metadata.get("plan_id"):
                plan_id = stripe_metadata.get("plan_id")
                logger.info(f"Extracted plan_id {plan_id} from Stripe metadata for subscription {subscription_id}")

            # Map Stripe status
            stripe_status = stripe_subscription.get("status", "")
            status_mapping = {
                "trialing": "trialing",
                "active": "active",
                "canceled": "canceled",
                "past_due": "past_due",
                "unpaid": "past_due",
            }
            new_status = status_mapping.get(stripe_status, subscription.status)

            # If trial is active, ensure status is trialing
            if trial_end and trial_end > datetime.utcnow():
                new_status = "trialing"

            # Determine billing cycle from Stripe subscription
            items = stripe_subscription.get("items", {}).get("data", [])
            billing_cycle = subscription.billing_cycle or "monthly"  # Default to existing or monthly
            if items:
                interval = items[0].get("price", {}).get("recurring", {}).get("interval", "month")
                if interval == "year":
                    billing_cycle = "yearly"
                elif interval == "month":
                    billing_cycle = "monthly"

            # Update subscription with Stripe data
            updates = {
                "status": new_status,
                "current_period_start": period_start,
                "current_period_end": period_end,
                "trial_start": trial_start,
                "trial_end": trial_end,
                "cancel_at_period_end": stripe_subscription.get("cancel_at_period_end", False),
                "billing_cycle": billing_cycle,  # Always update billing_cycle from Stripe
            }
            
            # Update plan_id if we extracted it from Stripe
            if plan_id and plan_id != subscription.plan_id:
                updates["plan_id"] = plan_id

            # Update canceled_at if subscription is canceled
            if new_status == "canceled" and stripe_subscription.get("canceled_at"):
                updates["canceled_at"] = datetime.fromtimestamp(
                    stripe_subscription.get("canceled_at", 0), tz=None
                )

            # Update subscription
            await self.repository.subscriptions.update(subscription_id, **updates)

            # Reload with plan
            result = await self.repository.session.execute(
                select(Subscription)
                .options(selectinload(Subscription.plan))
                .where(Subscription.id == subscription_id)
            )
            updated_subscription = result.scalar_one_or_none()

            logger.info(f"Synced subscription {subscription_id} from Stripe")
            return (
                self._subscription_to_response(updated_subscription, include_plan=True)
                if updated_subscription
                else None
            )

        except Exception as e:
            logger.error(f"Error syncing subscription {subscription_id} from Stripe: {e}")
            # Return current subscription even if sync fails
            return self._subscription_to_response(subscription, include_plan=True)

    async def get_user_subscription(
        self, user_id: str, include_plan: bool = True, auto_sync: bool = True
    ) -> Optional[SubscriptionResponse]:
        """
        Get active subscription for a user.

        Args:
            user_id: User ID
            include_plan: Whether to include plan details
            auto_sync: Whether to automatically sync from Stripe if data is missing

        Returns:
            SubscriptionResponse or None if no active subscription
        """
        subscription = await self.repository.subscriptions.get_by_user_id(user_id)
        if not subscription:
            return None

        # Auto-sync if subscription has Stripe ID and data appears incomplete
        # We sync if:
        # 1. plan_id is missing
        # 2. plan relationship is not loaded (even though we eager load it)
        # 3. period dates look like defaults (created within last minute and period_end is exactly 30 days from period_start)
        if (
            auto_sync
            and subscription.payment_provider == "stripe"
            and subscription.payment_provider_subscription_id
        ):
            should_sync = False
            reason = ""
            
            # Check if plan_id is missing
            if not subscription.plan_id:
                should_sync = True
                reason = "missing plan_id"
            # Check if plan relationship is not loaded (shouldn't happen with eager loading, but safety check)
            elif not subscription.plan:
                should_sync = True
                reason = "plan relationship not loaded"
            # Check if billing_cycle is missing or empty
            elif not subscription.billing_cycle or subscription.billing_cycle.strip() == "":
                should_sync = True
                reason = "missing billing_cycle"
            # Check if period dates look like defaults (heuristic: period_end is exactly 30 days from period_start)
            elif subscription.current_period_start and subscription.current_period_end:
                period_delta = (subscription.current_period_end - subscription.current_period_start).days
                # If period is exactly 30 days and subscription was created recently, might be default
                if period_delta == 30 and (datetime.utcnow() - subscription.created_at).total_seconds() < 300:
                    should_sync = True
                    reason = "period dates appear to be defaults"
            
            if should_sync:
                logger.info(
                    f"Auto-syncing subscription {subscription.id} from Stripe due to: {reason}"
                )
                synced = await self.sync_subscription_from_stripe(subscription.id)
                if synced:
                    return synced
                # If sync failed, continue with original subscription (might be network issue)
                logger.warning(f"Auto-sync failed for subscription {subscription.id}, returning original subscription")
        
        # If plan relationship is not loaded but plan_id exists, try to load it
        if subscription.plan_id and not subscription.plan:
            logger.warning(
                f"Plan relationship not loaded for subscription {subscription.id}, "
                f"attempting to load plan {subscription.plan_id}"
            )
            plan = await self.repository.plans.get_by_id(subscription.plan_id)
            if plan:
                # Manually set the plan on the subscription object (won't persist, but will work for this response)
                subscription.plan = plan

        return self._subscription_to_response(subscription, include_plan=include_plan)

    async def can_user_make_calls(self, user_id: str) -> tuple[bool, Optional[str]]:
        """
        Check if a user can make calls based on their subscription status.

        Args:
            user_id: User ID

        Returns:
            Tuple of (can_make_calls, reason) where:
            - can_make_calls: True if user can make calls, False otherwise
            - reason: Reason why calls are blocked (None if allowed)
        """
        subscription = await self.repository.subscriptions.get_by_user_id(user_id)
        
        # No subscription = blocked
        if not subscription:
            return False, "no_active_subscription"
        
        # Check subscription status
        status = subscription.status.lower()
        
        # Active and trialing subscriptions allow calls
        if status in ["active", "trialing"]:
            return True, None
        
        # Canceled, past_due, and other statuses block calls
        if status == "canceled":
            return False, "subscription_canceled"
        elif status == "past_due":
            return False, "subscription_past_due"
        else:
            return False, f"subscription_status_{status}"

    async def create_subscription(
        self,
        user_id: str,
        plan_id: str,
        billing_cycle: str = "monthly",
        payment_method_id: Optional[str] = None,
        payment_provider: Optional[str] = None,
        payment_provider_subscription_id: Optional[str] = None,
        trial_days: Optional[int] = None,
        use_stripe: bool = True,
        current_period_start: Optional[datetime] = None,
        current_period_end: Optional[datetime] = None,
        trial_start: Optional[datetime] = None,
        trial_end: Optional[datetime] = None,
    ) -> SubscriptionResponse:
        """
        Create a new subscription for a user.

        Args:
            user_id: User ID
            plan_id: Plan ID
            billing_cycle: Billing cycle (monthly or yearly)
            payment_method_id: Payment method ID (for Stripe)
            payment_provider: Payment provider name (e.g., "stripe")
            payment_provider_subscription_id: Payment provider subscription ID
            trial_days: Number of trial days (optional)
            use_stripe: Whether to create subscription via Stripe (default: True)

        Returns:
            Created SubscriptionResponse

        Raises:
            NotFoundError: If plan or user not found
            ConflictError: If user already has active subscription
            ValidationError: If billing cycle is invalid or Stripe operation fails
        """
        # Validate billing cycle
        if billing_cycle not in ["monthly", "yearly"]:
            raise ValidationError("Billing cycle must be 'monthly' or 'yearly'")

        # Check if plan exists
        plan = await self.repository.plans.get_by_id(plan_id)
        if not plan:
            raise NotFoundError(f"Plan with ID {plan_id} not found")

        # Get user
        from api_core.repositories.user_repository import UserRepository

        user_repo = UserRepository(self.repository.session)
        user = await user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")

        # Check if user already has active subscription
        existing = await self.repository.subscriptions.get_by_user_id(user_id)
        if existing:
            raise ConflictError("User already has an active subscription")

        # If using Stripe and payment method provided, create subscription in Stripe
        stripe_subscription_id = payment_provider_subscription_id
        if use_stripe and payment_method_id:
            try:
                stripe_service = get_stripe_service(self.repository.session)
                stripe_subscription = await stripe_service.create_subscription(
                    user=user,
                    plan=plan,
                    payment_method_id=payment_method_id,
                    trial_days=trial_days,
                )
                stripe_subscription_id = stripe_subscription.get("id")
                payment_provider = "stripe"
                logger.info(
                    f"Created Stripe subscription {stripe_subscription_id} for user {user_id}"
                )
            except Exception as e:
                logger.error(f"Failed to create Stripe subscription: {e}")
                raise ValidationError(f"Failed to create Stripe subscription: {str(e)}")

        # Calculate billing period (use provided dates if available, otherwise calculate)
        now = datetime.utcnow()
        if current_period_start is not None:
            period_start = current_period_start
        else:
            period_start = now
            
        if current_period_end is not None:
            period_end = current_period_end
        elif billing_cycle == "yearly":
            period_end = now + timedelta(days=365)
        else:
            period_end = now + timedelta(days=30)

        # Handle trial period (use provided dates if available, otherwise calculate)
        if trial_start is None and trial_end is None:
            if trial_days and trial_days > 0:
                trial_start = now
                trial_end = now + timedelta(days=trial_days)
                # Extend period end to include trial if not provided
                if current_period_end is None:
                    period_end = trial_end + (period_end - now)

        # Create subscription in database
        subscription = await self.repository.subscriptions.create_subscription(
            user_id=user_id,
            plan_id=plan_id,
            billing_cycle=billing_cycle,
            current_period_start=period_start,
            current_period_end=period_end,
            payment_provider=payment_provider or ("stripe" if use_stripe else None),
            payment_provider_subscription_id=stripe_subscription_id,
            trial_start=trial_start,
            trial_end=trial_end,
            payment_method_id=payment_method_id,  # Pass through kwargs
        )

        logger.info(f"Created subscription {subscription.id} for user {user_id}")
        return self._subscription_to_response(subscription, include_plan=True)

    async def update_subscription(
        self, subscription_id: str, updates: Dict[str, Any]
    ) -> SubscriptionResponse:
        """
        Update subscription.

        Args:
            subscription_id: Subscription ID
            updates: Dictionary of fields to update

        Returns:
            Updated SubscriptionResponse

        Raises:
            NotFoundError: If subscription not found
            ValidationError: If updates are invalid
        """
        # Get subscription with plan eagerly loaded
        result = await self.repository.session.execute(
            select(Subscription)
            .options(selectinload(Subscription.plan))
            .where(Subscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()
        if not subscription:
            raise NotFoundError(f"Subscription with ID {subscription_id} not found")

        # Validate updates
        allowed_fields = {
            "status",
            "billing_cycle",
            "payment_method_id",
            "cancel_at_period_end",
            "metadata_json",
        }
        invalid_fields = set(updates.keys()) - allowed_fields
        if invalid_fields:
            raise ValidationError(f"Invalid fields for update: {invalid_fields}")

        # Update subscription
        updated = await self.repository.subscriptions.update(subscription_id, **updates)
        if not updated:
            raise NotFoundError(f"Subscription with ID {subscription_id} not found")
        
        # Reload with plan to ensure it's available
        result = await self.repository.session.execute(
            select(Subscription)
            .options(selectinload(Subscription.plan))
            .where(Subscription.id == subscription_id)
        )
        updated_with_plan = result.scalar_one_or_none()

        return self._subscription_to_response(updated_with_plan, include_plan=True)

    async def cancel_subscription(
        self, subscription_id: str, cancel_at_period_end: bool = True
    ) -> SubscriptionResponse:
        """
        Cancel a subscription.

        Args:
            subscription_id: Subscription ID
            cancel_at_period_end: Whether to cancel at period end or immediately

        Returns:
            Updated SubscriptionResponse

        Raises:
            NotFoundError: If subscription not found
            ValidationError: If Stripe cancellation fails
        """
        # Get subscription with plan eagerly loaded to avoid greenlet_spawn error
        result = await self.repository.session.execute(
            select(Subscription)
            .options(selectinload(Subscription.plan))
            .where(Subscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()
        if not subscription:
            raise NotFoundError(f"Subscription with ID {subscription_id} not found")

        # Cancel in Stripe if subscription has Stripe ID
        if subscription.payment_provider == "stripe" and subscription.payment_provider_subscription_id:
            try:
                stripe_service = get_stripe_service(self.repository.session)
                await stripe_service.cancel_subscription(
                    stripe_subscription_id=subscription.payment_provider_subscription_id,
                    cancel_at_period_end=cancel_at_period_end,
                )
                logger.info(
                    f"Canceled Stripe subscription {subscription.payment_provider_subscription_id}"
                )
            except Exception as e:
                logger.error(f"Failed to cancel Stripe subscription: {e}")
                # Continue with local cancellation even if Stripe fails

        # Cancel in database
        canceled_subscription = await self.repository.subscriptions.cancel_subscription(
            subscription_id, cancel_at_period_end=cancel_at_period_end
        )
        if not canceled_subscription:
            raise NotFoundError(f"Subscription with ID {subscription_id} not found")

        logger.info(
            f"Canceled subscription {subscription_id} (at_period_end={cancel_at_period_end}). "
            f"Status: {canceled_subscription.status}, cancel_at_period_end: {canceled_subscription.cancel_at_period_end}"
        )
        response = self._subscription_to_response(canceled_subscription, include_plan=True)
        logger.debug(
            f"Subscription response for {subscription_id}: "
            f"status={response.status}, cancel_at_period_end={response.cancel_at_period_end}"
        )
        return response

    async def upgrade_subscription(
        self, subscription_id: str, new_plan_id: str, prorate: bool = True
    ) -> SubscriptionResponse:
        """
        Upgrade subscription to a new plan.

        Args:
            subscription_id: Subscription ID
            new_plan_id: New plan ID
            prorate: Whether to prorate the billing

        Returns:
            Updated SubscriptionResponse

        Raises:
            NotFoundError: If subscription or plan not found
            ValidationError: If upgrade is invalid or Stripe operation fails
        """
        # Get subscription with plan eagerly loaded
        result = await self.repository.session.execute(
            select(Subscription)
            .options(selectinload(Subscription.plan))
            .where(Subscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()
        if not subscription:
            raise NotFoundError(f"Subscription with ID {subscription_id} not found")

        new_plan = await self.repository.plans.get_by_id(new_plan_id)
        if not new_plan:
            raise NotFoundError(f"Plan with ID {new_plan_id} not found")

        # Update in Stripe if subscription has Stripe ID
        if subscription.payment_provider == "stripe" and subscription.payment_provider_subscription_id:
            try:
                stripe_service = get_stripe_service(self.repository.session)
                await stripe_service.update_subscription_plan(
                    stripe_subscription_id=subscription.payment_provider_subscription_id,
                    new_plan=new_plan,
                    prorate=prorate,
                )
                logger.info(
                    f"Updated Stripe subscription {subscription.payment_provider_subscription_id} "
                    f"to plan {new_plan_id}"
                )
            except Exception as e:
                logger.error(f"Failed to update Stripe subscription: {e}")
                raise ValidationError(f"Failed to update Stripe subscription: {str(e)}")

        # Update plan in database
        updates = {"plan_id": new_plan_id}
        if prorate:
            # Calculate prorated period end based on remaining time
            now = datetime.utcnow()
            remaining_days = (subscription.current_period_end - now).days
            if remaining_days > 0:
                # Extend period end to account for proration
                # This is simplified - in production, calculate actual prorated amount
                subscription.current_period_end = subscription.current_period_end + timedelta(
                    days=remaining_days
                )

        updated = await self.repository.subscriptions.update(subscription_id, **updates)
        logger.info(f"Upgraded subscription {subscription_id} to plan {new_plan_id}")
        
        # Reload with plan to ensure it's available
        result = await self.repository.session.execute(
            select(Subscription)
            .options(selectinload(Subscription.plan))
            .where(Subscription.id == subscription_id)
        )
        updated_with_plan = result.scalar_one_or_none()
        
        return self._subscription_to_response(updated_with_plan, include_plan=True)

    async def renew_subscription(self, subscription_id: str) -> SubscriptionResponse:
        """
        Renew subscription for another billing period.

        Args:
            subscription_id: Subscription ID

        Returns:
            Updated SubscriptionResponse

        Raises:
            NotFoundError: If subscription not found
        """
        # Get subscription with plan eagerly loaded
        result = await self.repository.session.execute(
            select(Subscription)
            .options(selectinload(Subscription.plan))
            .where(Subscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()
        if not subscription:
            raise NotFoundError(f"Subscription with ID {subscription_id} not found")

        # Calculate new period
        now = datetime.utcnow()
        if subscription.billing_cycle == "yearly":
            period_end = now + timedelta(days=365)
        else:
            period_end = now + timedelta(days=30)

        updated = await self.repository.subscriptions.update_subscription_period(
            subscription_id, period_start=now, period_end=period_end
        )
        if not updated:
            raise NotFoundError(f"Subscription with ID {subscription_id} not found")

        logger.info(f"Renewed subscription {subscription_id}")
        
        # Reload with plan to ensure it's available
        result = await self.repository.session.execute(
            select(Subscription)
            .options(selectinload(Subscription.plan))
            .where(Subscription.id == subscription_id)
        )
        updated_with_plan = result.scalar_one_or_none()
        
        return self._subscription_to_response(updated_with_plan, include_plan=True)

    # ==================== Invoice Methods ====================

    def _invoice_to_response(self, invoice: Invoice) -> InvoiceResponse:
        """
        Convert SQLAlchemy Invoice model to Pydantic InvoiceResponse.

        Args:
            invoice: Invoice database model

        Returns:
            InvoiceResponse Pydantic model
        """
        items = None
        if invoice.items_json:
            try:
                items_data = json.loads(invoice.items_json)
                if isinstance(items_data, list):
                    from api_core.models.billing import InvoiceItem

                    items = [InvoiceItem(**item) for item in items_data]
            except (json.JSONDecodeError, TypeError, ValueError):
                logger.warning(f"Invalid JSON in invoice items for invoice {invoice.id}")

        return InvoiceResponse(
            id=invoice.id,
            user_id=invoice.user_id,
            subscription_id=invoice.subscription_id,
            invoice_number=invoice.invoice_number,
            amount=float(invoice.amount),
            currency=invoice.currency,
            tax_amount=float(invoice.tax_amount) if invoice.tax_amount else None,
            status=invoice.status,
            paid_at=invoice.paid_at.isoformat() if invoice.paid_at else None,
            due_date=invoice.due_date.isoformat() if invoice.due_date else "",
            payment_provider=invoice.payment_provider,
            items=items,
            created_at=invoice.created_at.isoformat() if invoice.created_at else "",
            updated_at=invoice.updated_at.isoformat() if invoice.updated_at else "",
        )

    async def get_user_invoices(
        self, user_id: str, skip: int = 0, limit: int = 100
    ) -> List[InvoiceResponse]:
        """
        Get invoices for a user.

        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of InvoiceResponse
        """
        invoices = await self.repository.invoices.get_by_user_id(user_id, skip=skip, limit=limit)
        return [self._invoice_to_response(invoice) for invoice in invoices]

    async def get_invoice_by_id(self, invoice_id: str) -> InvoiceResponse:
        """
        Get invoice by ID.

        Args:
            invoice_id: Invoice ID

        Returns:
            InvoiceResponse

        Raises:
            NotFoundError: If invoice not found
        """
        invoice = await self.repository.invoices.get_by_id(invoice_id)
        if not invoice:
            raise NotFoundError(f"Invoice with ID {invoice_id} not found")

        return self._invoice_to_response(invoice)

    # ==================== Usage Tracking Methods ====================

    def _usage_record_to_response(self, usage_record: UsageRecord) -> UsageRecordResponse:
        """
        Convert SQLAlchemy UsageRecord model to Pydantic UsageRecordResponse.

        Args:
            usage_record: UsageRecord database model

        Returns:
            UsageRecordResponse Pydantic model
        """
        return UsageRecordResponse(
            id=usage_record.id,
            user_id=usage_record.user_id,
            feature=usage_record.feature,
            quantity=usage_record.quantity,
            unit=usage_record.unit,
            period_start=usage_record.period_start.isoformat() if usage_record.period_start else "",
            period_end=usage_record.period_end.isoformat() if usage_record.period_end else "",
            created_at=usage_record.created_at.isoformat() if usage_record.created_at else "",
        )

    async def track_usage(
        self,
        user_id: str,
        feature: str,
        quantity: int = 1,
        unit: str = "count",
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> UsageRecordResponse:
        """
        Track feature usage for a user.

        Args:
            user_id: User ID
            feature: Feature name (e.g., "calls", "storage", "api_requests")
            quantity: Usage quantity
            unit: Unit of measurement
            period_start: Period start date (defaults to now)
            period_end: Period end date (defaults to period_start + 1 day)

        Returns:
            Created UsageRecordResponse
        """
        usage_record = await self.repository.usage_records.create_usage_record(
            user_id=user_id,
            feature=feature,
            quantity=quantity,
            unit=unit,
            period_start=period_start,
            period_end=period_end,
        )

        logger.debug(f"Tracked usage: {feature} ({quantity} {unit}) for user {user_id}")
        return self._usage_record_to_response(usage_record)

    async def get_usage_summary(
        self, user_id: str, period_start: datetime, period_end: datetime
    ) -> UsageSummaryResponse:
        """
        Get usage summary for a user within a time period.

        Args:
            user_id: User ID
            period_start: Period start date
            period_end: Period end date

        Returns:
            UsageSummaryResponse
        """
        summary = await self.repository.usage_records.get_user_usage_summary(
            user_id, period_start, period_end
        )

        # Calculate total usage across all periods (simplified - in production, query all records)
        total_usage = summary.copy()

        return UsageSummaryResponse(
            user_id=user_id,
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
            features=summary,
            total_usage=total_usage,
        )

    async def check_usage_limits(
        self, user_id: str, feature: str, period_start: Optional[datetime] = None
    ) -> UsageLimitCheckResponse:
        """
        Check if user has exceeded usage limits for a feature.

        Args:
            user_id: User ID
            feature: Feature name
            period_start: Period start date (defaults to current billing period start)

        Returns:
            UsageLimitCheckResponse with limit check results

        Raises:
            NotFoundError: If user has no active subscription
        """
        # Get user's active subscription
        subscription = await self.repository.subscriptions.get_by_user_id(user_id)
        if not subscription:
            raise NotFoundError("User has no active subscription")

        # Get plan limits
        plan = subscription.plan
        if not plan:
            plan = await self.repository.plans.get_by_id(subscription.plan_id)

        # Determine period
        if period_start is None:
            period_start = subscription.current_period_start
        period_end = subscription.current_period_end

        # Get current usage
        usage_records = await self.repository.usage_records.get_by_user_and_feature(
            user_id, feature, period_start, period_end
        )
        current_usage = sum(record.quantity for record in usage_records)

        # Get limit based on feature
        limit = None
        if feature == "calls":
            limit = plan.max_calls_per_month
        elif feature == "storage":
            limit = plan.max_storage_gb
        elif feature == "users":
            limit = plan.max_users

        # Check if within limit
        within_limit = True
        remaining = None
        if limit is not None:
            remaining = max(0, limit - current_usage)
            within_limit = current_usage < limit

        return UsageLimitCheckResponse(
            feature=feature,
            current_usage=current_usage,
            limit=limit,
            remaining=remaining,
            within_limit=within_limit,
        )

    # ==================== Overage Calculation ====================

    async def calculate_overage_charges(
        self,
        user_id: str,
        period_start: datetime,
        period_end: datetime,
    ) -> Decimal:
        """
        Calculate overage charges for a billing period.

        Args:
            user_id: User ID
            period_start: Billing period start date
            period_end: Billing period end date

        Returns:
            Total overage amount in USD

        Note:
            This method uses the Plan model's `included_minutes` and
            `overage_rate_per_minute` columns, with fallback to `features_json` for backward compatibility.
        """
        subscription = await self.repository.subscriptions.get_by_user_id(user_id)
        if not subscription:
            return Decimal("0.00")

        plan = subscription.plan
        if not plan:
            plan = await self.repository.plans.get_by_id(subscription.plan_id)

        # Get total minutes used
        usage_records = await self.repository.usage_records.get_by_user_and_feature(
            user_id, "call_minutes", period_start, period_end
        )
        total_minutes = sum(record.quantity for record in usage_records)

        # Calculate overage using helper method (with fallback to features_json)
        included_minutes, overage_rate = _get_plan_minutes_data(plan)

        if included_minutes == 0:  # Unlimited plan
            return Decimal("0.00")

        overage_minutes = max(0, total_minutes - included_minutes)
        return Decimal(overage_minutes) * overage_rate

    # ==================== Invoice Generation ====================

    async def generate_billing_invoice(
        self,
        subscription_id: str,
        period_start: datetime,
        period_end: datetime,
    ) -> InvoiceResponse:
        """
        Generate invoice for billing period including overage.

        Creates invoice in both database and Stripe.

        Args:
            subscription_id: Subscription ID
            period_start: Billing period start date
            period_end: Billing period end date

        Returns:
            InvoiceResponse

        Raises:
            NotFoundError: If subscription not found
            ValidationError: If invoice generation fails
        """
        # Get subscription with plan eagerly loaded
        result = await self.repository.session.execute(
            select(Subscription)
            .options(selectinload(Subscription.plan))
            .where(Subscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()
        if not subscription:
            raise NotFoundError(f"Subscription with ID {subscription_id} not found")

        plan = subscription.plan
        if not plan:
            plan = await self.repository.plans.get_by_id(subscription.plan_id)

        # Calculate base subscription amount
        base_amount = Decimal("0.00")
        if subscription.billing_cycle == "monthly" and plan.price_monthly:
            base_amount = Decimal(str(plan.price_monthly))
        elif subscription.billing_cycle == "yearly" and plan.price_yearly:
            base_amount = Decimal(str(plan.price_yearly))

        # Calculate overage charges
        overage_amount = await self.calculate_overage_charges(
            subscription.user_id, period_start, period_end
        )

        total_amount = base_amount + overage_amount

        # Build invoice items
        items = [
            {
                "type": "subscription",
                "description": f"{plan.display_name} - {subscription.billing_cycle.capitalize()}",
                "amount": float(base_amount),
                "quantity": 1,
            }
        ]

        if overage_amount > 0:
            # Get usage to calculate overage minutes
            usage_records = await self.repository.usage_records.get_by_user_and_feature(
                subscription.user_id, "call_minutes", period_start, period_end
            )
            total_minutes = sum(record.quantity for record in usage_records)

            # Get included minutes and overage rate (with fallback to features_json)
            included_minutes, overage_rate = _get_plan_minutes_data(plan)
            overage_minutes = max(0, total_minutes - included_minutes)

            items.append(
                {
                    "type": "overage",
                    "description": f"Overage: {overage_minutes} minutes @ ${overage_rate}/min",
                    "amount": float(overage_amount),
                    "quantity": overage_minutes,
                    "unit": "minutes",
                }
            )

        # Generate invoice number
        invoice_number = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{subscription_id[:8].upper()}"

        # Create invoice in database
        invoice = await self.repository.invoices.create_invoice(
            user_id=subscription.user_id,
            subscription_id=subscription_id,
            invoice_number=invoice_number,
            amount=total_amount,
            currency=plan.currency,
            due_date=period_end,
            items_json=json.dumps(items),
            payment_provider=subscription.payment_provider,
        )

        logger.info(
            f"Generated invoice {invoice.id} for subscription {subscription_id}: "
            f"${total_amount} (base: ${base_amount}, overage: ${overage_amount})"
        )

        return self._invoice_to_response(invoice)

    # ==================== Payment Provider Integration ====================

    async def handle_checkout_completed(self, session_data: Dict[str, Any]) -> None:
        """
        Handle Stripe checkout.session.completed event.

        Creates subscription in database after successful checkout.

        Args:
            session_data: Stripe checkout session object
        """
        user_id = session_data.get("metadata", {}).get("user_id")
        plan_id = session_data.get("metadata", {}).get("plan_id")
        subscription_id = session_data.get("subscription")

        if not user_id or not plan_id or not subscription_id:
            logger.warning(f"Incomplete checkout session data: {session_data}")
            return

        # Check if subscription already exists
        existing = await self.repository.subscriptions.get_by_payment_provider_id(
            "stripe", subscription_id
        )
        if existing:
            logger.info(f"Subscription already exists for Stripe subscription {subscription_id}")
            return

        # Get subscription details from Stripe
        try:
            stripe_service = get_stripe_service(self.repository.session)
            stripe_subscription = await stripe_service.get_subscription(subscription_id)

            # Extract billing period from Stripe subscription
            period_start = datetime.fromtimestamp(
                stripe_subscription.get("current_period_start", 0), tz=None
            )
            period_end = datetime.fromtimestamp(
                stripe_subscription.get("current_period_end", 0), tz=None
            )
            
            # Extract trial period from Stripe subscription
            trial_start = None
            trial_end = None
            if stripe_subscription.get("trial_start"):
                trial_start = datetime.fromtimestamp(
                    stripe_subscription.get("trial_start", 0), tz=None
                )
            if stripe_subscription.get("trial_end"):
                trial_end = datetime.fromtimestamp(
                    stripe_subscription.get("trial_end", 0), tz=None
                )
            
            # Determine billing cycle from Stripe subscription
            items = stripe_subscription.get("items", {}).get("data", [])
            billing_cycle = "monthly"  # Default
            if items:
                interval = items[0].get("price", {}).get("recurring", {}).get("interval", "month")
                if interval == "year":
                    billing_cycle = "yearly"
            
            # Determine subscription status from Stripe
            stripe_status = stripe_subscription.get("status", "active")
            # Map Stripe status to our status
            status_map = {
                "trialing": "trialing",
                "active": "active",
                "past_due": "past_due",
                "canceled": "canceled",
                "unpaid": "past_due",
            }
            subscription_status = status_map.get(stripe_status, "active")
            
            # If trial is active, ensure status is trialing
            if trial_end and trial_end > datetime.utcnow():
                subscription_status = "trialing"

            # Create subscription in database with Stripe data
            subscription = await self.create_subscription(
                user_id=user_id,
                plan_id=plan_id,
                billing_cycle=billing_cycle,
                payment_provider="stripe",
                payment_provider_subscription_id=subscription_id,
                use_stripe=False,  # Already created in Stripe
                current_period_start=period_start,
                current_period_end=period_end,
                trial_start=trial_start,
                trial_end=trial_end,
            )
            
            # Update status if it differs from what was set (repository sets based on trial, but Stripe might have different status)
            if subscription.status != subscription_status:
                await self.repository.subscriptions.update(
                    subscription.id, status=subscription_status
                )

            logger.info(
                f"Created subscription from checkout session for user {user_id}, "
                f"Stripe subscription {subscription_id}"
            )
        except Exception as e:
            logger.error(f"Error handling checkout completed: {e}", exc_info=True)
            raise

    async def handle_subscription_created(self, subscription_data: Dict[str, Any]) -> None:
        """
        Handle Stripe customer.subscription.created event.

        Args:
            subscription_data: Stripe subscription object
        """
        subscription_id = subscription_data.get("id")
        user_id = subscription_data.get("metadata", {}).get("user_id")
        plan_id = subscription_data.get("metadata", {}).get("plan_id")

        if not subscription_id:
            logger.warning(f"Missing subscription ID in subscription.created event")
            return

        # Check if subscription already exists
        existing = await self.repository.subscriptions.get_by_payment_provider_id(
            "stripe", subscription_id
        )
        if existing:
            logger.info(f"Subscription already exists for Stripe subscription {subscription_id}")
            return

        if user_id and plan_id:
            # Extract billing period from Stripe subscription
            period_start = datetime.fromtimestamp(
                subscription_data.get("current_period_start", 0), tz=None
            )
            period_end = datetime.fromtimestamp(
                subscription_data.get("current_period_end", 0), tz=None
            )
            
            # Extract trial period
            trial_start = None
            trial_end = None
            if subscription_data.get("trial_start"):
                trial_start = datetime.fromtimestamp(
                    subscription_data.get("trial_start", 0), tz=None
                )
            if subscription_data.get("trial_end"):
                trial_end = datetime.fromtimestamp(
                    subscription_data.get("trial_end", 0), tz=None
                )
            
            # Determine billing cycle
            items = subscription_data.get("items", {}).get("data", [])
            billing_cycle = "monthly"
            if items:
                interval = items[0].get("price", {}).get("recurring", {}).get("interval", "month")
                if interval == "year":
                    billing_cycle = "yearly"

            await self.create_subscription(
                user_id=user_id,
                plan_id=plan_id,
                billing_cycle=billing_cycle,
                payment_provider="stripe",
                payment_provider_subscription_id=subscription_id,
                use_stripe=False,
                current_period_start=period_start,
                current_period_end=period_end,
                trial_start=trial_start,
                trial_end=trial_end,
            )

            logger.info(f"Created subscription from Stripe event for user {user_id}")

    async def handle_subscription_updated(self, subscription_data: Dict[str, Any]) -> None:
        """
        Handle Stripe customer.subscription.updated event.

        Updates subscription status and billing period.

        Args:
            subscription_data: Stripe subscription object
        """
        subscription_id = subscription_data.get("id")
        if not subscription_id:
            return

        subscription = await self.repository.subscriptions.get_by_payment_provider_id(
            "stripe", subscription_id
        )
        if not subscription:
            logger.warning(f"Subscription not found for Stripe subscription {subscription_id}")
            return

        # Update subscription status
        stripe_status = subscription_data.get("status", "")
        status_mapping = {
            "trialing": "trialing",
            "active": "active",
            "canceled": "canceled",
            "past_due": "past_due",
            "unpaid": "past_due",
        }
        new_status = status_mapping.get(stripe_status, subscription.status)
        
        # Also update trial dates if present
        trial_start = None
        trial_end = None
        if subscription_data.get("trial_start"):
            trial_start = datetime.fromtimestamp(
                subscription_data.get("trial_start", 0), tz=None
            )
        if subscription_data.get("trial_end"):
            trial_end = datetime.fromtimestamp(
                subscription_data.get("trial_end", 0), tz=None
            )
        
        # If trial is active, ensure status is trialing
        if trial_end and trial_end > datetime.utcnow():
            new_status = "trialing"

        # Update billing period
        period_start = datetime.fromtimestamp(
            subscription_data.get("current_period_start", 0), tz=None
        )
        period_end = datetime.fromtimestamp(
            subscription_data.get("current_period_end", 0), tz=None
        )

        # Extract plan_id from Stripe metadata if missing locally
        plan_id = subscription.plan_id
        stripe_metadata = subscription_data.get("metadata", {})
        if not plan_id and stripe_metadata.get("plan_id"):
            plan_id = stripe_metadata.get("plan_id")
            logger.info(f"Extracted plan_id {plan_id} from Stripe metadata for subscription {subscription.id}")

        updates = {
            "status": new_status,
        }
        
        # Update plan_id if we extracted it from Stripe
        if plan_id and plan_id != subscription.plan_id:
            updates["plan_id"] = plan_id

        # Update period if changed
        if period_start and period_end:
            if subscription.current_period_start != period_start:
                updates["current_period_start"] = period_start
            if subscription.current_period_end != period_end:
                updates["current_period_end"] = period_end
        
        # Update trial dates if changed
        if trial_start and subscription.trial_start != trial_start:
            updates["trial_start"] = trial_start
        if trial_end and subscription.trial_end != trial_end:
            updates["trial_end"] = trial_end

        # Update cancel_at_period_end
        cancel_at_period_end = subscription_data.get("cancel_at_period_end", False)
        if subscription.cancel_at_period_end != cancel_at_period_end:
            updates["cancel_at_period_end"] = cancel_at_period_end

        await self.repository.subscriptions.update(subscription.id, **updates)
        logger.info(f"Updated subscription {subscription.id} from Stripe event")

    async def handle_subscription_deleted(self, subscription_data: Dict[str, Any]) -> None:
        """
        Handle Stripe customer.subscription.deleted event.

        Cancels subscription in database.

        Args:
            subscription_data: Stripe subscription object
        """
        subscription_id = subscription_data.get("id")
        if not subscription_id:
            return

        subscription = await self.repository.subscriptions.get_by_payment_provider_id(
            "stripe", subscription_id
        )
        if not subscription:
            logger.warning(f"Subscription not found for Stripe subscription {subscription_id}")
            return

        # Cancel subscription
        await self.cancel_subscription(subscription.id, cancel_at_period_end=False)
        logger.info(f"Canceled subscription {subscription.id} from Stripe deletion event")

    async def handle_invoice_paid(self, invoice_data: Dict[str, Any]) -> None:
        """
        Handle Stripe invoice.paid event.

        Marks invoice as paid in database.

        Args:
            invoice_data: Stripe invoice object
        """
        invoice_id = invoice_data.get("id")
        subscription_id = invoice_data.get("subscription")

        if not invoice_id:
            return

        # Find invoice by Stripe invoice ID
        invoice = await self.repository.invoices.get_by_payment_provider_id(
            "stripe", invoice_id
        )

        if invoice:
            # Mark as paid
            paid_at = datetime.fromtimestamp(invoice_data.get("paid", 0), tz=None)
            await self.repository.invoices.mark_as_paid(invoice.id, paid_at=paid_at)
            logger.info(f"Marked invoice {invoice.id} as paid")
        else:
            # Invoice might not exist yet, create it if we have subscription
            if subscription_id:
                subscription = await self.repository.subscriptions.get_by_payment_provider_id(
                    "stripe", subscription_id
                )
                if subscription:
                    # Generate invoice for the period
                    period_start = datetime.fromtimestamp(
                        invoice_data.get("period_start", 0), tz=None
                    )
                    period_end = datetime.fromtimestamp(
                        invoice_data.get("period_end", 0), tz=None
                    )
                    await self.generate_billing_invoice(
                        subscription.id, period_start, period_end
                    )

    async def handle_invoice_payment_failed(self, invoice_data: Dict[str, Any]) -> None:
        """
        Handle Stripe invoice.payment_failed event.

        Updates invoice status and may suspend subscription.

        Args:
            invoice_data: Stripe invoice object
        """
        invoice_id = invoice_data.get("id")
        subscription_id = invoice_data.get("subscription")

        if invoice_id:
            invoice = await self.repository.invoices.get_by_payment_provider_id(
                "stripe", invoice_id
            )
            if invoice:
                # Update invoice status
                await self.repository.invoices.update(invoice.id, status="uncollectible")
                logger.warning(f"Marked invoice {invoice.id} as uncollectible")

        # Optionally suspend subscription after multiple failures
        if subscription_id:
            subscription = await self.repository.subscriptions.get_by_payment_provider_id(
                "stripe", subscription_id
            )
            if subscription:
                # Update subscription status to past_due
                await self.repository.subscriptions.update(
                    subscription.id, status="past_due"
                )
                logger.warning(f"Updated subscription {subscription.id} to past_due status")

    async def handle_payment_webhook(
        self, provider: str, event_type: str, event_data: Dict[str, Any]
    ) -> None:
        """
        Handle webhook events from payment provider.

        Args:
            provider: Payment provider name (e.g., "stripe")
            event_type: Event type (e.g., "subscription.updated", "invoice.paid")
            event_data: Event data from payment provider

        Note:
            This method routes webhook events to specific handlers.
        """
        logger.info(f"Received {provider} webhook: {event_type}")

        if provider != "stripe":
            logger.warning(f"Unsupported payment provider: {provider}")
            return

        try:
            if event_type == "checkout.session.completed":
                await self.handle_checkout_completed(event_data)
            elif event_type == "customer.subscription.created":
                await self.handle_subscription_created(event_data)
            elif event_type == "customer.subscription.updated":
                await self.handle_subscription_updated(event_data)
            elif event_type == "customer.subscription.deleted":
                await self.handle_subscription_deleted(event_data)
            elif event_type == "invoice.paid":
                await self.handle_invoice_paid(event_data)
            elif event_type == "invoice.payment_failed":
                await self.handle_invoice_payment_failed(event_data)
            else:
                logger.debug(f"Unhandled webhook event type: {event_type}")

            logger.debug(f"Processed {provider} webhook: {event_type}")
        except Exception as e:
            logger.error(f"Error processing webhook {event_type}: {e}", exc_info=True)
            raise


def get_billing_service(session: AsyncSession) -> BillingService:
    """
    Factory function to create BillingService instance.

    Args:
        session: Database session

    Returns:
        BillingService instance
    """
    return BillingService(session)
