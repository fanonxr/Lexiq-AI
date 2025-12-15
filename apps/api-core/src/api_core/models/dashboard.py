"""Dashboard request/response models."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CallStats(BaseModel):
    """Call statistics model."""

    totalCalls: int = Field(alias="total_calls", default=0)
    answeredCalls: int = Field(alias="answered_calls", default=0)
    missedCalls: int = Field(alias="missed_calls", default=0)
    averageDuration: float = Field(alias="average_duration", default=0.0)  # in seconds
    totalDuration: float = Field(alias="total_duration", default=0.0)  # in seconds


class UsageStats(BaseModel):
    """Usage statistics model."""

    calls: int = 0
    storageGb: float = Field(alias="storage_gb", default=0.0)
    apiRequests: int = Field(alias="api_requests", default=0)
    periodStart: str = Field(alias="period_start")
    periodEnd: str = Field(alias="period_end")


class SubscriptionStats(BaseModel):
    """Subscription statistics model."""

    hasActiveSubscription: bool = Field(alias="has_active_subscription", default=False)
    planName: Optional[str] = Field(None, alias="plan_name")
    billingCycle: Optional[str] = Field(None, alias="billing_cycle")
    currentPeriodStart: Optional[str] = Field(None, alias="current_period_start")
    currentPeriodEnd: Optional[str] = Field(None, alias="current_period_end")
    daysUntilRenewal: Optional[int] = Field(None, alias="days_until_renewal")


class BillingStats(BaseModel):
    """Billing statistics model."""

    totalInvoices: int = Field(alias="total_invoices", default=0)
    paidInvoices: int = Field(alias="paid_invoices", default=0)
    pendingInvoices: int = Field(alias="pending_invoices", default=0)
    totalSpent: float = Field(alias="total_spent", default=0.0)
    currency: str = "USD"


class ActivityItem(BaseModel):
    """Activity feed item model."""

    id: str
    type: str  # "call", "invoice", "subscription", "usage"
    title: str
    description: Optional[str] = None
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None


class DashboardStats(BaseModel):
    """Dashboard statistics response model."""

    model_config = ConfigDict(populate_by_name=True)

    userId: str = Field(alias="user_id")
    callStats: CallStats = Field(alias="call_stats")
    usageStats: UsageStats = Field(alias="usage_stats")
    subscriptionStats: SubscriptionStats = Field(alias="subscription_stats")
    billingStats: BillingStats = Field(alias="billing_stats")
    lastUpdated: str = Field(alias="last_updated")


class CallInfo(BaseModel):
    """Call information model (placeholder for future Call model)."""

    id: str
    userId: str = Field(alias="user_id")
    phoneNumber: Optional[str] = Field(None, alias="phone_number")
    direction: str  # "inbound" or "outbound"
    status: str  # "answered", "missed", "voicemail", etc.
    duration: Optional[float] = None  # in seconds
    startedAt: str = Field(alias="started_at")
    endedAt: Optional[str] = Field(None, alias="ended_at")
    recordingUrl: Optional[str] = Field(None, alias="recording_url")
    transcript: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class CallListResponse(BaseModel):
    """Call list response model."""

    calls: List[CallInfo]
    total: int
    limit: int


class ActivityFeedResponse(BaseModel):
    """Activity feed response model."""

    activities: List[ActivityItem]
    total: int
    limit: int
