"""Billing request/response models."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class PlanResponse(BaseModel):
    """Subscription plan response model."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    displayName: str = Field(alias="display_name")
    description: Optional[str] = None
    priceMonthly: Optional[Decimal] = Field(None, alias="price_monthly")
    priceYearly: Optional[Decimal] = Field(None, alias="price_yearly")
    currency: str = "USD"
    features: Optional[Dict[str, Any]] = None
    maxCallsPerMonth: Optional[int] = Field(None, alias="max_calls_per_month")
    maxUsers: Optional[int] = Field(None, alias="max_users")
    maxStorageGb: Optional[int] = Field(None, alias="max_storage_gb")
    # Usage-based billing fields (preferred over features_json)
    includedMinutes: Optional[int] = Field(None, alias="included_minutes")
    overageRatePerMinute: Optional[Decimal] = Field(None, alias="overage_rate_per_minute")
    isActive: bool = Field(alias="is_active")
    isPublic: bool = Field(alias="is_public")
    createdAt: str = Field(alias="created_at")
    updatedAt: str = Field(alias="updated_at")


class SubscriptionRequest(BaseModel):
    """Subscription creation/update request model."""

    model_config = ConfigDict(populate_by_name=True)

    planId: str = Field(alias="plan_id")
    billingCycle: str = Field("monthly", alias="billing_cycle")  # monthly or yearly
    paymentMethodId: Optional[str] = Field(None, alias="payment_method_id")
    trialDays: Optional[int] = Field(None, alias="trial_days")


class SubscriptionResponse(BaseModel):
    """Subscription response model."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    userId: str = Field(alias="user_id")
    planId: str = Field(alias="plan_id")
    plan: Optional[PlanResponse] = None
    status: str
    billingCycle: str = Field(alias="billing_cycle")
    currentPeriodStart: str = Field(alias="current_period_start")
    currentPeriodEnd: str = Field(alias="current_period_end")
    paymentProvider: Optional[str] = Field(None, alias="payment_provider")
    paymentMethodId: Optional[str] = Field(None, alias="payment_method_id")
    canceledAt: Optional[str] = Field(None, alias="canceled_at")
    cancelAtPeriodEnd: bool = Field(alias="cancel_at_period_end")
    trialStart: Optional[str] = Field(None, alias="trial_start")
    trialEnd: Optional[str] = Field(None, alias="trial_end")
    createdAt: str = Field(alias="created_at")
    updatedAt: str = Field(alias="updated_at")


class InvoiceItem(BaseModel):
    """Invoice item model."""

    description: str
    quantity: int = 1
    unitPrice: Decimal = Field(alias="unit_price")
    total: Decimal


class InvoiceResponse(BaseModel):
    """Invoice response model."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    userId: str = Field(alias="user_id")
    subscriptionId: Optional[str] = Field(None, alias="subscription_id")
    invoiceNumber: str = Field(alias="invoice_number")
    amount: Decimal
    currency: str = "USD"
    taxAmount: Optional[Decimal] = Field(None, alias="tax_amount")
    status: str
    paidAt: Optional[str] = Field(None, alias="paid_at")
    dueDate: str = Field(alias="due_date")
    paymentProvider: Optional[str] = Field(None, alias="payment_provider")
    items: Optional[List[InvoiceItem]] = None
    createdAt: str = Field(alias="created_at")
    updatedAt: str = Field(alias="updated_at")


class InvoiceListResponse(BaseModel):
    """Invoice list response model."""

    invoices: List[InvoiceResponse]
    total: int
    skip: int = 0
    limit: int = 100


class UsageRecordResponse(BaseModel):
    """Usage record response model."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    userId: str = Field(alias="user_id")
    feature: str
    quantity: int
    unit: str
    periodStart: str = Field(alias="period_start")
    periodEnd: str = Field(alias="period_end")
    createdAt: str = Field(alias="created_at")


class UsageSummaryResponse(BaseModel):
    """Usage summary response model."""

    userId: str = Field(alias="user_id")
    periodStart: str = Field(alias="period_start")
    periodEnd: str = Field(alias="period_end")
    features: Dict[str, int]  # feature -> total quantity
    totalUsage: Dict[str, int] = Field(alias="total_usage")  # feature -> total across all periods


class UsageLimitCheckResponse(BaseModel):
    """Usage limit check response model."""

    feature: str
    currentUsage: int = Field(alias="current_usage")
    limit: Optional[int] = None
    remaining: Optional[int] = None
    withinLimit: bool = Field(alias="within_limit")
