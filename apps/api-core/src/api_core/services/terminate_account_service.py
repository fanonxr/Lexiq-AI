"""
Permanently terminate a user account and all associated resources.

Order: Stripe cancel → Twilio return-to-pool → collect conversation IDs →
Calendar webhook revoke → Qdrant + Blob → DB (orphan firm then user) → Redis keys.

User delete cascades: ConversationMessage, Call, Conversation, Subscription,
Invoice, UsageRecord, KnowledgeBaseFile, AgentConfig, CalendarIntegration.
Orphan firm delete: FirmPersona, Appointment, Lead, Notification, Client (→ ClientMemory).
Plan is shared reference data and is not deleted.
"""

from __future__ import annotations

import json
import logging
from typing import List, Optional

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api_core.config import get_settings

from api_core.database.models import (
    Appointment,
    Client,
    Conversation,
    Firm,
    FirmPersona,
    Lead,
    Notification,
    Subscription,
    User,
)
from api_core.exceptions import NotFoundError
from api_core.repositories.calendar_integration_repository import (
    CalendarIntegrationRepository,
)
from api_core.repositories.firms_repository import FirmsRepository
from api_core.repositories.knowledge_repository import KnowledgeRepository
from api_core.repositories.phone_number_pool_repository import PhoneNumberPoolRepository
from api_core.repositories.user_repository import UserRepository
from api_core.services.calendar_integration_service import CalendarIntegrationService
from api_core.services.qdrant_service import delete_collection as qdrant_delete_collection
from api_core.services.qdrant_service import delete_points as qdrant_delete_points
from api_core.services.redis_cleanup_service import delete_conversation_keys
from api_core.services.storage_service import get_storage_service

logger = logging.getLogger(__name__)


