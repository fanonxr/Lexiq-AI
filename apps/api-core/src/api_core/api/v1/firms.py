"""Firm endpoints (MVP firm personas)."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from api_core.auth.dependencies import get_user_or_internal_auth
from api_core.auth.token_validator import TokenValidationResult
from api_core.database.session import get_session_context
from api_core.exceptions import (
    AuthorizationError,
    ExternalServiceError,
    NotFoundError,
    ValidationError,
)
from api_core.models.firms import (
    FirmPersonaResponse,
    FirmPersonaUpsertRequest,
    FirmPhoneNumberRequest,
    FirmPhoneNumberResponse,
    FirmSettingsResponse,
)
from api_core.services.firms_service import get_firms_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/firms", tags=["firms"])


@router.get(
    "/{firm_id}/persona",
    response_model=FirmPersonaResponse,
    status_code=status.HTTP_200_OK,
    summary="Get firm persona",
    description="Retrieve firm-specific system prompt/persona. Users can only access personas for firms they have access to.",
)
async def get_firm_persona(
    firm_id: str,
    auth_result: Optional[TokenValidationResult] = Depends(get_user_or_internal_auth),
) -> FirmPersonaResponse:
    """
    Get firm persona.
    
    Returns the system prompt/persona configured for the specified firm.
    Supports both:
    - User authentication: Users must have access to the firm (e.g., have uploaded files or created resources for that firm).
    - Internal API key: Service-to-service calls (e.g., from Cognitive Orchestrator) can access any firm.
    """
    try:
        async with get_session_context() as session:
            service = get_firms_service(session)
            # If None, it's an internal service call - skip authorization
            user_id = auth_result.user_id if auth_result else None
            return await service.get_firm_persona(firm_id, user_id)
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
        logger.error(f"Error getting firm persona: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving firm persona",
        ) from e


@router.put(
    "/{firm_id}/persona",
    response_model=FirmPersonaResponse,
    status_code=status.HTTP_200_OK,
    summary="Update firm persona",
    description="Set or update firm-specific system prompt/persona. Users can only update personas for firms they have access to.",
)
async def upsert_firm_persona(
    firm_id: str,
    request: FirmPersonaUpsertRequest,
    auth_result: Optional[TokenValidationResult] = Depends(get_user_or_internal_auth),
) -> FirmPersonaResponse:
    """
    Update firm persona.
    
    Sets or updates the system prompt/persona for the specified firm.
    Supports both:
    - User authentication: Users must have access to the firm (e.g., have uploaded files or created resources for that firm).
    - Internal API key: Service-to-service calls (e.g., from Cognitive Orchestrator) can update any firm.
    """
    try:
        async with get_session_context() as session:
            service = get_firms_service(session)
            # If None, it's an internal service call - skip authorization
            user_id = auth_result.user_id if auth_result else None
            return await service.upsert_firm_persona(
                firm_id, request.system_prompt, user_id
            )
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
    except Exception as e:
        logger.error(f"Error updating firm persona: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating firm persona",
        ) from e


@router.get(
    "/{firm_id}/settings",
    response_model=FirmSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get firm settings",
    description="Retrieve full firm settings including model, persona, specialties, and Qdrant configuration. Primarily for internal service calls (Cognitive Orchestrator).",
)
async def get_firm_settings(
    firm_id: str,
    auth_result: Optional[TokenValidationResult] = Depends(get_user_or_internal_auth),
) -> FirmSettingsResponse:
    """
    Get firm settings.
    
    Returns the complete firm configuration including:
    - Firm name and domain
    - Default model override
    - System prompt/persona
    - Specialties
    - Qdrant collection name
    
    Supports both:
    - User authentication: Users must have access to the firm
    - Internal API key: Service-to-service calls (e.g., from Cognitive Orchestrator) can access any firm.
    """
    try:
        async with get_session_context() as session:
            service = get_firms_service(session)
            # If None, it's an internal service call - skip authorization
            user_id = auth_result.user_id if auth_result else None
            return await service.get_firm_settings(firm_id, user_id)
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
        logger.error(f"Error getting firm settings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving firm settings",
        ) from e


@router.post(
    "/{firm_id}/phone-number",
    response_model=FirmPhoneNumberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Provision phone number",
    description="Provision a new Twilio phone number for a firm. Users can only provision numbers for firms they have access to.",
)
async def provision_phone_number(
    firm_id: str,
    request: FirmPhoneNumberRequest,
    auth_result: Optional[TokenValidationResult] = Depends(get_user_or_internal_auth),
) -> FirmPhoneNumberResponse:
    """
    Provision a new Twilio phone number for a firm.
    
    This endpoint:
    - Creates or retrieves Twilio subaccount for the firm
    - Searches for available Twilio numbers (optionally by area code)
    - Purchases the number via Twilio API
    - Configures webhook automatically
    - Returns the phone number details
    
    Requires user to have access to the firm.
    """
    try:
        async with get_session_context() as session:
            firms_service = get_firms_service(session)
            # If None, it's an internal service call - skip authorization
            user_id = auth_result.user_id if auth_result else None
            logger.debug(
                f"[provision_phone_number endpoint] Received request: "
                f"firm_id={firm_id} (type: {type(firm_id)}, length: {len(firm_id) if firm_id else 0}), "
                f"user_id={user_id}"
            )
            return await firms_service.provision_phone_number(
                firm_id=firm_id,
                area_code=request.area_code,
                user_id=user_id,
            )
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
    except ExternalServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error provisioning phone number: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while provisioning phone number",
        ) from e


@router.get(
    "/{firm_id}/phone-number",
    response_model=FirmPhoneNumberResponse,
    status_code=status.HTTP_200_OK,
    summary="Get firm phone number",
    description="Get firm's Twilio phone number. Users can only access phone numbers for firms they have access to.",
)
async def get_firm_phone_number(
    firm_id: str,
    auth_result: Optional[TokenValidationResult] = Depends(get_user_or_internal_auth),
) -> FirmPhoneNumberResponse:
    """
    Get firm's Twilio phone number.
    
    Returns the phone number details for the specified firm, including:
    - Phone number in E.164 format
    - Formatted phone number for display
    - Twilio Phone Number SID
    - Twilio Subaccount SID
    - Area code
    
    Requires user to have access to the firm.
    """
    try:
        async with get_session_context() as session:
            firms_service = get_firms_service(session)
            # If None, it's an internal service call - skip authorization
            user_id = auth_result.user_id if auth_result else None
            logger.debug(
                f"[get_firm_phone_number endpoint] Received request: "
                f"firm_id={firm_id} (type: {type(firm_id)}, length: {len(firm_id) if firm_id else 0}), "
                f"user_id={user_id}"
            )
            return await firms_service.get_firm_phone_number(
                firm_id=firm_id,
                user_id=user_id,
            )
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
        logger.error(f"Error getting firm phone number: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving firm phone number",
        ) from e


@router.delete(
    "/{firm_id}/phone-number",
    summary="Release phone number",
    description="Release (delete) a firm's Twilio phone number. This permanently removes the number from Twilio and clears it from the database. Users can only release numbers for firms they have access to.",
)
async def release_firm_phone_number(
    firm_id: str,
    release_from_twilio: bool = Query(
        True,
        description="If True, release the number from Twilio. If False, only clear from database.",
    ),
    auth_result: Optional[TokenValidationResult] = Depends(get_user_or_internal_auth),
) -> Response:
    """
    Release (delete) a firm's Twilio phone number.
    
    This endpoint:
    - Releases the phone number from Twilio (permanently deletes it)
    - Clears the phone number fields from the database
    - Keeps the subaccount SID (in case firm wants to provision a new number later)
    
    Args:
        firm_id: Firm ID
        release_from_twilio: If True (default), release the number from Twilio.
                           If False, only clear from database (useful if number was already released).
    
    Requires user to have access to the firm.
    """
    try:
        async with get_session_context() as session:
            firms_service = get_firms_service(session)
            # If None, it's an internal service call - skip authorization
            user_id = auth_result.user_id if auth_result else None
            
            await firms_service.release_phone_number(
                firm_id=firm_id,
                user_id=user_id,
                release_from_twilio=release_from_twilio,
            )
            
            # Return 204 No Content with no body
            return Response(status_code=status.HTTP_204_NO_CONTENT)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        ) from e
    except ExternalServiceError as e:
        logger.error(f"External service error releasing phone number: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error releasing phone number from Twilio: {str(e)}",
        ) from e
    except Exception as e:
        logger.error(f"Error releasing phone number: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while releasing the phone number",
        ) from e


