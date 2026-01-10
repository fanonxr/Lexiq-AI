"""Billing and subscription endpoints."""

import json
import logging
from datetime import datetime
from typing import Dict, Optional

import stripe
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status

from api_core.auth.dependencies import get_current_active_user
from api_core.auth.token_validator import TokenValidationResult
from api_core.config import get_settings
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
from api_core.services.stripe_service import get_stripe_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])



# ==================== Debug Endpoint ====================

@router.get("/debug/stripe-config", status_code=status.HTTP_200_OK)
async def debug_stripe_config():
    """
    Debug endpoint to check Stripe configuration status.
    Returns configuration status without exposing sensitive keys.
    """
    settings = get_settings()
    return {
        "stripe_configured": settings.stripe.is_configured,
        "stripe_test_mode": settings.stripe.is_test_mode,
        "stripe_live_mode": settings.stripe.is_live_mode,
        "has_secret_key": bool(settings.stripe.secret_key),
        "has_publishable_key": bool(settings.stripe.publishable_key),
        "has_webhook_secret": bool(settings.stripe.webhook_secret),
        "secret_key_prefix": settings.stripe.secret_key[:10] + "..." if settings.stripe.secret_key else None,
        "publishable_key_prefix": settings.stripe.publishable_key[:10] + "..." if settings.stripe.publishable_key else None,
        "api_version": settings.stripe.api_version,
        "billing_base_url": settings.billing.base_url,
        "billing_currency": settings.billing.currency,
    }


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


# ==================== Checkout Verification ====================


