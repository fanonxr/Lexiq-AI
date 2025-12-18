"""Firm configuration service (MVP firm personas)."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api_core.database.models import Appointment, Firm, KnowledgeBaseFile, Lead
from api_core.exceptions import AuthorizationError, NotFoundError, ValidationError
from api_core.models.firms import FirmPersonaResponse, FirmSettingsResponse
from api_core.repositories.firms_repository import FirmsRepository


class FirmsService:
    """Service for firm persona operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = FirmsRepository(session)
        self.session = session

    async def check_user_firm_access(self, user_id: str, firm_id: str) -> bool:
        """
        Check if a user has access to a firm by verifying they have resources for that firm.
        
        A user has access if they have:
        - Knowledge base files for the firm
        - Appointments for the firm
        - Leads for the firm
        - Or if firm_id == user_id (simple MVP: user is their own firm)
        """
        # Simple MVP: user is their own firm
        if firm_id == user_id:
            return True

        # Check if user has any resources for this firm
        # Check knowledge base files
        kb_result = await self.session.execute(
            select(KnowledgeBaseFile).where(
                KnowledgeBaseFile.user_id == user_id,
                KnowledgeBaseFile.firm_id == firm_id,
            ).limit(1)
        )
        if kb_result.scalar_one_or_none():
            return True

        # Check appointments (if user_id is stored somewhere - for now, just check firm_id)
        # Note: Appointments don't have user_id, so we skip this check for now
        # In the future, we might add created_by_user_id to appointments

        # Check leads (if user_id is stored)
        lead_result = await self.session.execute(
            select(Lead).where(
                Lead.created_by_user_id == user_id,
                Lead.firm_id == firm_id,
            ).limit(1)
        )
        if lead_result.scalar_one_or_none():
            return True

        return False

    async def get_firm_persona(
        self, firm_id: str, user_id: Optional[str]
    ) -> FirmPersonaResponse:
        if not firm_id or not firm_id.strip():
            raise ValidationError("firm_id is required")

        # Check authorization (skip if user_id is None - internal service call)
        if user_id is not None:
            has_access = await self.check_user_firm_access(user_id, firm_id)
            if not has_access:
                raise AuthorizationError(
                    f"User {user_id} does not have access to firm {firm_id}"
                )

        persona = await self._repo.get_persona(firm_id)
        if not persona:
            raise NotFoundError(resource="FirmPersona", resource_id=firm_id)

        return FirmPersonaResponse(
            firm_id=persona.firm_id,
            system_prompt=persona.system_prompt,
            updated_at=persona.updated_at,
        )

    async def upsert_firm_persona(
        self, firm_id: str, system_prompt: str, user_id: Optional[str]
    ) -> FirmPersonaResponse:
        if not firm_id or not firm_id.strip():
            raise ValidationError("firm_id is required")
        if system_prompt is None:
            raise ValidationError("system_prompt is required")

        # Check authorization (skip if user_id is None - internal service call)
        if user_id is not None:
            has_access = await self.check_user_firm_access(user_id, firm_id)
            if not has_access:
                raise AuthorizationError(
                    f"User {user_id} does not have access to firm {firm_id}"
                )

        persona = await self._repo.upsert_persona(firm_id, system_prompt)
        return FirmPersonaResponse(
            firm_id=persona.firm_id,
            system_prompt=persona.system_prompt,
            updated_at=persona.updated_at,
        )

    async def get_firm_settings(
        self, firm_id: str, user_id: Optional[str]
    ) -> FirmSettingsResponse:
        """Get full firm settings including model, persona, specialties, etc.
        
        This endpoint is primarily for internal service calls (Cognitive Orchestrator)
        to retrieve all firm configuration needed for prompt building.
        """
        if not firm_id or not firm_id.strip():
            raise ValidationError("firm_id is required")

        # Check authorization (skip if user_id is None - internal service call)
        if user_id is not None:
            has_access = await self.check_user_firm_access(user_id, firm_id)
            if not has_access:
                raise AuthorizationError(
                    f"User {user_id} does not have access to firm {firm_id}"
                )

        # Get firm from database
        result = await self.session.execute(
            select(Firm).where(Firm.id == firm_id)
        )
        firm = result.scalar_one_or_none()
        
        if not firm:
            raise NotFoundError(resource="Firm", resource_id=firm_id)

        # Get persona if it exists
        persona = await self._repo.get_persona(firm_id)
        system_prompt = persona.system_prompt if persona else firm.system_prompt

        return FirmSettingsResponse(
            firm_id=firm.id,
            name=firm.name,
            domain=firm.domain,
            default_model=firm.default_model,
            system_prompt=system_prompt,
            specialties=firm.specialties,
            qdrant_collection=firm.qdrant_collection,
            created_at=firm.created_at,
            updated_at=firm.updated_at,
        )


def get_firms_service(session: AsyncSession) -> FirmsService:
    return FirmsService(session=session)


