"""Agent configuration repository."""

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from api_core.database.models import AgentConfig
from api_core.exceptions import DatabaseError
from api_core.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class AgentRepository(BaseRepository[AgentConfig]):
    """Repository for agent configuration operations."""

    def __init__(self, session: AsyncSession):
        """Initialize agent repository."""
        super().__init__(AgentConfig, session)

    async def get_by_user_id(self, user_id: str, firm_id: Optional[str] = None) -> Optional[AgentConfig]:
        """
        Get agent config by user ID, optionally filtered by firm ID.
        
        Priority: firm-specific config > user-specific config
        
        Args:
            user_id: User ID
            firm_id: Optional firm ID (if provided, looks for firm-specific config first)
            
        Returns:
            AgentConfig instance or None if not found
        """
        try:
            # If firm_id is provided, try to get firm-specific config first
            if firm_id:
                result = await self.session.execute(
                    select(AgentConfig)
                    .where(AgentConfig.user_id == user_id)
                    .where(AgentConfig.firm_id == firm_id)
                )
                config = result.scalar_one_or_none()
                if config:
                    return config
            
            # Fallback to user-specific config (firm_id is NULL)
            result = await self.session.execute(
                select(AgentConfig)
                .where(AgentConfig.user_id == user_id)
                .where(AgentConfig.firm_id.is_(None))
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting agent config for user {user_id}, firm {firm_id}: {e}")
            raise DatabaseError("Failed to retrieve agent configuration") from e

    async def create_or_update(
        self,
        user_id: str,
        firm_id: Optional[str] = None,
        **kwargs
    ) -> AgentConfig:
        """
        Create or update agent configuration.
        
        If a config exists for the user/firm combination, update it.
        Otherwise, create a new one.
        
        Args:
            user_id: User ID
            firm_id: Optional firm ID
            **kwargs: Configuration fields to update
            
        Returns:
            AgentConfig instance
        """
        try:
            # Try to get existing config
            existing = await self.get_by_user_id(user_id, firm_id)
            
            if existing:
                # Update existing config
                for key, value in kwargs.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                await self.session.commit()
                await self.session.refresh(existing)
                return existing
            else:
                # Create new config
                config_data = {
                    "user_id": user_id,
                    "firm_id": firm_id,
                    **kwargs
                }
                return await self.create(**config_data)
        except SQLAlchemyError as e:
            logger.error(f"Error creating/updating agent config for user {user_id}, firm {firm_id}: {e}")
            await self.session.rollback()
            raise DatabaseError("Failed to save agent configuration") from e

