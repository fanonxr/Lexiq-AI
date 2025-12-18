"""Firm endpoints (MVP firm personas)."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from api_core.auth.dependencies import get_user_or_internal_auth
from api_core.auth.token_validator import TokenValidationResult
from api_core.database.session import get_session_context
from api_core.exceptions import AuthorizationError, NotFoundError, ValidationError
from api_core.models.firms import FirmPersonaResponse, FirmPersonaUpsertRequest, FirmSettingsResponse
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


