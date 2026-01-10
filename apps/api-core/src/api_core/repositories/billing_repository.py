"""Billing repository for subscription and invoice data access operations."""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from api_core.database.models import Invoice, Plan, Subscription, UsageRecord
from api_core.exceptions import ConflictError, DatabaseError, NotFoundError
from api_core.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class PlanRepository(BaseRepository[Plan]):
    """Repository for subscription plan data access operations."""

    def __init__(self, session: AsyncSession):
        """Initialize plan repository."""
        super().__init__(Plan, session)

    async def get_by_name(self, name: str) -> Optional[Plan]:
        """
        Get plan by name.

        Args:
            name: Plan name

        Returns:
            Plan instance or None if not found
        """
        try:
            result = await self.session.execute(select(Plan).where(Plan.name == name))
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting plan by name {name}: {e}")
            raise DatabaseError("Failed to retrieve plan by name") from e

    async def get_active_plans(self) -> List[Plan]:
        """
        Get all active public plans.

        Returns:
            List of active plans
        """
        try:
            result = await self.session.execute(
                select(Plan).where(and_(Plan.is_active == True, Plan.is_public == True))
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting active plans: {e}")
            raise DatabaseError("Failed to retrieve active plans") from e


class SubscriptionRepository(BaseRepository[Subscription]):
    """Repository for subscription data access operations."""

    def __init__(self, session: AsyncSession):
        """Initialize subscription repository."""
        super().__init__(Subscription, session)

    async def get_by_user_id(self, user_id: str) -> Optional[Subscription]:
        """
        Get active or trialing subscription for a user.

        Args:
            user_id: User ID

        Returns:
            Subscription instance or None if not found
        """
        try:
            from sqlalchemy.orm import selectinload
            from sqlalchemy import or_
            
            result = await self.session.execute(
                select(Subscription)
                .options(selectinload(Subscription.plan))  # Eagerly load plan relationship
                .where(Subscription.user_id == user_id)
                .where(or_(
                    Subscription.status == "active",
                    Subscription.status == "trialing"
                ))
                .order_by(Subscription.created_at.desc())
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting subscription for user {user_id}: {e}")
            raise DatabaseError("Failed to retrieve subscription") from e

    async def get_all_by_user_id(self, user_id: str) -> List[Subscription]:
        """
        Get all subscriptions for a user.

        Args:
            user_id: User ID

        Returns:
            List of subscription instances
        """
        try:
            result = await self.session.execute(
                select(Subscription)
                .where(Subscription.user_id == user_id)
                .order_by(Subscription.created_at.desc())
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting all subscriptions for user {user_id}: {e}")
            raise DatabaseError("Failed to retrieve subscriptions") from e

    async def get_by_payment_provider_id(
        self, provider: str, provider_subscription_id: str
    ) -> Optional[Subscription]:
        """
        Get subscription by payment provider subscription ID.

        Args:
            provider: Payment provider name (e.g., "stripe")
            provider_subscription_id: Payment provider subscription ID

        Returns:
            Subscription instance or None if not found
        """
        try:
            result = await self.session.execute(
                select(Subscription).where(
                    and_(
                        Subscription.payment_provider == provider,
                        Subscription.payment_provider_subscription_id == provider_subscription_id,
                    )
                )
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(
                f"Error getting subscription by provider ID {provider_subscription_id}: {e}"
            )
            raise DatabaseError("Failed to retrieve subscription by provider ID") from e

    async def get_by_status(self, status: str, skip: int = 0, limit: int = 100) -> List[Subscription]:
        """
        Get subscriptions by status.

        Args:
            status: Subscription status
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of subscription instances
        """
        try:
            result = await self.session.execute(
                select(Subscription)
                .where(Subscription.status == status)
                .offset(skip)
                .limit(limit)
                .order_by(Subscription.created_at.desc())
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting subscriptions by status {status}: {e}")
            raise DatabaseError("Failed to retrieve subscriptions by status") from e

    async def get_expiring_soon(self, days: int = 7) -> List[Subscription]:
        """
        Get subscriptions expiring within the specified number of days.

        Args:
            days: Number of days to look ahead

        Returns:
            List of subscription instances
        """
        try:
            cutoff_date = datetime.utcnow() + timedelta(days=days)
            result = await self.session.execute(
                select(Subscription).where(
                    and_(
                        Subscription.status == "active",
                        Subscription.current_period_end <= cutoff_date,
                        Subscription.cancel_at_period_end == False,
                    )
                )
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting expiring subscriptions: {e}")
            raise DatabaseError("Failed to retrieve expiring subscriptions") from e

    async def create_subscription(
        self,
        user_id: str,
        plan_id: str,
        billing_cycle: str = "monthly",
        current_period_start: Optional[datetime] = None,
        current_period_end: Optional[datetime] = None,
        payment_provider: Optional[str] = None,
        payment_provider_subscription_id: Optional[str] = None,
        trial_start: Optional[datetime] = None,
        trial_end: Optional[datetime] = None,
        **kwargs,
    ) -> Subscription:
        """
        Create a new subscription.

        Args:
            user_id: User ID
            plan_id: Plan ID
            billing_cycle: Billing cycle (monthly or yearly)
            current_period_start: Start of current billing period
            current_period_end: End of current billing period
            payment_provider: Payment provider name
            payment_provider_subscription_id: Payment provider subscription ID
            trial_start: Trial start date
            trial_end: Trial end date
            **kwargs: Additional subscription fields

        Returns:
            Created subscription instance

        Raises:
            ConflictError: If subscription already exists
            DatabaseError: If database operation fails
        """
        try:
            # Set default period dates if not provided
            now = datetime.utcnow()
            if current_period_start is None:
                current_period_start = now
            if current_period_end is None:
                if billing_cycle == "yearly":
                    current_period_end = now + timedelta(days=365)
                else:
                    current_period_end = now + timedelta(days=30)

            # Determine status: trialing if trial is active, otherwise active
            now = datetime.utcnow()
            subscription_status = "active"
            if trial_end and trial_end > now:
                subscription_status = "trialing"
            
            subscription = await self.create(
                user_id=user_id,
                plan_id=plan_id,
                status=subscription_status,
                billing_cycle=billing_cycle,
                current_period_start=current_period_start,
                current_period_end=current_period_end,
                payment_provider=payment_provider,
                payment_provider_subscription_id=payment_provider_subscription_id,
                trial_start=trial_start,
                trial_end=trial_end,
                **kwargs,
            )

            logger.info(f"Created subscription: {subscription.id} for user: {user_id}")
            return subscription

        except IntegrityError as e:
            logger.error(f"Integrity error creating subscription: {e}")
            await self.session.rollback()
            raise ConflictError("Subscription creation failed due to constraint violation") from e
        except SQLAlchemyError as e:
            logger.error(f"Error creating subscription: {e}")
            await self.session.rollback()
            raise DatabaseError("Failed to create subscription") from e

    async def cancel_subscription(
        self, subscription_id: str, cancel_at_period_end: bool = True
    ) -> Optional[Subscription]:
        """
        Cancel a subscription.

        Args:
            subscription_id: Subscription ID
            cancel_at_period_end: Whether to cancel at period end or immediately

        Returns:
            Updated subscription instance or None if not found
        """
        try:
            from sqlalchemy.orm import selectinload
            
            # Eagerly load plan relationship to avoid greenlet_spawn error
            result = await self.session.execute(
                select(Subscription)
                .options(selectinload(Subscription.plan))
                .where(Subscription.id == subscription_id)
            )
            subscription = result.scalar_one_or_none()
            if not subscription:
                return None

            if cancel_at_period_end:
                # Mark for cancellation at period end
                subscription.cancel_at_period_end = True
                logger.info(
                    f"Marked subscription {subscription_id} for cancellation at period end. "
                    f"Status remains: {subscription.status}, cancel_at_period_end: {subscription.cancel_at_period_end}"
                )
            else:
                # Cancel immediately
                subscription.status = "canceled"
                subscription.canceled_at = datetime.utcnow()
                subscription.cancel_at_period_end = False
                logger.info(
                    f"Canceled subscription {subscription_id} immediately. "
                    f"Status: {subscription.status}, canceled_at: {subscription.canceled_at}"
                )

            await self.session.flush()
            await self.session.refresh(subscription)
            logger.info(
                f"Canceled subscription: {subscription_id}. "
                f"Final status: {subscription.status}, cancel_at_period_end: {subscription.cancel_at_period_end}"
            )
            return subscription

        except SQLAlchemyError as e:
            logger.error(f"Error canceling subscription {subscription_id}: {e}")
            await self.session.rollback()
            raise DatabaseError("Failed to cancel subscription") from e

    async def update_subscription_period(
        self, subscription_id: str, period_start: datetime, period_end: datetime
    ) -> Optional[Subscription]:
        """
        Update subscription billing period.

        Args:
            subscription_id: Subscription ID
            period_start: New period start date
            period_end: New period end date

        Returns:
            Updated subscription instance or None if not found
        """
        return await self.update(
            subscription_id,
            current_period_start=period_start,
            current_period_end=period_end,
        )


class InvoiceRepository(BaseRepository[Invoice]):
    """Repository for invoice data access operations."""

    def __init__(self, session: AsyncSession):
        """Initialize invoice repository."""
        super().__init__(Invoice, session)

    async def get_by_user_id(
        self, user_id: str, skip: int = 0, limit: int = 100
    ) -> List[Invoice]:
        """
        Get invoices for a user.

        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of invoice instances
        """
        try:
            result = await self.session.execute(
                select(Invoice)
                .where(Invoice.user_id == user_id)
                .offset(skip)
                .limit(limit)
                .order_by(Invoice.created_at.desc())
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting invoices for user {user_id}: {e}")
            raise DatabaseError("Failed to retrieve invoices") from e

    async def get_by_invoice_number(self, invoice_number: str) -> Optional[Invoice]:
        """
        Get invoice by invoice number.

        Args:
            invoice_number: Invoice number

        Returns:
            Invoice instance or None if not found
        """
        try:
            result = await self.session.execute(
                select(Invoice).where(Invoice.invoice_number == invoice_number)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting invoice by number {invoice_number}: {e}")
            raise DatabaseError("Failed to retrieve invoice by number") from e

    async def get_by_payment_provider_id(
        self, provider: str, provider_invoice_id: str
    ) -> Optional[Invoice]:
        """
        Get invoice by payment provider invoice ID.

        Args:
            provider: Payment provider name
            provider_invoice_id: Payment provider invoice ID

        Returns:
            Invoice instance or None if not found
        """
        try:
            result = await self.session.execute(
                select(Invoice).where(
                    and_(
                        Invoice.payment_provider == provider,
                        Invoice.payment_provider_invoice_id == provider_invoice_id,
                    )
                )
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting invoice by provider ID {provider_invoice_id}: {e}")
            raise DatabaseError("Failed to retrieve invoice by provider ID") from e

    async def get_by_status(
        self, status: str, skip: int = 0, limit: int = 100
    ) -> List[Invoice]:
        """
        Get invoices by status.

        Args:
            status: Invoice status
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of invoice instances
        """
        try:
            result = await self.session.execute(
                select(Invoice)
                .where(Invoice.status == status)
                .offset(skip)
                .limit(limit)
                .order_by(Invoice.created_at.desc())
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting invoices by status {status}: {e}")
            raise DatabaseError("Failed to retrieve invoices by status") from e

    async def create_invoice(
        self,
        user_id: str,
        subscription_id: Optional[str] = None,
        invoice_number: str = "",
        amount: Decimal = Decimal("0.00"),
        currency: str = "USD",
        due_date: Optional[datetime] = None,
        items_json: Optional[str] = None,
        payment_provider: Optional[str] = None,
        payment_provider_invoice_id: Optional[str] = None,
        **kwargs,
    ) -> Invoice:
        """
        Create a new invoice.

        Args:
            user_id: User ID
            subscription_id: Optional subscription ID
            invoice_number: Invoice number
            amount: Invoice amount
            currency: Currency code
            due_date: Due date
            items_json: JSON string of invoice items
            payment_provider: Payment provider name
            payment_provider_invoice_id: Payment provider invoice ID
            **kwargs: Additional invoice fields

        Returns:
            Created invoice instance

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            if due_date is None:
                due_date = datetime.utcnow() + timedelta(days=30)

            invoice = await self.create(
                user_id=user_id,
                subscription_id=subscription_id,
                invoice_number=invoice_number,
                amount=amount,
                currency=currency,
                due_date=due_date,
                items_json=items_json,
                payment_provider=payment_provider,
                payment_provider_invoice_id=payment_provider_invoice_id,
                status="draft",
                **kwargs,
            )

            logger.info(f"Created invoice: {invoice.id} for user: {user_id}")
            return invoice

        except SQLAlchemyError as e:
            logger.error(f"Error creating invoice: {e}")
            await self.session.rollback()
            raise DatabaseError("Failed to create invoice") from e

    async def mark_as_paid(
        self, invoice_id: str, paid_at: Optional[datetime] = None
    ) -> Optional[Invoice]:
        """
        Mark invoice as paid.

        Args:
            invoice_id: Invoice ID
            paid_at: Payment timestamp (defaults to now)

        Returns:
            Updated invoice instance or None if not found
        """
        if paid_at is None:
            paid_at = datetime.utcnow()

        return await self.update(invoice_id, status="paid", paid_at=paid_at)


class UsageRecordRepository(BaseRepository[UsageRecord]):
    """Repository for usage record data access operations."""

    def __init__(self, session: AsyncSession):
        """Initialize usage record repository."""
        super().__init__(UsageRecord, session)

    async def get_by_user_and_feature(
        self, user_id: str, feature: str, period_start: datetime, period_end: datetime
    ) -> List[UsageRecord]:
        """
        Get usage records for a user and feature within a time period.

        Args:
            user_id: User ID
            feature: Feature name
            period_start: Period start date
            period_end: Period end date

        Returns:
            List of usage record instances
        """
        try:
            result = await self.session.execute(
                select(UsageRecord).where(
                    and_(
                        UsageRecord.user_id == user_id,
                        UsageRecord.feature == feature,
                        UsageRecord.period_start >= period_start,
                        UsageRecord.period_end <= period_end,
                    )
                )
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting usage records: {e}")
            raise DatabaseError("Failed to retrieve usage records") from e

    async def get_user_usage_summary(
        self, user_id: str, period_start: datetime, period_end: datetime
    ) -> dict:
        """
        Get usage summary for a user within a time period.

        Args:
            user_id: User ID
            period_start: Period start date
            period_end: Period end date

        Returns:
            Dictionary with feature usage totals
        """
        try:
            from sqlalchemy import func

            result = await self.session.execute(
                select(
                    UsageRecord.feature,
                    func.sum(UsageRecord.quantity).label("total"),
                )
                .where(
                    and_(
                        UsageRecord.user_id == user_id,
                        UsageRecord.period_start >= period_start,
                        UsageRecord.period_end <= period_end,
                    )
                )
                .group_by(UsageRecord.feature)
            )
            return {row.feature: row.total for row in result.all()}
        except SQLAlchemyError as e:
            logger.error(f"Error getting usage summary: {e}")
            raise DatabaseError("Failed to retrieve usage summary") from e

    async def create_usage_record(
        self,
        user_id: str,
        feature: str,
        quantity: int = 1,
        unit: str = "count",
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
        **kwargs,
    ) -> UsageRecord:
        """
        Create a usage record.

        Args:
            user_id: User ID
            feature: Feature name
            quantity: Usage quantity
            unit: Unit of measurement
            period_start: Period start date (defaults to now)
            period_end: Period end date (defaults to period_start + 1 day)
            **kwargs: Additional usage record fields

        Returns:
            Created usage record instance
        """
        try:
            now = datetime.utcnow()
            if period_start is None:
                period_start = now
            if period_end is None:
                period_end = period_start + timedelta(days=1)

            usage_record = await self.create(
                user_id=user_id,
                feature=feature,
                quantity=quantity,
                unit=unit,
                period_start=period_start,
                period_end=period_end,
                **kwargs,
            )

            logger.debug(f"Created usage record: {usage_record.id} for user: {user_id}, feature: {feature}")
            return usage_record

        except SQLAlchemyError as e:
            logger.error(f"Error creating usage record: {e}")
            await self.session.rollback()
            raise DatabaseError("Failed to create usage record") from e


class BillingRepository:
    """Aggregate repository for all billing-related operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize billing repository.

        Args:
            session: Database session
        """
        self.session = session
        self.plans = PlanRepository(session)
        self.subscriptions = SubscriptionRepository(session)
        self.invoices = InvoiceRepository(session)
        self.usage_records = UsageRecordRepository(session)
