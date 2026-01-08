"""Call endpoints for managing phone calls."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api_core.auth.dependencies import get_current_active_user, get_user_or_internal_auth
from api_core.auth.internal_service import InternalAuthDep
from api_core.auth.token_validator import TokenValidationResult
from api_core.database.session import get_session_context
from api_core.exceptions import AuthorizationError, NotFoundError, ValidationError
from api_core.models.calls import (
    CallCreateRequest,
    CallListResponse,
    CallResponse,
    CallUpdateRequest,
)
from pydantic import BaseModel, Field
from api_core.services.calls_service import get_calls_service
from api_core.services.storage_service import get_storage_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calls", tags=["calls"])


@router.get(
    "",
    response_model=CallListResponse,
    status_code=status.HTTP_200_OK,
    summary="List calls",
    description="List calls for the authenticated user, optionally filtered by status.",
)
async def list_calls(
    status: Optional[str] = Query(None, description="Filter by call status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    current_user: TokenValidationResult = Depends(get_current_active_user),
) -> CallListResponse:
    """List calls for the authenticated user."""
    try:
        async with get_session_context() as session:
            service = get_calls_service(session)
            return await service.list_calls(
                user_id=current_user.user_id, status=status, skip=skip, limit=limit
            )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error listing calls: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving calls",
        ) from e


@router.get(
    "/{call_id}",
    response_model=CallResponse,
    status_code=status.HTTP_200_OK,
    summary="Get call",
    description="Get a call by ID. Users can only access their own calls.",
)
async def get_call(
    call_id: str,
    current_user: Optional[TokenValidationResult] = Depends(get_user_or_internal_auth),
) -> CallResponse:
    """
    Get call by ID.
    
    Returns the call details including transcript and recording URL.
    
    **Authentication**: Dual auth (user token OR internal API key)
    - **User authentication**: Users can only access their own calls
    - **Internal API key**: Service-to-service calls can access any call (via X-Internal-API-Key header)
    """
    try:
        async with get_session_context() as session:
            service = get_calls_service(session)
            user_id = current_user.user_id if current_user else None
            return await service.get_call(call_id, user_id)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        ) from e
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error getting call: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving call",
        ) from e


@router.post(
    "",
    response_model=CallResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create call (Internal)",
    description=(
        "Create a new call record. "
        "Intended for internal service calls (e.g., Voice Gateway)."
    ),
    dependencies=[InternalAuthDep],
    include_in_schema=False,
)
async def create_call(request: CallCreateRequest) -> CallResponse:
    """
    Create a new call record.
    
    **Authentication**: Internal API key only (via InternalAuthDep)
    **Used by**: Voice Gateway service
    **Note**: This endpoint is not accessible to users. It requires the X-Internal-API-Key header.
    """
    try:
        async with get_session_context() as session:
            service = get_calls_service(session)
            return await service.create_call(request)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error creating call: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating call",
        ) from e


@router.put(
    "/{call_id}",
    response_model=CallResponse,
    status_code=status.HTTP_200_OK,
    summary="Update call",
    description="Update a call record. Users can only update their own calls.",
)
async def update_call(
    call_id: str,
    request: CallUpdateRequest,
    current_user: Optional[TokenValidationResult] = Depends(get_user_or_internal_auth),
) -> CallResponse:
    """
    Update call by ID.
    
    Updates call status, transcript, recording URL, etc.
    
    **Authentication**: Dual auth (user token OR internal API key)
    - **User authentication**: Users can only update their own calls
    - **Internal API key**: Service-to-service calls can update any call (via X-Internal-API-Key header)
    """
    try:
        async with get_session_context() as session:
            service = get_calls_service(session)
            user_id = current_user.user_id if current_user else None
            return await service.update_call(call_id, request, user_id)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        ) from e
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error updating call: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating call",
        ) from e


class AudioUrlResponse(BaseModel):
    """Response model for audio URL."""

    audioUrl: str = Field(alias="audio_url")
    expiresAt: Optional[str] = Field(None, alias="expires_at")  # ISO datetime string


@router.get(
    "/{call_id}/audio",
    response_model=AudioUrlResponse,
    status_code=status.HTTP_200_OK,
    summary="Get call audio URL",
    description="Get a signed URL for the call recording audio file.",
)
async def get_call_audio(
    call_id: str,
    current_user: TokenValidationResult = Depends(get_current_active_user),
) -> AudioUrlResponse:
    """
    Get signed URL for call audio recording.
    
    Returns a time-limited signed URL that can be used to access the call recording
    from Azure Blob Storage. The URL expires after 60 minutes by default.
    
    Args:
        call_id: Call ID
        current_user: Current authenticated user
    
    Returns:
        AudioUrlResponse with signed URL and expiration time
    """
    try:
        async with get_session_context() as session:
            # Get call to verify access and get recording URL
            service = get_calls_service(session)
            call = await service.get_call(call_id, current_user.user_id)

            if not call.recording_url:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No recording available for this call",
                )

            # Parse recording URL to extract container and blob name
            # Recording URL format: https://{account}.blob.core.windows.net/{container}/{blob}
            # Or: {container}/{blob} (relative path)
            recording_url = call.recording_url

            # If it's already a full URL with SAS token, return it
            if "?" in recording_url and ("sig=" in recording_url or "sv=" in recording_url):
                # Already has SAS token, return as-is
                from datetime import datetime, timedelta
                expires_at = (datetime.utcnow() + timedelta(hours=1)).isoformat()
                return AudioUrlResponse(audio_url=recording_url, expires_at=expires_at)

            # Parse blob storage path
            # Try to extract container and blob from URL
            if recording_url.startswith("http"):
                # Full URL: https://{account}.blob.core.windows.net/{container}/{blob}
                from urllib.parse import urlparse
                parsed = urlparse(recording_url)
                path_parts = parsed.path.lstrip("/").split("/", 1)
                if len(path_parts) == 2:
                    container_name = path_parts[0]
                    blob_name = path_parts[1]
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid recording URL format",
                    )
            else:
                # Relative path: {container}/{blob}
                path_parts = recording_url.split("/", 1)
                if len(path_parts) == 2:
                    container_name = path_parts[0]
                    blob_name = path_parts[1]
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid recording URL format",
                    )

            # Generate signed URL
            storage_service = get_storage_service()
            signed_url = await storage_service.generate_signed_url(
                container_name=container_name,
                blob_name=blob_name,
                expiry_minutes=60,
            )

            # Calculate expiration time
            from datetime import datetime, timedelta
            expires_at = (datetime.utcnow() + timedelta(minutes=60)).isoformat()

            return AudioUrlResponse(audio_url=signed_url, expires_at=expires_at)

    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        ) from e
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error getting call audio URL: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving audio URL",
        ) from e