class TerminateAccountService:
    """Permanently terminate a user account and all associated resources."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._user_repo = UserRepository(session)
        self._firms_repo = FirmsRepository(session)
        self._knowledge_repo = KnowledgeRepository(session)
        self._pool_repo = PhoneNumberPoolRepository(session)
        self._calendar_repo = CalendarIntegrationRepository(session)
        self._calendar_service = CalendarIntegrationService(session)
        self._storage = get_storage_service()

    async def _get_user_count_in_firm(self, firm_id: str) -> int:
        """Return number of users with this firm_id (including the one we're deleting)."""
        result = await self.session.execute(
            select(func.count(User.id)).where(User.firm_id == firm_id)
        )
        return result.scalar() or 0

    async def _cancel_stripe_subscriptions_for_user(self, user_id: str) -> None:
        """Cancel all active/trialing Stripe subscriptions for the user (immediate cancel)."""
        result = await self.session.execute(
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .where(Subscription.payment_provider == "stripe")
            .where(
                or_(
                    Subscription.status == "active",
                    Subscription.status == "trialing",
                )
            )
            .where(Subscription.payment_provider_subscription_id.isnot(None))
        )
        subs = list(result.scalars().all())
        if not subs:
            return
        try:
            from api_core.services.stripe_service import get_stripe_service

            stripe_service = get_stripe_service(self.session)
            for sub in subs:
                sid = sub.payment_provider_subscription_id
                if not sid:
                    continue
                try:
                    await stripe_service.cancel_subscription(
                        stripe_subscription_id=sid,
                        cancel_at_period_end=False,
                    )
                    logger.info(
                        f"Cancelled Stripe subscription {sid} for user {user_id}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to cancel Stripe subscription {sid} for user {user_id}: {e}. Continuing."
                    )
        except Exception as e:
            logger.warning(
                f"Stripe cancel failed for user {user_id}: {e}. Continuing with terminate."
            )

    async def _return_firm_number_to_pool(self, firm: Firm) -> None:
        """Transfer firm's Twilio number to pool and add to pool table (return-to-pool)."""
        phone_sid = getattr(firm, "twilio_phone_number_sid", None)
        subaccount_sid = getattr(firm, "twilio_subaccount_sid", None)
        phone_number = getattr(firm, "twilio_phone_number", None)
        if not phone_sid or not subaccount_sid or not phone_number:
            return
        settings = get_settings()
        pool_target_sid = (
            settings.twilio.pool_subaccount_sid
            if (settings.twilio.pool_subaccount_sid and settings.twilio.pool_subaccount_sid.strip())
            else None
        )
        if not pool_target_sid:
            from api_core.services.twilio_service import get_twilio_service

            twilio_service = get_twilio_service()
            pool_target_sid = twilio_service.main_account_sid
        if not pool_target_sid:
            logger.warning(
                "Twilio pool target (main or TWILIO_POOL_SUBACCOUNT_SID) not available. Skipping return-to-pool."
            )
            return
        try:
            from api_core.services.twilio_service import get_twilio_service

            twilio_service = get_twilio_service()
            await twilio_service.transfer_phone_number_to_account(
                phone_number_sid=phone_sid,
                source_account_sid=subaccount_sid,
                target_account_sid=pool_target_sid,
            )
            await self._pool_repo.add_to_pool(
                phone_number=phone_number,
                twilio_phone_number_sid=phone_sid,
                pool_account_sid=pool_target_sid,
            )
            await self._firms_repo.clear_phone_number(firm.id)
            logger.info(
                f"Returned number {phone_number} to pool (firm_id={firm.id})"
            )
        except Exception as e:
            logger.warning(
                f"Twilio return-to-pool failed for firm {firm.id}: {e}. Continuing with terminate."
            )

    async def _close_firm_twilio_subaccount(self, firm: Firm) -> None:
        """Close the firm's Twilio subaccount (status=closed). Call after number is returned to pool."""
        subaccount_sid = getattr(firm, "twilio_subaccount_sid", None)
        if not subaccount_sid:
            return
        try:
            from api_core.services.twilio_service import get_twilio_service

            twilio_service = get_twilio_service()
            await twilio_service.close_subaccount(subaccount_sid)
        except Exception as e:
            logger.warning(
                f"Twilio close subaccount failed for firm {firm.id}: {e}. Continuing with terminate."
            )

    async def _delete_qdrant_and_blob_for_user(self, user_id: str) -> None:
        """Delete Qdrant points and Blob files for all knowledge base files of this user."""
        kb_files = await self._knowledge_repo.get_by_user_id(user_id)
        for kb in kb_files:
            # Qdrant: delete points for this file (before we lose metadata)
            if kb.qdrant_collection and kb.qdrant_point_ids:
                try:
                    point_ids: List[str] = json.loads(kb.qdrant_point_ids)
                    if point_ids:
                        qdrant_delete_points(kb.qdrant_collection, point_ids)
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(
                        f"Could not parse qdrant_point_ids for file {kb.id}: {e}"
                    )
            # Blob: delete file (best-effort; continue on failure)
            try:
                parts = kb.storage_path.split("/", 1)
                if len(parts) == 2:
                    container_name, blob_name = parts
                    await self._storage.delete_file(container_name, blob_name)
            except Exception as e:
                logger.warning(
                    f"Blob delete failed for {kb.storage_path} (file_id={kb.id}): {e}. Continuing."
                )

    async def _delete_orphan_firm_data(self, firm_id: str) -> None:
        """Delete firm-scoped rows and the firm. Client cascades to ClientMemory."""
        await self.session.execute(delete(FirmPersona).where(FirmPersona.firm_id == firm_id))
        await self.session.execute(delete(Appointment).where(Appointment.firm_id == firm_id))
        await self.session.execute(delete(Lead).where(Lead.firm_id == firm_id))
        await self.session.execute(delete(Notification).where(Notification.firm_id == firm_id))
        await self.session.execute(delete(Client).where(Client.firm_id == firm_id))  # cascades ClientMemory
        await self.session.execute(delete(Firm).where(Firm.id == firm_id))
        await self.session.flush()

    async def terminate_account(self, user_id: str) -> None:
        """
        Permanently terminate the account for the given user.

        Raises NotFoundError if the user does not exist.
        """
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(resource="User", resource_id=user_id)

        firm_id: Optional[str] = getattr(user, "firm_id", None)
        firm = await self._firms_repo.get_by_id(firm_id) if firm_id else None
        orphan_firm = False
        if firm_id:
            user_count = await self._get_user_count_in_firm(firm_id)
            orphan_firm = user_count <= 1

        await self._cancel_stripe_subscriptions_for_user(user_id)

        if orphan_firm and firm and getattr(firm, "twilio_phone_number_sid", None):
            await self._return_firm_number_to_pool(firm)

        if orphan_firm and firm and getattr(firm, "twilio_subaccount_sid", None):
            await self._close_firm_twilio_subaccount(firm)

        conv_result = await self.session.execute(
            select(Conversation.id).where(Conversation.user_id == user_id)
        )
        conversation_ids: List[str] = [row[0] for row in conv_result.all()]

        calendar_integrations = await self._calendar_repo.get_all_by_user(user_id)
        for integration in calendar_integrations:
            try:
                await self._calendar_service.delete_outlook_webhook_subscription(
                    integration
                )
            except Exception as e:
                logger.warning(
                    f"Calendar webhook delete failed for integration {integration.id}: {e}. Continuing."
                )

        await self._delete_qdrant_and_blob_for_user(user_id)
        if orphan_firm and firm and getattr(firm, "qdrant_collection", None):
            qdrant_delete_collection(firm.qdrant_collection)

        if orphan_firm and firm_id:
            await self._delete_orphan_firm_data(firm_id)

        await self.session.delete(user)
        await self.session.flush()

        await delete_conversation_keys(conversation_ids)

        logger.info(
            f"Terminated account: user_id={user_id}, orphan_firm={orphan_firm}",
            extra={"user_id": user_id, "orphan_firm": orphan_firm},
        )


def get_terminate_account_service(session: AsyncSession) -> TerminateAccountService:
    """Create a TerminateAccountService for the given session."""
    return TerminateAccountService(session)
