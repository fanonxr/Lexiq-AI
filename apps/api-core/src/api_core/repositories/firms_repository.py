"""Firm configuration repository (MVP firm personas)."""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from api_core.database.models import FirmPersona
from api_core.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class FirmsRepository:
    """Repository for firm persona records."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_persona(self, firm_id: str) -> Optional[FirmPersona]:
        try:
            result = await self.session.execute(
                select(FirmPersona).where(FirmPersona.firm_id == firm_id)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting firm persona: {e}")
            raise DatabaseError("Failed to retrieve firm persona") from e

    async def upsert_persona(self, firm_id: str, system_prompt: str) -> FirmPersona:
        try:
            existing = await self.get_persona(firm_id)
            if existing:
                existing.system_prompt = system_prompt
                await self.session.flush()
                await self.session.refresh(existing)
                return existing

            persona = FirmPersona(firm_id=firm_id, system_prompt=system_prompt)
            self.session.add(persona)
            await self.session.flush()
            await self.session.refresh(persona)
            return persona
        except DatabaseError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error upserting firm persona: {e}")
            raise DatabaseError("Failed to upsert firm persona") from e


