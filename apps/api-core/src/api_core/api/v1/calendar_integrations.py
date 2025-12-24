"""Calendar integration endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, ConfigDict

from api_core.auth.dependencies import get_current_active_user
from api_core.auth.token_validator import TokenValidationResult
from api_core.database.session import get_session_context
from api_core.exceptions import AuthorizationError, NotFoundError, ValidationError
from api_core.services.calendar_integration_service import CalendarIntegrationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calendar-integrations", tags=["calendar-integrations"])


class InitiateOAuthRequest(BaseModel):
    """Request to initiate OAuth flow."""

    redirect_uri: str = Field(..., description="OAuth redirect URI")


class InitiateOAuthResponse(BaseModel):
    """Response with OAuth authorization URL."""

    model_config = ConfigDict(populate_by_name=True)
    
    authUrl: str = Field(..., description="OAuth authorization URL")


class OAuthCallbackRequest(BaseModel):
    """OAuth callback request."""

    code: str = Field(..., description="Authorization code")
    state: str = Field(..., description="State parameter (user_id)")
    redirect_uri: str = Field(..., description="OAuth redirect URI")


class OAuthCallbackResponse(BaseModel):
    """OAuth callback response."""

    success: bool = Field(..., description="Whether the OAuth callback was successful")
    integration_id: str = Field(..., description="ID of the created/updated integration")


class SyncCalendarResponse(BaseModel):
    """Response for calendar sync operation."""

    success: bool = Field(..., description="Whether the sync was successful")
    appointments_synced: int = Field(..., description="Number of appointments synced")


@router.post(
    "/outlook/initiate",
    response_model=InitiateOAuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Initiate Outlook OAuth flow",
    description="Generate OAuth authorization URL for Outlook calendar integration",
)
async def initiate_outlook_oauth(
    request: InitiateOAuthRequest,
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """Initiate Outlook OAuth flow.
    
    Requires authentication - user must be logged in to connect their calendar.
    """
    try:
        if not current_user or not current_user.user_id:
            logger.error("Invalid user context in initiate_outlook_oauth")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required. Please log in to connect your calendar.",
            )
        
        logger.info(f"Initiating Outlook OAuth for user {current_user.user_id}, redirect_uri={request.redirect_uri}")
        async with get_session_context() as session:
            service = CalendarIntegrationService(session)
            auth_url = await service.initiate_outlook_oauth(
                user_id=current_user.user_id,
                redirect_uri=request.redirect_uri,
            )
            
            if not auth_url:
                logger.error("Auth URL is None or empty")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to generate authorization URL",
                )
            
            logger.info(f"Returning authUrl: {auth_url[:100]}...")
            return InitiateOAuthResponse(authUrl=auth_url)
    except ValidationError as e:
        logger.error(f"Validation error initiating Outlook OAuth: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error initiating Outlook OAuth: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate Outlook OAuth flow",
        ) from e


@router.post(
    "/outlook/callback",
    response_model=OAuthCallbackResponse,
    status_code=status.HTTP_200_OK,
    summary="Handle Outlook OAuth callback",
    description="Exchange authorization code for tokens and store calendar integration",
)
async def handle_outlook_oauth_callback(
    request: OAuthCallbackRequest,
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """Handle Outlook OAuth callback."""
    try:
        # Verify that the state (user_id) matches the current user
        if request.state != current_user.user_id:
            raise AuthorizationError("State parameter does not match current user")

        async with get_session_context() as session:
            service = CalendarIntegrationService(session)
            integration = await service.handle_outlook_oauth_callback(
                user_id=request.state,  # user_id passed in state
                authorization_code=request.code,
                redirect_uri=request.redirect_uri,
            )
            return OAuthCallbackResponse(success=True, integration_id=integration.id)
    except ValidationError as e:
        logger.error(f"Validation error in Outlook OAuth callback: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except AuthorizationError as e:
        logger.error(f"Authorization error in Outlook OAuth callback: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error handling Outlook OAuth callback: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to handle Outlook OAuth callback",
        ) from e


@router.post(
    "/outlook/sync",
    response_model=SyncCalendarResponse,
    status_code=status.HTTP_200_OK,
    summary="Sync Outlook calendar",
    description="Sync appointments from Outlook calendar to LexiqAI",
)
async def sync_outlook_calendar(
    start_date: Optional[str] = Query(
        None,
        description="Start date for sync range (ISO8601 format). If not provided, syncs from 30 days ago.",
    ),
    end_date: Optional[str] = Query(
        None,
        description="End date for sync range (ISO8601 format). If not provided, syncs to 90 days ahead.",
    ),
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """Sync Outlook calendar."""
    try:
        async with get_session_context() as session:
            service = CalendarIntegrationService(session)
            integration = await service.repository.get_by_user_and_type(
                current_user.user_id,
                "outlook",
            )
            if not integration:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Outlook integration not found. Please connect your Outlook calendar first.",
                )

            # Parse date parameters if provided
            from datetime import datetime

            start_dt = None
            end_dt = None
            if start_date:
                start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            if end_date:
                end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))

            # Default to 30 days ago to 90 days ahead if not specified
            if not start_dt:
                from datetime import timedelta

                start_dt = datetime.utcnow() - timedelta(days=30)
            if not end_dt:
                from datetime import timedelta

                end_dt = datetime.utcnow() + timedelta(days=90)

            count = await service.sync_outlook_calendar(integration, start_dt, end_dt)
            return SyncCalendarResponse(success=True, appointments_synced=count)
    except ValidationError as e:
        logger.error(f"Validation error syncing Outlook calendar: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except NotFoundError as e:
        logger.error(f"Not found error syncing Outlook calendar: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error syncing Outlook calendar: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync Outlook calendar",
        ) from e


@router.delete(
    "/outlook/disconnect",
    status_code=status.HTTP_200_OK,
    summary="Disconnect Outlook calendar",
    description="Disconnect and deactivate Outlook calendar integration",
)
async def disconnect_outlook_calendar(
    current_user: TokenValidationResult = Depends(get_current_active_user),
):
    """Disconnect Outlook calendar integration."""
    try:
        async with get_session_context() as session:
            service = CalendarIntegrationService(session)
            integration = await service.repository.get_by_user_and_type(
                current_user.user_id,
                "outlook",
            )
            if not integration:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Outlook integration not found.",
                )

            await service.disconnect_integration(integration.id, current_user.user_id)
            return {"success": True, "message": "Outlook calendar disconnected successfully"}
    except NotFoundError as e:
        logger.error(f"Not found error disconnecting Outlook calendar: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except AuthorizationError as e:
        logger.error(f"Authorization error disconnecting Outlook calendar: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error disconnecting Outlook calendar: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disconnect Outlook calendar",
        ) from e

