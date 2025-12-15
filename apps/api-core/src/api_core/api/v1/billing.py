"""Billing and subscription endpoints."""

import logging
from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status

from api_core.auth.dependencies import get_current_active_user
from api_core.auth.token_validator import TokenValidationResult
from api_core.database.session import get_session_context
from api_core.exceptions import ConflictError, NotFoundError, ValidationError
from api_core.models.billing import (
    InvoiceListResponse,
    InvoiceResponse,
    PlanResponse,
    SubscriptionRequest,
    SubscriptionResponse,
    UsageLimitCheckResponse,
    UsageSummaryResponse,
)
from api_core.services.billing_service import get_billing_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])


# ==================== Plans ====================


@router.get("/plans", response_model=list[PlanResponse], status_code=status.HTTP_200_OK)
async def get_plans():
    """
    Get all active public subscription plans.

    Returns a list of all active plans that are visible to users.
    """
    try:
        async with get_session_context() as session:
            billing_service = get_billing_service(session)
            plans = await billing_service.get_active_plans()
            return plans
    except Exception as e:
        logger.error(f"Error getting plans: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve plans",
        ) from e


@router.get("/plans/{plan_id}", response_model=PlanResponse, status_code=status.HTTP_200_OK)
async def get_plan(plan_id: str):
    """
    Get a specific subscription plan by ID.

    Args:
        plan_id: Plan ID
    """
    try:
        async with get_session_context() as session:
            billing_service = get_billing_service(session)
            plan = await billing_service.get_plan_by_id(plan_id)
            return plan
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error getting plan {plan_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve plan",
        ) from e


# ==================== Subscriptions ====================


