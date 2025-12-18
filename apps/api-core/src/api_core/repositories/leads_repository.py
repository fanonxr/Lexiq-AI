"""Leads repository for data access operations."""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from api_core.database.models import Lead
from api_core.exceptions import DatabaseError
from api_core.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class LeadsRepository(BaseRepository[Lead]):
    """Repository for lead data access operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Lead, session)

    async def get_by_idempotency_key(self, idempotency_key: str) -> Optional[Lead]:
        """Return a lead by idempotency key (if exists)."""
        try:
            result = await self.session.execute(select(Lead).where(Lead.idempotency_key == idempotency_key))
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting lead by idempotency_key: {e}")
            raise DatabaseError("Failed to retrieve lead") from e


