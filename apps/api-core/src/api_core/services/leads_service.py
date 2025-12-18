"""Lead/intake service (LexiqAI-native).

MVP behavior:
- Idempotent creation via idempotency_key
- Minimal validation (requires firm_id + full_name)
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from api_core.exceptions import ValidationError
from api_core.models.leads import LeadCreateRequest, LeadResponse
from api_core.repositories.leads_repository import LeadsRepository


class LeadsService:
    """Service for lead/intake operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = LeadsRepository(session)

    async def create_lead(self, request: LeadCreateRequest) -> LeadResponse:
        """Create a lead (idempotent)."""
        if not request.firm_id.strip():
            raise ValidationError("firm_id is required")
        if not request.full_name.strip():
            raise ValidationError("full_name is required")

        existing = await self._repo.get_by_idempotency_key(request.idempotency_key)
        if existing:
            return LeadResponse(
                lead_id=existing.id,
                firm_id=existing.firm_id,
                full_name=existing.full_name,
                email=existing.email,
                phone=existing.phone,
                matter_type=existing.matter_type,
                summary=existing.summary,
                status=existing.status,
                created_at=existing.created_at,
            )

        created = await self._repo.create(
            firm_id=request.firm_id,
            full_name=request.full_name,
            email=request.email,
            phone=request.phone,
            matter_type=request.matter_type,
            summary=request.summary,
            status="new",
            idempotency_key=request.idempotency_key,
        )

        return LeadResponse(
            lead_id=created.id,
            firm_id=created.firm_id,
            full_name=created.full_name,
            email=created.email,
            phone=created.phone,
            matter_type=created.matter_type,
            summary=created.summary,
            status=created.status,
            created_at=created.created_at,
        )


def get_leads_service(session: AsyncSession) -> LeadsService:
    """Factory for LeadsService."""
    return LeadsService(session=session)


