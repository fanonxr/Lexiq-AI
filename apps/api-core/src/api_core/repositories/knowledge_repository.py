"""Knowledge base repository for data access operations."""

import logging
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from api_core.database.models import KnowledgeBaseFile
from api_core.exceptions import DatabaseError, NotFoundError
from api_core.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class KnowledgeRepository(BaseRepository[KnowledgeBaseFile]):
    """Repository for knowledge base file data access operations."""

    def __init__(self, session: AsyncSession):
        """Initialize knowledge repository."""
        super().__init__(KnowledgeBaseFile, session)

    async def get_by_user_id(
        self, user_id: str, firm_id: Optional[str] = None
    ) -> List[KnowledgeBaseFile]:
        """
        Get all knowledge base files for a user.

        Args:
            user_id: User ID
            firm_id: Optional firm ID to filter by

        Returns:
            List of KnowledgeBaseFile instances
        """
        try:
            query = select(KnowledgeBaseFile).where(KnowledgeBaseFile.user_id == user_id)
            if firm_id:
                query = query.where(KnowledgeBaseFile.firm_id == firm_id)
            query = query.order_by(KnowledgeBaseFile.created_at.desc())

            result = await self.session.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting knowledge base files for user {user_id}: {e}")
            raise DatabaseError("Failed to retrieve knowledge base files") from e

    async def get_by_firm_id(self, firm_id: str) -> List[KnowledgeBaseFile]:
        """
        Get all knowledge base files for a firm.

        Args:
            firm_id: Firm ID

        Returns:
            List of KnowledgeBaseFile instances
        """
        try:
            result = await self.session.execute(
                select(KnowledgeBaseFile)
                .where(KnowledgeBaseFile.firm_id == firm_id)
                .order_by(KnowledgeBaseFile.created_at.desc())
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting knowledge base files for firm {firm_id}: {e}")
            raise DatabaseError("Failed to retrieve knowledge base files") from e

    async def get_by_status(self, status: str, firm_id: Optional[str] = None) -> List[KnowledgeBaseFile]:
        """
        Get knowledge base files by status.

        Args:
            status: File status (pending, processing, indexed, failed)
            firm_id: Optional firm ID to filter by

        Returns:
            List of KnowledgeBaseFile instances
        """
        try:
            query = select(KnowledgeBaseFile).where(KnowledgeBaseFile.status == status)
            if firm_id:
                query = query.where(KnowledgeBaseFile.firm_id == firm_id)
            query = query.order_by(KnowledgeBaseFile.created_at.desc())

            result = await self.session.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting knowledge base files by status {status}: {e}")
            raise DatabaseError("Failed to retrieve knowledge base files") from e