@router.get(
    "/checkout/verify/{session_id}",
    status_code=status.HTTP_200_OK,
)
async def verify_checkout_session(
    session_id: str,
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """
    Verify a Stripe Checkout session and check if subscription was created.

    This endpoint is called by the frontend after successful checkout to verify
    that the subscription was created via webhook. It may take a few seconds for
    the webhook to process, so the frontend should poll this endpoint.

    Args:
        session_id: Stripe Checkout session ID
        current_user: Current authenticated user

    Returns:
        Dictionary with verification status and subscription info
    """
    try:
        async with get_session_context() as session:
            stripe_service = get_stripe_service(session)
            
            # Retrieve the checkout session from Stripe
            checkout_session = await stripe_service.get_checkout_session(session_id)
            
            # Verify the session belongs to the current user
            session_user_id = checkout_session.get("metadata", {}).get("user_id")
            if session_user_id != current_user.user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This checkout session does not belong to you",
                )
            
            # Check if session is completed
            session_status = checkout_session.get("status")
            if session_status != "complete":
                return {
                    "verified": False,
                    "status": session_status,
                    "message": "Checkout session is not yet complete",
                    "subscription_created": False,
                }
            
            # Check if subscription was created in our database
            # The webhook should have created it, but there might be a delay
            billing_service = get_billing_service(session)
            subscription = await billing_service.get_user_subscription(
                current_user.user_id, include_plan=True
            )
            
            if subscription:
                return {
                    "verified": True,
                    "status": "complete",
                    "message": "Subscription created successfully",
                    "subscription_created": True,
                    "subscription": subscription,
                }
            else:
                # Session is complete but subscription not yet created (webhook delay)
                return {
                    "verified": True,
                    "status": "complete",
                    "message": "Payment successful, waiting for subscription activation...",
                    "subscription_created": False,
                }
                
    except HTTPException:
        raise
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
        logger.error(f"Error verifying checkout session {session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify checkout session",
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
    has no active subscription. Automatically syncs from Stripe if data is missing.
    """
    try:
        async with get_session_context() as session:
            billing_service = get_billing_service(session)
            subscription = await billing_service.get_user_subscription(
                current_user.user_id, include_plan=True, auto_sync=True
            )
            return subscription
    except Exception as e:
        logger.error(f"Error getting subscription for user {current_user.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subscription",
        ) from e


@router.post(
    "/subscription/{subscription_id}/sync",
    response_model=SubscriptionResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
)
async def sync_subscription(
    subscription_id: str,
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """
    Manually sync subscription data from Stripe.

    This endpoint fetches the latest subscription data from Stripe and updates
    the local subscription record. Useful for fixing missing or outdated data.

    Args:
        subscription_id: Local subscription ID
        current_user: Current authenticated user

    Returns:
        Updated SubscriptionResponse
    """
    try:
        async with get_session_context() as session:
            billing_service = get_billing_service(session)

            # Verify subscription belongs to user
            subscription = await billing_service.get_user_subscription(
                current_user.user_id, include_plan=False, auto_sync=False
            )
            if not subscription or subscription.id != subscription_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Subscription not found",
                )

            # Sync from Stripe
            synced = await billing_service.sync_subscription_from_stripe(subscription_id)
            if not synced:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Subscription not found",
                )

            logger.info(
                f"Manually synced subscription {subscription_id} from Stripe for user {current_user.user_id}"
            )
            return synced
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
        logger.error(f"Error syncing subscription {subscription_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync subscription",
        ) from e


@router.post(
    "/checkout",
    status_code=status.HTTP_200_OK,
)
async def create_checkout_session(
    plan_id: str = Body(..., embed=True),
    success_url: Optional[str] = Body(None, embed=True),
    cancel_url: Optional[str] = Body(None, embed=True),
    trial_days: Optional[int] = Body(None, embed=True),
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """
    Create a Stripe Checkout session for subscription.

    Creates a Stripe Checkout session that redirects the user to Stripe's
    hosted checkout page. After successful payment, Stripe will send a webhook
    event to create the subscription in our system.

    Args:
        plan_id: Plan ID to subscribe to
        success_url: URL to redirect after successful payment (defaults to billing success page)
        cancel_url: URL to redirect after cancellation (defaults to billing cancel page)
        trial_days: Optional number of trial days (defaults to BILLING_TRIAL_DAYS from config)
        current_user: Current authenticated user

    Returns:
        Dictionary with checkout session_id and url
    """
    """
    Create a Stripe Checkout session for subscription.

    Creates a Stripe Checkout session that redirects the user to Stripe's
    hosted checkout page. After successful payment, Stripe will send a webhook
    event to create the subscription in our system.

    Args:
        plan_id: Plan ID to subscribe to
        success_url: URL to redirect after successful payment (defaults to billing success page)
        cancel_url: URL to redirect after cancellation (defaults to billing cancel page)
        trial_days: Optional number of trial days
        current_user: Current authenticated user

    Returns:
        Dictionary with checkout session_id and url
    """
    try:
        settings = get_settings()
        if not settings.stripe.is_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Stripe is not configured",
            )

        # Set default URLs if not provided
        if not success_url:
            success_url = f"{settings.billing.base_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
        if not cancel_url:
            cancel_url = f"{settings.billing.base_url}/billing/cancel"

        async with get_session_context() as session:
            # Get user and plan
            from api_core.repositories.user_repository import UserRepository

            user_repo = UserRepository(session)
            user = await user_repo.get_by_id(current_user.user_id)
            if not user:
                raise NotFoundError(f"User with ID {current_user.user_id} not found")

            billing_service = get_billing_service(session)
            plan = await billing_service.get_plan_by_id(plan_id)

            # Get plan model for StripeService
            from api_core.repositories.billing_repository import BillingRepository

            billing_repo = BillingRepository(session)
            plan_model = await billing_repo.plans.get_by_id(plan_id)
            if not plan_model:
                raise NotFoundError(f"Plan with ID {plan_id} not found")

            # Use default trial days from config if not provided
            if trial_days is None:
                trial_days = settings.billing.trial_days

            # Create checkout session
            stripe_service = get_stripe_service(session)
            checkout_data = await stripe_service.create_checkout_session(
                user=user,
                plan=plan_model,
                success_url=success_url,
                cancel_url=cancel_url,
                trial_days=trial_days,
            )

            logger.info(
                f"Created checkout session {checkout_data['session_id']} "
                f"for user {current_user.user_id}, plan {plan_id}"
            )
            return checkout_data

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
        error_detail = str(e)
        logger.error(
            f"Error creating checkout session for user {current_user.user_id}: {error_detail}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create checkout session: {error_detail}",
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

    **Note:** For most use cases, use `/billing/checkout` instead, which
    creates a Stripe Checkout session for a better user experience.

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


@router.post("/webhook/stripe", status_code=status.HTTP_200_OK)
async def handle_stripe_webhook(
    request: Request,
):
    """
    Handle Stripe webhook events.

    Processes subscription and invoice events from Stripe.
    This endpoint verifies the webhook signature and routes events
    to the appropriate handlers in BillingService.

    **Security:**
    - Verifies Stripe webhook signature using webhook secret
    - Returns 200 OK even on errors to prevent Stripe retries for bad requests
    - Logs all errors for monitoring

    **Supported Events:**
    - checkout.session.completed: Subscription created via checkout
    - customer.subscription.created: Subscription created
    - customer.subscription.updated: Subscription updated (plan change, renewal, etc.)
    - customer.subscription.deleted: Subscription canceled
    - invoice.paid: Invoice paid successfully
    - invoice.payment_failed: Payment failed

    **Note:** This endpoint should be configured in Stripe Dashboard with:
    - Webhook URL: https://api.lexiqai.com/api/v1/billing/webhook/stripe
    - Events to listen for: All subscription and invoice events
    """
    payload = await request.body()
    signature = request.headers.get("stripe-signature")

    if not signature:
        logger.warning("Stripe webhook received without signature header")
        # Return 200 to prevent Stripe from retrying
        return {"status": "error", "message": "Missing signature"}

    try:
        # Get webhook secret from settings
        settings = get_settings()
        if not settings.stripe.webhook_secret:
            logger.error("Stripe webhook secret not configured")
            return {"status": "error", "message": "Webhook secret not configured"}

        # Verify signature and construct event
        # This both verifies the signature and parses the event
        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                settings.stripe.webhook_secret,
            )
        except ValueError as e:
            logger.error(f"Invalid payload in Stripe webhook: {e}")
            return {"status": "error", "message": "Invalid payload"}
        except stripe.error.SignatureVerificationError as e:
            logger.warning(f"Invalid Stripe webhook signature: {e}")
            return {"status": "error", "message": "Invalid signature"}

        async with get_session_context() as session:
            billing_service = get_billing_service(session)

            # Handle event based on type
            event_type = event.get("type")
            event_data = event.get("data", {}).get("object", {})

            logger.info(f"Processing Stripe webhook event: {event_type}")

            if event_type == "checkout.session.completed":
                # Subscription created via checkout
                await billing_service.handle_checkout_completed(event_data)

            elif event_type == "customer.subscription.created":
                # Subscription created
                await billing_service.handle_subscription_created(event_data)

            elif event_type == "customer.subscription.updated":
                # Subscription updated (plan change, renewal, etc.)
                await billing_service.handle_subscription_updated(event_data)

            elif event_type == "customer.subscription.deleted":
                # Subscription canceled
                await billing_service.handle_subscription_deleted(event_data)

            elif event_type == "invoice.paid":
                # Invoice paid successfully
                await billing_service.handle_invoice_paid(event_data)

            elif event_type == "invoice.payment_failed":
                # Payment failed
                await billing_service.handle_invoice_payment_failed(event_data)

            else:
                logger.debug(f"Unhandled Stripe webhook event type: {event_type}")

            logger.info(f"Successfully processed Stripe webhook event: {event_type}")
            return {"status": "success"}

    except Exception as e:
        logger.error(f"Error processing Stripe webhook: {e}", exc_info=True)
        # Return 200 to prevent Stripe retries for bad requests
        # Stripe will retry on 4xx/5xx, but we want to handle errors gracefully
        return {"status": "error", "message": str(e)}


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def handle_payment_webhook(
    provider: str = Body(..., embed=True),
    event_type: str = Body(..., embed=True, alias="eventType"),
    event_data: Dict = Body(..., embed=True, alias="eventData"),
):
    """
    Handle webhook events from payment providers (generic endpoint).

    Processes webhook events from payment providers (e.g., Azure Billing)
    to update subscription and invoice status.

    **Note:** For Stripe webhooks, use `/billing/webhook/stripe` instead,
    which includes proper signature verification.

    **Note:** In production, this endpoint should:
    - Verify webhook signatures
    - Validate event authenticity
    - Handle rate limiting
    - Implement idempotency

    Args:
        provider: Payment provider name (e.g., "azure_billing")
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
