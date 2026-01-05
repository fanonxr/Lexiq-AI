"""Database repositories for integration worker.

This module provides access to database models from api-core.
Both services share the same PostgreSQL database.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Import models from api-core (shared database)
# Import directly from models to avoid triggering config initialization
try:
    # Direct import to avoid config validation issues
    import sys
    import os
    
    # Add api-core to path if not already there
    api_core_path = "/app/api-core/src"
    if api_core_path not in sys.path:
        sys.path.insert(0, api_core_path)
    
    # Import models directly (avoids __init__.py which imports connection.py which loads config)
    from api_core.database.models import CalendarIntegration, User, Appointment
    
except ImportError as e:
    # Fallback for development - we'll handle this by symlinking or path manipulation
    raise ImportError(
        f"Cannot import api_core models: {e}. "
        "Ensure api-core is in PYTHONPATH or installed as a package."
    )


class CalendarIntegrationRepository:
    """Repository for calendar integration operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, integration_id: str) -> Optional[CalendarIntegration]:
        """Get integration by ID."""
        result = await self.session.execute(
            select(CalendarIntegration).where(CalendarIntegration.id == integration_id)
        )
        return result.scalar_one_or_none()
    
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
    
    async def get_all_active(self) -> List[CalendarIntegration]:
        """Get all active calendar integrations (for scheduled sync)."""
        result = await self.session.execute(
            select(CalendarIntegration).where(CalendarIntegration.is_active == True)
        )
        return list(result.scalars().all())
    
    async def get_with_expiring_tokens(
        self, expiration_threshold: datetime
    ) -> List[CalendarIntegration]:
        """
        Get integrations with tokens expiring soon.
        
        Args:
            expiration_threshold: Get tokens expiring before this datetime
        
        Returns:
            List of integrations with expiring tokens
        """
        result = await self.session.execute(
            select(CalendarIntegration)
            .where(CalendarIntegration.is_active == True)
            .where(CalendarIntegration.token_expires_at != None)
            .where(CalendarIntegration.token_expires_at <= expiration_threshold)
        )
        return list(result.scalars().all())


class AppointmentsRepository:
    """Repository for appointment operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_idempotency_key(self, idempotency_key: str) -> Optional[Appointment]:
        """Get appointment by idempotency key."""
        result = await self.session.execute(
            select(Appointment).where(Appointment.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()
    
    async def create(self, **kwargs) -> Appointment:
        """Create a new appointment."""
        appointment = Appointment(**kwargs)
        self.session.add(appointment)
        await self.session.flush()
        await self.session.refresh(appointment)
        return appointment
    
    async def update(self, appointment: Appointment) -> Appointment:
        """Update an existing appointment."""
        await self.session.flush()
        await self.session.refresh(appointment)
        return appointment

