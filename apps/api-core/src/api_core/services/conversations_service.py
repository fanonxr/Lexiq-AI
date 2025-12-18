"""Conversations service for business logic."""

from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from api_core.exceptions import AuthorizationError, NotFoundError, ValidationError
from api_core.models.conversations import (
    ConversationListResponse,
    ConversationMessageResponse,
    ConversationResponse,
)
from api_core.repositories.conversations_repository import (
    ConversationMessagesRepository,
    ConversationsRepository,
)

logger = logging.getLogger(__name__)


class ConversationsService:
    """Service for conversation operations."""

    def __init__(self, session: AsyncSession):
        self._repo = ConversationsRepository(session)
        self._messages_repo = ConversationMessagesRepository(session)
        self.session = session

    async def get_conversation(
        self, conversation_id: str, user_id: Optional[str] = None
    ) -> ConversationResponse:
        """Get a conversation by ID with messages."""
        if not conversation_id or not conversation_id.strip():
            raise ValidationError("conversation_id is required")

        conversation = await self._repo.get_by_id_with_messages(conversation_id)
        if not conversation:
            raise NotFoundError(resource="Conversation", resource_id=conversation_id)

        # Check authorization if user_id provided
        if user_id and conversation.user_id != user_id:
            raise AuthorizationError(
                f"User {user_id} does not have access to conversation {conversation_id}"
            )

        # Convert messages
        messages = [
            ConversationMessageResponse(
                id=msg.id,
                conversation_id=msg.conversation_id,
                role=msg.role,
                content=msg.content,
                tool_calls=msg.tool_calls,
                tool_call_id=msg.tool_call_id,
                tokens=msg.tokens,
                model=msg.model,
                created_at=msg.created_at,
            )
            for msg in conversation.messages
        ]

        return ConversationResponse(
            id=conversation.id,
            user_id=conversation.user_id,
            firm_id=conversation.firm_id,
            call_id=conversation.call_id,
            status=conversation.status,
            model_used=conversation.model_used,
            total_tokens=conversation.total_tokens,
            started_at=conversation.started_at,
            ended_at=conversation.ended_at,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            messages=messages,
        )

    async def list_conversations(
        self,
        user_id: str,
        firm_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> ConversationListResponse:
        """List conversations for a user."""
        if not user_id or not user_id.strip():
            raise ValidationError("user_id is required")

        conversations = await self._repo.get_by_user_id(user_id, firm_id, skip, limit)
        total = await self._repo.count_by_user_id(user_id, firm_id)

        conversation_responses = [
            ConversationResponse(
                id=conv.id,
                user_id=conv.user_id,
                firm_id=conv.firm_id,
                call_id=conv.call_id,
                status=conv.status,
                model_used=conv.model_used,
                total_tokens=conv.total_tokens,
                started_at=conv.started_at,
                ended_at=conv.ended_at,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                messages=[],  # Don't load messages in list view
            )
            for conv in conversations
        ]

        return ConversationListResponse(conversations=conversation_responses, total=total)


def get_conversations_service(session: AsyncSession) -> ConversationsService:
    """Factory for ConversationsService."""
    return ConversationsService(session=session)