@router.get(
    "/subscription",
    response_model=Optional[SubscriptionResponse],
    status_code=status.HTTP_200_OK,
)
async def get_current_subscription(
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """
    Get current active subscription for the authenticated user.

    Returns the active subscription if one exists, or None if the user
    has no active subscription.
    """
    try:
        async with get_session_context() as session:
            billing_service = get_billing_service(session)
            subscription = await billing_service.get_user_subscription(
                current_user.user_id, include_plan=True
            )
            return subscription
    except Exception as e:
        logger.error(f"Error getting subscription for user {current_user.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subscription",
        ) from e


@router.post(
    "/subscription",
    response_model=SubscriptionResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
)
async def create_subscription(
    request: SubscriptionRequest,
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """
    Create a new subscription for the authenticated user.

    Creates a subscription with the specified plan and billing cycle.
    Optionally includes a trial period.

    Args:
        request: Subscription creation request
        current_user: Current authenticated user
    """
    try:
        async with get_session_context() as session:
            billing_service = get_billing_service(session)
            subscription = await billing_service.create_subscription(
                user_id=current_user.user_id,
                plan_id=request.planId,
                billing_cycle=request.billingCycle,
                payment_method_id=request.paymentMethodId,
                trial_days=request.trialDays,
            )
            logger.info(f"Created subscription {subscription.id} for user {current_user.user_id}")
            return subscription
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error creating subscription for user {current_user.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create subscription",
        ) from e


@router.put(
    "/subscription/{subscription_id}",
    response_model=SubscriptionResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
)
async def update_subscription(
    subscription_id: str,
    updates: Dict = Body(...),
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """
    Update a subscription.

    Updates subscription fields such as status, billing cycle, or payment method.
    Only the subscription owner can update their subscription.

    Args:
        subscription_id: Subscription ID
        updates: Dictionary of fields to update
        current_user: Current authenticated user
    """
    try:
        async with get_session_context() as session:
            billing_service = get_billing_service(session)
            # Verify subscription belongs to user
            subscription = await billing_service.get_user_subscription(
                current_user.user_id, include_plan=False
            )
            if not subscription or subscription.id != subscription_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Subscription not found",
                )

            updated = await billing_service.update_subscription(subscription_id, updates)
            logger.info(f"Updated subscription {subscription_id} for user {current_user.user_id}")
            return updated
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error updating subscription {subscription_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update subscription",
        ) from e


@router.delete(
    "/subscription/{subscription_id}",
    response_model=SubscriptionResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
)
async def cancel_subscription(
    subscription_id: str,
    cancel_at_period_end: bool = Query(True, description="Cancel at period end or immediately"),
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """
    Cancel a subscription.

    Cancels the subscription either immediately or at the end of the current
    billing period. Only the subscription owner can cancel their subscription.

    Args:
        subscription_id: Subscription ID
        cancel_at_period_end: Whether to cancel at period end (default: True)
        current_user: Current authenticated user
    """
    try:
        async with get_session_context() as session:
            billing_service = get_billing_service(session)
            # Verify subscription belongs to user
            subscription = await billing_service.get_user_subscription(
                current_user.user_id, include_plan=False
            )
            if not subscription or subscription.id != subscription_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Subscription not found",
                )

            canceled = await billing_service.cancel_subscription(
                subscription_id, cancel_at_period_end=cancel_at_period_end
            )
            logger.info(
                f"Canceled subscription {subscription_id} for user {current_user.user_id} "
                f"(at_period_end={cancel_at_period_end})"
            )
            return canceled
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error canceling subscription {subscription_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel subscription",
        ) from e


@router.post(
    "/subscription/{subscription_id}/upgrade",
    response_model=SubscriptionResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
)
async def upgrade_subscription(
    subscription_id: str,
    new_plan_id: str = Body(..., embed=True),
    prorate: bool = Body(True, embed=True),
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """
    Upgrade subscription to a new plan.

    Upgrades the subscription to a new plan with optional proration.
    Only the subscription owner can upgrade their subscription.

    Args:
        subscription_id: Subscription ID
        new_plan_id: New plan ID
        prorate: Whether to prorate the billing (default: True)
        current_user: Current authenticated user
    """
    try:
        async with get_session_context() as session:
            billing_service = get_billing_service(session)
            # Verify subscription belongs to user
            subscription = await billing_service.get_user_subscription(
                current_user.user_id, include_plan=False
            )
            if not subscription or subscription.id != subscription_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Subscription not found",
                )

            upgraded = await billing_service.upgrade_subscription(
                subscription_id, new_plan_id=new_plan_id, prorate=prorate
            )
            logger.info(
                f"Upgraded subscription {subscription_id} to plan {new_plan_id} "
                f"for user {current_user.user_id}"
            )
            return upgraded
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error upgrading subscription {subscription_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upgrade subscription",
        ) from e


# ==================== Invoices ====================


@router.get(
    "/invoices",
    response_model=InvoiceListResponse,
    status_code=status.HTTP_200_OK,
)
async def get_invoices(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """
    Get invoices for the authenticated user.

    Returns a paginated list of invoices for the current user.

    Args:
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        current_user: Current authenticated user
    """
    try:
        async with get_session_context() as session:
            billing_service = get_billing_service(session)
            invoices = await billing_service.get_user_invoices(
                current_user.user_id, skip=skip, limit=limit
            )
            return InvoiceListResponse(
                invoices=invoices,
                total=len(invoices),  # In production, get actual total count
                skip=skip,
                limit=limit,
            )
    except Exception as e:
        logger.error(f"Error getting invoices for user {current_user.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve invoices",
        ) from e


@router.get(
    "/invoices/{invoice_id}",
    response_model=InvoiceResponse,
    status_code=status.HTTP_200_OK,
)
async def get_invoice(
    invoice_id: str,
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """
    Get a specific invoice by ID.

    Returns invoice details if it belongs to the authenticated user.

    Args:
        invoice_id: Invoice ID
        current_user: Current authenticated user
    """
    try:
        async with get_session_context() as session:
            billing_service = get_billing_service(session)
            invoice = await billing_service.get_invoice_by_id(invoice_id)

            # Verify invoice belongs to user
            if invoice.userId != current_user.user_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Invoice not found",
                )

            return invoice
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error getting invoice {invoice_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve invoice",
        ) from e


# ==================== Usage ====================


@router.get(
    "/usage",
    response_model=UsageSummaryResponse,
    status_code=status.HTTP_200_OK,
)
async def get_usage(
    period_start: Optional[str] = Query(
        None, description="Period start date (ISO format, defaults to current billing period)"
    ),
    period_end: Optional[str] = Query(
        None, description="Period end date (ISO format, defaults to current billing period)"
    ),
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """
    Get usage statistics for the authenticated user.

    Returns usage summary for the specified time period. If no period is specified,
    uses the current billing period from the user's active subscription.

    Args:
        period_start: Period start date (ISO format)
        period_end: Period end date (ISO format)
        current_user: Current authenticated user
    """
    try:
        async with get_session_context() as session:
            billing_service = get_billing_service(session)

            # If no period specified, get from current subscription
            if not period_start or not period_end:
                subscription = await billing_service.get_user_subscription(
                    current_user.user_id, include_plan=False
                )
                if not subscription:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="No active subscription found",
                    )
                period_start_dt = datetime.fromisoformat(subscription.currentPeriodStart.replace("Z", "+00:00"))
                period_end_dt = datetime.fromisoformat(subscription.currentPeriodEnd.replace("Z", "+00:00"))
            else:
                period_start_dt = datetime.fromisoformat(period_start.replace("Z", "+00:00"))
                period_end_dt = datetime.fromisoformat(period_end.replace("Z", "+00:00"))

            summary = await billing_service.get_usage_summary(
                current_user.user_id, period_start_dt, period_end_dt
            )
            return summary
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {e}",
        ) from e
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error getting usage for user {current_user.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve usage statistics",
        ) from e


@router.get(
    "/usage/limits/{feature}",
    response_model=UsageLimitCheckResponse,
    status_code=status.HTTP_200_OK,
)
async def check_usage_limits(
    feature: str,
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """
    Check usage limits for a specific feature.

    Returns current usage, limit, remaining quota, and whether the user
    is within limits for the specified feature.

    Args:
        feature: Feature name (e.g., "calls", "storage", "api_requests")
        current_user: Current authenticated user
    """
    try:
        async with get_session_context() as session:
            billing_service = get_billing_service(session)
            limit_check = await billing_service.check_usage_limits(
                current_user.user_id, feature
            )
            return limit_check
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(
            f"Error checking usage limits for feature {feature} and user {current_user.user_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check usage limits",
        ) from e


@router.post(
    "/usage/track",
    status_code=status.HTTP_201_CREATED,
)
async def track_usage(
    feature: str = Body(..., embed=True),
    quantity: int = Body(1, embed=True, ge=1),
    unit: str = Body("count", embed=True),
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """
    Track feature usage for the authenticated user.

    Records usage for a specific feature. This endpoint is typically called
    by internal services to track usage.

    Args:
        feature: Feature name (e.g., "calls", "storage", "api_requests")
        quantity: Usage quantity (default: 1)
        unit: Unit of measurement (default: "count")
        current_user: Current authenticated user
    """
    try:
        async with get_session_context() as session:
            billing_service = get_billing_service(session)
            usage_record = await billing_service.track_usage(
                user_id=current_user.user_id,
                feature=feature,
                quantity=quantity,
                unit=unit,
            )
            logger.info(
                f"Tracked usage: {feature} ({quantity} {unit}) for user {current_user.user_id}"
            )
            return {"id": usage_record.id, "message": "Usage tracked successfully"}
    except Exception as e:
        logger.error(f"Error tracking usage for user {current_user.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to track usage",
        ) from e


# ==================== Webhooks ====================


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def handle_payment_webhook(
    provider: str = Body(..., embed=True),
    event_type: str = Body(..., embed=True, alias="eventType"),
    event_data: Dict = Body(..., embed=True, alias="eventData"),
):
    """
    Handle webhook events from payment providers.

    Processes webhook events from payment providers (e.g., Stripe, Azure Billing)
    to update subscription and invoice status.

    **Note:** In production, this endpoint should:
    - Verify webhook signatures
    - Validate event authenticity
    - Handle rate limiting
    - Implement idempotency

    Args:
        provider: Payment provider name (e.g., "stripe")
        event_type: Event type (e.g., "subscription.updated", "invoice.paid")
        event_data: Event data from payment provider
    """
    try:
        async with get_session_context() as session:
            billing_service = get_billing_service(session)
            await billing_service.handle_payment_webhook(provider, event_type, event_data)
            logger.info(f"Processed {provider} webhook: {event_type}")
            return {"status": "success", "message": "Webhook processed"}
    except Exception as e:
        logger.error(f"Error processing webhook from {provider}: {e}")
        # Don't expose internal errors to webhook caller
        return {"status": "error", "message": "Webhook processing failed"}
