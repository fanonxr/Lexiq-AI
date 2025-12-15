"""Dashboard service with business logic for aggregating dashboard data."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api_core.database.models import Invoice, Subscription, UsageRecord
from api_core.exceptions import NotFoundError
from api_core.models.billing import UsageSummaryResponse
from api_core.models.dashboard import (
    ActivityFeedResponse,
    ActivityItem,
    BillingStats,
    CallInfo,
    CallListResponse,
    CallStats,
    DashboardStats,
    SubscriptionStats,
    UsageStats,
)
from api_core.repositories.billing_repository import BillingRepository
from api_core.services.billing_service import BillingService

logger = logging.getLogger(__name__)


class DashboardService:
    """Service for dashboard data aggregation and statistics."""

    def __init__(self, session: AsyncSession):
        """
        Initialize dashboard service.

        Args:
            session: Database session
        """
        self.session = session
        self.billing_repository = BillingRepository(session)
        self.billing_service = BillingService(session)

    async def get_dashboard_stats(self, user_id: str) -> DashboardStats:
        """
        Get comprehensive dashboard statistics for a user.

        Aggregates data from multiple sources:
        - Call statistics (from usage records or external service)
        - Usage statistics (from usage records)
        - Subscription statistics (from subscriptions)
        - Billing statistics (from invoices)

        Args:
            user_id: User ID

        Returns:
            DashboardStats with all aggregated statistics
        """
        try:
            # Get subscription stats
            subscription_stats = await self._get_subscription_stats(user_id)

            # Get usage stats for current billing period
            usage_stats = await self._get_usage_stats(user_id, subscription_stats)

            # Get call stats (from usage records for now)
            call_stats = await self._get_call_stats(user_id, subscription_stats)

            # Get billing stats
            billing_stats = await self._get_billing_stats(user_id)

            return DashboardStats(
                user_id=user_id,
                call_stats=call_stats,
                usage_stats=usage_stats,
                subscription_stats=subscription_stats,
                billing_stats=billing_stats,
                last_updated=datetime.utcnow().isoformat(),
            )
        except Exception as e:
            logger.error(f"Error getting dashboard stats for user {user_id}: {e}")
            raise

    async def _get_subscription_stats(self, user_id: str) -> SubscriptionStats:
        """
        Get subscription statistics for a user.

        Args:
            user_id: User ID

        Returns:
            SubscriptionStats
        """
        subscription = await self.billing_repository.subscriptions.get_by_user_id(user_id)

        if not subscription:
            return SubscriptionStats(
                has_active_subscription=False,
                plan_name=None,
                billing_cycle=None,
                current_period_start=None,
                current_period_end=None,
                days_until_renewal=None,
            )

        # Calculate days until renewal
        days_until_renewal = None
        if subscription.current_period_end:
            now = datetime.utcnow()
            if subscription.current_period_end.tzinfo:
                now = now.replace(tzinfo=subscription.current_period_end.tzinfo)
            delta = subscription.current_period_end - now
            days_until_renewal = max(0, delta.days)

        # Get plan name
        plan_name = None
        if subscription.plan:
            plan_name = subscription.plan.display_name or subscription.plan.name

        return SubscriptionStats(
            has_active_subscription=True,
            plan_name=plan_name,
            billing_cycle=subscription.billing_cycle,
            current_period_start=subscription.current_period_start.isoformat()
            if subscription.current_period_start
            else None,
            current_period_end=subscription.current_period_end.isoformat()
            if subscription.current_period_end
            else None,
            days_until_renewal=days_until_renewal,
        )

    async def _get_usage_stats(
        self, user_id: str, subscription_stats: SubscriptionStats
    ) -> UsageStats:
        """
        Get usage statistics for a user.

        Args:
            user_id: User ID
            subscription_stats: Subscription statistics to determine period

        Returns:
            UsageStats
        """
        # Determine period from subscription or use default
        if (
            subscription_stats.has_active_subscription
            and subscription_stats.current_period_start
            and subscription_stats.current_period_end
        ):
            period_start = datetime.fromisoformat(
                subscription_stats.current_period_start.replace("Z", "+00:00")
            )
            period_end = datetime.fromisoformat(
                subscription_stats.current_period_end.replace("Z", "+00:00")
            )
        else:
            # Default to last 30 days
            period_end = datetime.utcnow()
            period_start = period_end - timedelta(days=30)

        # Get usage summary from billing service
        try:
            summary = await self.billing_service.get_usage_summary(
                user_id, period_start, period_end
            )
        except NotFoundError:
            # No subscription, return empty stats
            return UsageStats(
                calls=0,
                storage_gb=0.0,
                api_requests=0,
                period_start=period_start.isoformat(),
                period_end=period_end.isoformat(),
            )

        # Extract usage by feature
        calls = summary.features.get("calls", 0)
        storage_gb = summary.features.get("storage", 0) / 1024.0 if summary.features.get("storage") else 0.0  # Convert MB to GB
        api_requests = summary.features.get("api_requests", 0)

        return UsageStats(
            calls=calls,
            storage_gb=storage_gb,
            api_requests=api_requests,
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
        )

    async def _get_call_stats(
        self, user_id: str, subscription_stats: SubscriptionStats
    ) -> CallStats:
        """
        Get call statistics for a user.

        Currently aggregates from usage records. In production, this would
        integrate with the Voice Gateway or Cognitive Orchestrator service
        to get actual call data.

        Args:
            user_id: User ID
            subscription_stats: Subscription statistics to determine period

        Returns:
            CallStats
        """
        # Determine period from subscription or use default
        if (
            subscription_stats.has_active_subscription
            and subscription_stats.current_period_start
            and subscription_stats.current_period_end
        ):
            period_start = datetime.fromisoformat(
                subscription_stats.current_period_start.replace("Z", "+00:00")
            )
            period_end = datetime.fromisoformat(
                subscription_stats.current_period_end.replace("Z", "+00:00")
            )
        else:
            # Default to last 30 days
            period_end = datetime.utcnow()
            period_start = period_end - timedelta(days=30)

        # Get call usage records
        try:
            call_records = await self.billing_repository.usage_records.get_by_user_and_feature(
                user_id, "calls", period_start, period_end
            )
        except Exception:
            call_records = []

        # Aggregate call statistics
        total_calls = sum(record.quantity for record in call_records)
        # For now, assume all calls are answered (in production, get from actual call data)
        answered_calls = total_calls
        missed_calls = 0
        total_duration = 0.0
        average_duration = 0.0

        # In production, this would query actual call records with duration
        # For now, we'll use placeholder values
        if total_calls > 0:
            # Placeholder: assume average call duration of 3 minutes
            average_duration = 180.0  # seconds
            total_duration = total_calls * average_duration

        return CallStats(
            total_calls=total_calls,
            answered_calls=answered_calls,
            missed_calls=missed_calls,
            average_duration=average_duration,
            total_duration=total_duration,
        )

    async def _get_billing_stats(self, user_id: str) -> BillingStats:
        """
        Get billing statistics for a user.

        Args:
            user_id: User ID

        Returns:
            BillingStats
        """
        # Get all invoices for user
        invoices = await self.billing_repository.invoices.get_by_user_id(user_id, skip=0, limit=1000)

        total_invoices = len(invoices)
        paid_invoices = sum(1 for inv in invoices if inv.status == "paid")
        pending_invoices = sum(1 for inv in invoices if inv.status in ["draft", "open"])

        # Calculate total spent
        total_spent = sum(float(inv.amount) for inv in invoices if inv.status == "paid")
        currency = invoices[0].currency if invoices else "USD"

        return BillingStats(
            total_invoices=total_invoices,
            paid_invoices=paid_invoices,
            pending_invoices=pending_invoices,
            total_spent=total_spent,
            currency=currency,
        )

    async def get_recent_calls(self, user_id: str, limit: int = 10) -> CallListResponse:
        """
        Get recent calls for a user.

        **Note:** This is a placeholder implementation. In production, this would
        integrate with the Voice Gateway or Cognitive Orchestrator service to
        retrieve actual call records.

        Args:
            user_id: User ID
            limit: Maximum number of calls to return

        Returns:
            CallListResponse with recent calls
        """
        # Placeholder: In production, this would query actual call records
        # from the database or call an external service
        logger.warning(
            f"get_recent_calls is a placeholder - actual call data not yet available for user {user_id}"
        )

        # For now, return empty list
        # In production, this would:
        # 1. Query Call table from database, OR
        # 2. Call Voice Gateway/Cognitive Orchestrator API, OR
        # 3. Query from a shared database/event store

        calls: List[CallInfo] = []

        return CallListResponse(
            calls=calls,
            total=0,
            limit=limit,
        )

    async def get_usage_summary(
        self, user_id: str, period: str = "current"
    ) -> UsageSummaryResponse:
        """
        Get usage summary for a user.

        Delegates to BillingService.get_usage_summary() with period handling.

        Args:
            user_id: User ID
            period: Period identifier ("current", "last_month", "last_30_days", or ISO date range)

        Returns:
            UsageSummaryResponse
        """
        # Get subscription to determine period
        subscription = await self.billing_repository.subscriptions.get_by_user_id(user_id)

        if not subscription:
            # No subscription, use default period (last 30 days)
            period_end = datetime.utcnow()
            period_start = period_end - timedelta(days=30)
        else:
            # Use subscription billing period
            period_start = subscription.current_period_start
            period_end = subscription.current_period_end

            # Handle period parameter
            if period == "last_month":
                # Previous month
                now = datetime.utcnow()
                period_end = datetime(now.year, now.month, 1) - timedelta(days=1)
                period_start = datetime(period_end.year, period_end.month, 1)
            elif period == "last_30_days":
                period_end = datetime.utcnow()
                period_start = period_end - timedelta(days=30)
            # "current" uses subscription period (already set)

        return await self.billing_service.get_usage_summary(user_id, period_start, period_end)

    async def get_recent_activity(
        self, user_id: str, limit: int = 20
    ) -> ActivityFeedResponse:
        """
        Get recent activity feed for a user.

        Aggregates recent activities from:
        - Usage records (calls, API requests)
        - Invoices (payments, billing events)
        - Subscriptions (upgrades, cancellations)

        Args:
            user_id: User ID
            limit: Maximum number of activities to return

        Returns:
            ActivityFeedResponse with recent activities
        """
        activities: List[ActivityItem] = []

        # Get recent usage records
        try:
            period_end = datetime.utcnow()
            period_start = period_end - timedelta(days=30)

            usage_records = await self.billing_repository.usage_records.get_by_user_and_feature(
                user_id, "calls", period_start, period_end
            )

            # Limit and sort by created_at
            usage_records = sorted(
                usage_records, key=lambda r: r.created_at, reverse=True
            )[:limit]

            for record in usage_records:
                activities.append(
                    ActivityItem(
                        id=record.id,
                        type="usage",
                        title=f"Call usage tracked",
                        description=f"{record.quantity} call(s) recorded",
                        timestamp=record.created_at.isoformat(),
                        metadata={"feature": record.feature, "quantity": record.quantity},
                    )
                )
        except Exception as e:
            logger.warning(f"Error getting usage records for activity feed: {e}")

        # Get recent invoices
        try:
            invoices = await self.billing_repository.invoices.get_by_user_id(
                user_id, skip=0, limit=limit
            )
            invoices = sorted(invoices, key=lambda inv: inv.created_at, reverse=True)

            for invoice in invoices[:limit]:
                activities.append(
                    ActivityItem(
                        id=invoice.id,
                        type="invoice",
                        title=f"Invoice {invoice.invoice_number}",
                        description=f"${float(invoice.amount):.2f} - {invoice.status}",
                        timestamp=invoice.created_at.isoformat(),
                        metadata={
                            "invoice_number": invoice.invoice_number,
                            "amount": float(invoice.amount),
                            "status": invoice.status,
                        },
                    )
                )
        except Exception as e:
            logger.warning(f"Error getting invoices for activity feed: {e}")

        # Sort all activities by timestamp and limit
        activities = sorted(activities, key=lambda a: a.timestamp, reverse=True)[:limit]

        return ActivityFeedResponse(
            activities=activities,
            total=len(activities),
            limit=limit,
        )


def get_dashboard_service(session: AsyncSession) -> DashboardService:
    """
    Factory function to create DashboardService instance.

    Args:
        session: Database session

    Returns:
        DashboardService instance
    """
    return DashboardService(session)
