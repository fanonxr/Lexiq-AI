"""Appointments repository for data access operations."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

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

    async def get_by_user_id(
        self,
        user_id: str,
        firm_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        clients_only: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Appointment]:
        """
        Get appointments for a user.
        
        Args:
            user_id: User ID
            firm_id: Optional firm ID to filter by
            start_date: Optional start date filter
            end_date: Optional end date filter
            clients_only: If True, only return appointments created through LexiqAI (source_calendar_id IS NULL)
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of appointments
        """
        try:
            from sqlalchemy import or_
            
            query = select(Appointment)
            
            # Filter by user (created_by_user_id) or firm
            # Include appointments that match either firm_id OR created_by_user_id
            conditions = []
            if firm_id:
                conditions.append(Appointment.firm_id == firm_id)
            if user_id:
                conditions.append(Appointment.created_by_user_id == user_id)
            
            if conditions:
                # Use OR logic if both conditions exist, otherwise use the single condition
                if len(conditions) > 1:
                    query = query.where(or_(*conditions))
                else:
                    query = query.where(conditions[0])
            
            # Filter by source: if clients_only=True, only show LexiqAI-created appointments
            # (appointments where source_calendar_id IS NULL)
            if clients_only:
                query = query.where(Appointment.source_calendar_id.is_(None))
            
            # Date range filters
            if start_date:
                query = query.where(Appointment.start_at >= start_date)
            if end_date:
                query = query.where(Appointment.start_at <= end_date)
            
            # Order by start_at ascending
            query = query.order_by(Appointment.start_at.asc())
            
            # Pagination
            query = query.offset(skip).limit(limit)
            
            result = await self.session.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting appointments for user {user_id}: {e}")
            raise DatabaseError("Failed to retrieve appointments") from e


