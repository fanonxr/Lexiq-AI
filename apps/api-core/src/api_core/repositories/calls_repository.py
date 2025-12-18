"""Calls repository for data access operations."""

from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from api_core.database.models import Call
from api_core.exceptions import DatabaseError
from api_core.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class CallsRepository(BaseRepository[Call]):
    """Repository for call data access operations."""

    def __init__(self, session: AsyncSession):
        """Initialize calls repository."""
        super().__init__(Call, session)

    async def get_by_user_id(
        self,
        user_id: str,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Call]:
        """Get calls for a user, optionally filtered by status."""
        try:
            query = select(Call).where(Call.user_id == user_id)
            if status:
                query = query.where(Call.status == status)
            query = query.order_by(Call.created_at.desc()).offset(skip).limit(limit)

            result = await self.session.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting calls for user {user_id}: {e}")
            raise DatabaseError("Failed to retrieve calls") from e

    async def get_by_twilio_call_sid(self, twilio_call_sid: str) -> Optional[Call]:
        """Get a call by Twilio call SID."""
        try:
            result = await self.session.execute(
                select(Call).where(Call.twilio_call_sid == twilio_call_sid)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting call by Twilio SID {twilio_call_sid}: {e}")
            raise DatabaseError("Failed to retrieve call") from e

    async def count_by_user_id(self, user_id: str, status: Optional[str] = None) -> int:
        """Count calls for a user."""
        try:
            from sqlalchemy import func

            query = select(func.count(Call.id)).where(Call.user_id == user_id)
            if status:
                query = query.where(Call.status == status)

            result = await self.session.execute(query)
            return result.scalar_one() or 0
        except SQLAlchemyError as e:
            logger.error(f"Error counting calls for user {user_id}: {e}")
            raise DatabaseError("Failed to count calls") from e

