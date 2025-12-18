"""Conversation endpoints for managing AI conversations."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api_core.auth.dependencies import get_current_active_user, get_user_or_internal_auth
from api_core.auth.token_validator import TokenValidationResult
from api_core.database.session import get_session_context
from api_core.exceptions import AuthorizationError, NotFoundError, ValidationError
from api_core.models.conversations import ConversationListResponse, ConversationResponse
from api_core.services.conversations_service import get_conversations_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get(
    "",
    response_model=ConversationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List conversations",
    description="List conversations for the authenticated user, optionally filtered by firm.",
)
async def list_conversations(
    firm_id: Optional[str] = Query(None, description="Filter by firm ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    current_user: TokenValidationResult = Depends(get_current_active_user),
) -> ConversationListResponse:
    """List conversations for the authenticated user."""
    try:
        async with get_session_context() as session:
            service = get_conversations_service(session)
            return await service.list_conversations(
                user_id=current_user.user_id, firm_id=firm_id, skip=skip, limit=limit
            )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error listing conversations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving conversations",
        ) from e


@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get conversation",
    description="Get a conversation by ID with all messages. Users can only access their own conversations.",
)
async def get_conversation(
    conversation_id: str,
    current_user: Optional[TokenValidationResult] = Depends(get_user_or_internal_auth),
) -> ConversationResponse:
    """
    Get conversation by ID.
    
    Returns the conversation with all messages. Supports both:
    - User authentication: Users can only access their own conversations
    - Internal API key: Service-to-service calls can access any conversation
    """
    try:
        async with get_session_context() as session:
            service = get_conversations_service(session)
            user_id = current_user.user_id if current_user else None
            return await service.get_conversation(conversation_id, user_id)
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
        logger.error(f"Error getting conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving conversation",
        ) from e

