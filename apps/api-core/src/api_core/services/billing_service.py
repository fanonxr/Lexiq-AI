"""Billing and subscription service with business logic."""

import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from api_core.database.models import Invoice, Plan, Subscription, UsageRecord
from api_core.exceptions import ConflictError, NotFoundError, ValidationError
from api_core.models.billing import (
    InvoiceResponse,
    PlanResponse,
    SubscriptionResponse,
    UsageLimitCheckResponse,
    UsageRecordResponse,
    UsageSummaryResponse,
)
from api_core.repositories.billing_repository import BillingRepository

logger = logging.getLogger(__name__)


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
        if include_plan and subscription.plan:
            plan_response = self._plan_to_response(subscription.plan)

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

    async def get_user_subscription(
        self, user_id: str, include_plan: bool = True
    ) -> Optional[SubscriptionResponse]:
        """
        Get active subscription for a user.

        Args:
            user_id: User ID
            include_plan: Whether to include plan details

        Returns:
            SubscriptionResponse or None if no active subscription
        """
        subscription = await self.repository.subscriptions.get_by_user_id(user_id)
        if not subscription:
            return None

        return self._subscription_to_response(subscription, include_plan=include_plan)

    async def create_subscription(
        self,
        user_id: str,
        plan_id: str,
        billing_cycle: str = "monthly",
        payment_method_id: Optional[str] = None,
        payment_provider: Optional[str] = None,
        payment_provider_subscription_id: Optional[str] = None,
        trial_days: Optional[int] = None,
    ) -> SubscriptionResponse:
        """
        Create a new subscription for a user.

        Args:
            user_id: User ID
            plan_id: Plan ID
            billing_cycle: Billing cycle (monthly or yearly)
            payment_method_id: Payment method ID
            payment_provider: Payment provider name (e.g., "stripe")
            payment_provider_subscription_id: Payment provider subscription ID
            trial_days: Number of trial days (optional)

        Returns:
            Created SubscriptionResponse

        Raises:
            NotFoundError: If plan not found
            ConflictError: If user already has active subscription
            ValidationError: If billing cycle is invalid
        """
        # Validate billing cycle
        if billing_cycle not in ["monthly", "yearly"]:
            raise ValidationError("Billing cycle must be 'monthly' or 'yearly'")

        # Check if plan exists
        plan = await self.repository.plans.get_by_id(plan_id)
        if not plan:
            raise NotFoundError(f"Plan with ID {plan_id} not found")

        # Check if user already has active subscription
        existing = await self.repository.subscriptions.get_by_user_id(user_id)
        if existing:
            raise ConflictError("User already has an active subscription")

        # Calculate billing period
        now = datetime.utcnow()
        if billing_cycle == "yearly":
            period_end = now + timedelta(days=365)
        else:
            period_end = now + timedelta(days=30)

        # Handle trial period
        trial_start = None
        trial_end = None
        if trial_days and trial_days > 0:
            trial_start = now
            trial_end = now + timedelta(days=trial_days)
            # Extend period end to include trial
            period_end = trial_end + (period_end - now)

        # Create subscription
        subscription = await self.repository.subscriptions.create_subscription(
            user_id=user_id,
            plan_id=plan_id,
            billing_cycle=billing_cycle,
            current_period_start=now,
            current_period_end=period_end,
            payment_provider=payment_provider,
            payment_provider_subscription_id=payment_provider_subscription_id,
            payment_method_id=payment_method_id,
            trial_start=trial_start,
            trial_end=trial_end,
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
        subscription = await self.repository.subscriptions.get_by_id(subscription_id)
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

        return self._subscription_to_response(updated, include_plan=True)

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
        """
        subscription = await self.repository.subscriptions.cancel_subscription(
            subscription_id, cancel_at_period_end=cancel_at_period_end
        )
        if not subscription:
            raise NotFoundError(f"Subscription with ID {subscription_id} not found")

        logger.info(f"Canceled subscription {subscription_id} (at_period_end={cancel_at_period_end})")
        return self._subscription_to_response(subscription, include_plan=True)

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
            ValidationError: If upgrade is invalid
        """
        subscription = await self.repository.subscriptions.get_by_id(subscription_id)
        if not subscription:
            raise NotFoundError(f"Subscription with ID {subscription_id} not found")

        new_plan = await self.repository.plans.get_by_id(new_plan_id)
        if not new_plan:
            raise NotFoundError(f"Plan with ID {new_plan_id} not found")

        # Update plan
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
        return self._subscription_to_response(updated, include_plan=True)

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
        subscription = await self.repository.subscriptions.get_by_id(subscription_id)
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
        return self._subscription_to_response(updated, include_plan=True)

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

    # ==================== Payment Provider Integration ====================

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
            This is a placeholder for payment provider integration.
            In production, implement actual webhook handling for your payment provider.
        """
        logger.info(f"Received {provider} webhook: {event_type}")

        # Placeholder implementation
        # In production, implement:
        # - Verify webhook signature
        # - Handle subscription.updated, subscription.deleted, invoice.paid, etc.
        # - Update local subscription/invoice records
        # - Send notifications if needed

        if event_type == "subscription.updated":
            provider_sub_id = event_data.get("subscription_id")
            if provider_sub_id:
                subscription = await self.repository.subscriptions.get_by_payment_provider_id(
                    provider, provider_sub_id
                )
                if subscription:
                    # Update subscription status based on provider data
                    status = event_data.get("status", subscription.status)
                    await self.repository.subscriptions.update(
                        subscription.id, status=status
                    )

        elif event_type == "invoice.paid":
            provider_invoice_id = event_data.get("invoice_id")
            if provider_invoice_id:
                invoice = await self.repository.invoices.get_by_payment_provider_id(
                    provider, provider_invoice_id
                )
                if invoice:
                    await self.repository.invoices.mark_as_paid(invoice.id)

        logger.debug(f"Processed {provider} webhook: {event_type}")


def get_billing_service(session: AsyncSession) -> BillingService:
    """
    Factory function to create BillingService instance.

    Args:
        session: Database session

    Returns:
        BillingService instance
    """
    return BillingService(session)
