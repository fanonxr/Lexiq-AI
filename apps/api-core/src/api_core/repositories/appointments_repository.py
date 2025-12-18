"""Appointments repository for data access operations."""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from api_core.database.models import Appointment
from api_core.exceptions import DatabaseError
from api_core.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class AppointmentsRepository(BaseRepository[Appointment]):
    """Repository for appointment data access operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Appointment, session)

    async def get_by_idempotency_key(self, idempotency_key: str) -> Optional[Appointment]:
        """Return an appointment by idempotency key (if exists)."""
        try:
            result = await self.session.execute(
                select(Appointment).where(Appointment.idempotency_key == idempotency_key)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting appointment by idempotency_key: {e}")
            raise DatabaseError("Failed to retrieve appointment") from e


