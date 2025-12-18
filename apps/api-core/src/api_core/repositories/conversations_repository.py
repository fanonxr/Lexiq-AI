"""Conversations repository for data access operations."""

from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api_core.database.models import Conversation, ConversationMessage
from api_core.exceptions import DatabaseError
from api_core.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class ConversationsRepository(BaseRepository[Conversation]):
    """Repository for conversation data access operations."""

    def __init__(self, session: AsyncSession):
        """Initialize conversations repository."""
        super().__init__(Conversation, session)

    async def get_by_id_with_messages(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID with messages loaded."""
        try:
            result = await self.session.execute(
                select(Conversation)
                .where(Conversation.id == conversation_id)
                .options(selectinload(Conversation.messages))
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting conversation {conversation_id}: {e}")
            raise DatabaseError("Failed to retrieve conversation") from e

    async def get_by_user_id(
        self, user_id: str, firm_id: Optional[str] = None, skip: int = 0, limit: int = 100
    ) -> List[Conversation]:
        """Get conversations for a user, optionally filtered by firm."""
        try:
            query = select(Conversation).where(Conversation.user_id == user_id)
            if firm_id:
                query = query.where(Conversation.firm_id == firm_id)
            query = query.order_by(Conversation.created_at.desc()).offset(skip).limit(limit)

            result = await self.session.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting conversations for user {user_id}: {e}")
            raise DatabaseError("Failed to retrieve conversations") from e

    async def count_by_user_id(self, user_id: str, firm_id: Optional[str] = None) -> int:
        """Count conversations for a user."""
        try:
            from sqlalchemy import func

            query = select(func.count(Conversation.id)).where(Conversation.user_id == user_id)
            if firm_id:
                query = query.where(Conversation.firm_id == firm_id)

            result = await self.session.execute(query)
            return result.scalar_one() or 0
        except SQLAlchemyError as e:
            logger.error(f"Error counting conversations for user {user_id}: {e}")
            raise DatabaseError("Failed to count conversations") from e


class ConversationMessagesRepository(BaseRepository[ConversationMessage]):
    """Repository for conversation message data access operations."""

    def __init__(self, session: AsyncSession):
        """Initialize conversation messages repository."""
        super().__init__(ConversationMessage, session)

    async def get_by_conversation_id(
        self, conversation_id: str
    ) -> List[ConversationMessage]:
        """Get all messages for a conversation."""
        try:
            result = await self.session.execute(
                select(ConversationMessage)
                .where(ConversationMessage.conversation_id == conversation_id)
                .order_by(ConversationMessage.created_at.asc())
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting messages for conversation {conversation_id}: {e}")
            raise DatabaseError("Failed to retrieve conversation messages") from e

