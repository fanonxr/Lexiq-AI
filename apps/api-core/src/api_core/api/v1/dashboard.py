"""Dashboard endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api_core.auth.dependencies import get_current_active_user
from api_core.auth.token_validator import TokenValidationResult
from api_core.database.session import get_session_context
from api_core.exceptions import NotFoundError
from api_core.models.billing import UsageSummaryResponse
from api_core.models.dashboard import (
    ActivityFeedResponse,
    CallListResponse,
    DashboardStats,
    VolumeDataResponse,
)
from api_core.services.dashboard_service import get_dashboard_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "/stats",
    response_model=DashboardStats,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
)
async def get_dashboard_stats(
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """
    Get comprehensive dashboard statistics for the authenticated user.

    Returns aggregated statistics including:
    - Call statistics (total, answered, missed, duration)
    - Usage statistics (calls, storage, API requests)
    - Subscription statistics (plan, billing cycle, renewal date)
    - Billing statistics (invoices, total spent)

    Args:
        current_user: Current authenticated user

    Returns:
        DashboardStats with all aggregated statistics
    """
    try:
        async with get_session_context() as session:
            dashboard_service = get_dashboard_service(session)
            stats = await dashboard_service.get_dashboard_stats(current_user.user_id)
            return stats
    except Exception as e:
        logger.error(f"Error getting dashboard stats for user {current_user.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dashboard statistics",
        ) from e


@router.get(
    "/recent-calls",
    response_model=CallListResponse,
    status_code=status.HTTP_200_OK,
)
async def get_recent_calls(
    limit: int = Query(10, ge=1, le=100, description="Maximum number of calls to return"),
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """
    Get recent call recordings for the authenticated user.

    **Note:** This endpoint is currently a placeholder. In production, it will
    integrate with the Voice Gateway or Cognitive Orchestrator service to
    retrieve actual call records.

    Args:
        limit: Maximum number of calls to return (default: 10, max: 100)
        current_user: Current authenticated user

    Returns:
        CallListResponse with recent calls
    """
    try:
        async with get_session_context() as session:
            dashboard_service = get_dashboard_service(session)
            calls = await dashboard_service.get_recent_calls(
                current_user.user_id, limit=limit
            )
            return calls
    except Exception as e:
        logger.error(
            f"Error getting recent calls for user {current_user.user_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve recent calls",
        ) from e


@router.get(
    "/usage",
    response_model=UsageSummaryResponse,
    status_code=status.HTTP_200_OK,
)
async def get_usage_summary(
    period: str = Query(
        "current",
        description="Period identifier: 'current', 'last_month', or 'last_30_days'",
    ),
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """
    Get usage summary for the authenticated user.

    Returns usage statistics for the specified period. If the user has an active
    subscription, "current" uses the current billing period. Otherwise, it uses
    the last 30 days.

    Args:
        period: Period identifier:
            - "current": Current billing period (or last 30 days if no subscription)
            - "last_month": Previous calendar month
            - "last_30_days": Last 30 days from now
        current_user: Current authenticated user

    Returns:
        UsageSummaryResponse with usage statistics
    """
    try:
        async with get_session_context() as session:
            dashboard_service = get_dashboard_service(session)
            usage = await dashboard_service.get_usage_summary(
                current_user.user_id, period=period
            )
            return usage
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid period: {e}",
        ) from e
    except Exception as e:
        logger.error(
            f"Error getting usage summary for user {current_user.user_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve usage summary",
        ) from e


@router.get(
    "/volume",
    response_model=VolumeDataResponse,
    status_code=status.HTTP_200_OK,
)
async def get_volume_data(
    from_date: str = Query(..., alias="from", description="Start date (ISO format: YYYY-MM-DD)"),
    to_date: str = Query(..., alias="to", description="End date (ISO format: YYYY-MM-DD)"),
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """
    Get call volume data for a date range.

    Returns daily call counts for the specified date range, suitable for
    volume charts. Missing dates are filled with 0.

    Args:
        from_date: Start date in ISO format (YYYY-MM-DD)
        to_date: End date in ISO format (YYYY-MM-DD)
        current_user: Current authenticated user

    Returns:
        VolumeDataResponse with daily call counts
    """
    try:
        from datetime import datetime

        # Parse dates
        try:
            date_from = datetime.fromisoformat(from_date.replace("Z", "+00:00"))
            date_to = datetime.fromisoformat(to_date.replace("Z", "+00:00"))
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid date format. Use ISO format (YYYY-MM-DD): {e}",
            ) from e

        # Validate date range
        if date_from > date_to:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="from_date must be before or equal to to_date",
            )

        # Limit date range to prevent excessive queries
        max_days = 365
        if (date_to - date_from).days > max_days:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Date range cannot exceed {max_days} days",
            )

        async with get_session_context() as session:
            dashboard_service = get_dashboard_service(session)
            volume_data = await dashboard_service.get_volume_data(
                current_user.user_id, date_from, date_to
            )
            return volume_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error getting volume data for user {current_user.user_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve volume data",
        ) from e


@router.get(
    "/activity",
    response_model=ActivityFeedResponse,
    status_code=status.HTTP_200_OK,
)
async def get_recent_activity(
    limit: int = Query(
        20, ge=1, le=100, description="Maximum number of activities to return"
    ),
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """
    Get recent activity feed for the authenticated user.

    Returns a chronological feed of recent activities including:
    - Usage events (calls tracked, API requests)
    - Billing events (invoices created, payments)
    - Subscription events (upgrades, cancellations)

    Activities are sorted by timestamp, most recent first.

    Args:
        limit: Maximum number of activities to return (default: 20, max: 100)
        current_user: Current authenticated user

    Returns:
        ActivityFeedResponse with recent activities
    """
    try:
        async with get_session_context() as session:
            dashboard_service = get_dashboard_service(session)
            activity = await dashboard_service.get_recent_activity(
                current_user.user_id, limit=limit
            )
            return activity
    except Exception as e:
        logger.error(
            f"Error getting recent activity for user {current_user.user_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve recent activity",
        ) from e
