"""Notifications service (LexiqAI-native outbox).

MVP behavior:
- Create an outbox record (idempotent via idempotency_key)
- Does not deliver externally yet (provider integration later)
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from api_core.exceptions import ValidationError
from api_core.models.notifications import NotificationCreateRequest, NotificationResponse
from api_core.repositories.notifications_repository import NotificationsRepository


class NotificationsService:
    """Service for notification outbox operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = NotificationsRepository(session)

    async def create_notification(self, request: NotificationCreateRequest) -> NotificationResponse:
        """Create a notification outbox record (idempotent)."""
        if not request.firm_id.strip():
            raise ValidationError("firm_id is required")
        if not request.to.strip():
            raise ValidationError("to is required")
        if not request.message.strip():
            raise ValidationError("message is required")

        if request.channel == "email" and request.subject is None:
            # Optional subject is allowed, but UX generally wants one; keep it permissive for MVP.
            pass

        existing = await self._repo.get_by_idempotency_key(request.idempotency_key)
        if existing:
            return NotificationResponse(
                notification_id=existing.id,
                firm_id=existing.firm_id,
                channel=existing.channel,  # literal coercion
                to=existing.to,
                subject=existing.subject,
                message=existing.message,
                status=existing.status,
                created_at=existing.created_at,
            )

        created = await self._repo.create(
            firm_id=request.firm_id,
            channel=request.channel,
            to=request.to,
            subject=request.subject,
            message=request.message,
            status="queued",
            idempotency_key=request.idempotency_key,
        )

        return NotificationResponse(
            notification_id=created.id,
            firm_id=created.firm_id,
            channel=created.channel,
            to=created.to,
            subject=created.subject,
            message=created.message,
            status=created.status,
            created_at=created.created_at,
        )


def get_notifications_service(session: AsyncSession) -> NotificationsService:
    """Factory for NotificationsService."""
    return NotificationsService(session=session)


