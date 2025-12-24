"""Calendar integration repository."""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api_core.database.models import CalendarIntegration
from api_core.repositories.base import BaseRepository


class CalendarIntegrationRepository(BaseRepository[CalendarIntegration]):
    """Repository for calendar integration operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(CalendarIntegration, session)

    async def get_by_user_and_type(
        self,
        user_id: str,
        integration_type: str,
    ) -> Optional[CalendarIntegration]:
        """Get integration by user and type."""
        result = await self.session.execute(
            select(CalendarIntegration)
            .where(CalendarIntegration.user_id == user_id)
            .where(CalendarIntegration.integration_type == integration_type)
            .where(CalendarIntegration.is_active == True)
        )
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: str) -> List[CalendarIntegration]:
        """Get all active integrations for a user."""
        result = await self.session.execute(
            select(CalendarIntegration)
            .where(CalendarIntegration.user_id == user_id)
            .where(CalendarIntegration.is_active == True)
        )
        return list(result.scalars().all())

