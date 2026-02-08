"""
Periodic cleanup of orphaned resources.

Finds resources that no longer have a corresponding entity in our DB
(Twilio subaccounts, pool numbers, Qdrant collections, Redis keys,
user-scoped rows for deleted users) and terminates or reclaims them.
"""

from __future__ import annotations

import json
import logging
from typing import Set

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from api_core.database.models import (
    CalendarIntegration,
    Conversation,
    Firm,
    Invoice,
    KnowledgeBaseFile,
    PhoneNumberPool,
    Subscription,
    UsageRecord,
    User,
)
from api_core.services.redis_cleanup_service import CONVERSATION_KEY_PREFIX

logger = logging.getLogger(__name__)


class OrphanCleanupService:
    """Finds and terminates all orphaned resources (Twilio, pool, Qdrant, Redis, orphan user data)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def run(self) -> dict:
        """
        Run all orphan cleanup steps.

        Returns:
            Dict with counts for each resource type cleaned.
        """
        result = {
            "twilio_subaccounts_closed": 0,
            "pool_numbers_reclaimed": 0,
            "qdrant_collections_deleted": 0,
            "redis_conversation_keys_deleted": 0,
            "orphan_user_data_deleted": 0,
        }

        result["twilio_subaccounts_closed"] = await self._close_orphaned_twilio_subaccounts()
        result["pool_numbers_reclaimed"] = await self._reclaim_orphaned_pool_numbers()
        result["qdrant_collections_deleted"] = await self._delete_orphaned_qdrant_collections()
        result["redis_conversation_keys_deleted"] = await self._delete_orphaned_redis_conversation_keys()
        result["orphan_user_data_deleted"] = await self._delete_orphaned_user_data()

        logger.info("Orphan cleanup completed", extra=result)
        return result

    async def _close_orphaned_twilio_subaccounts(self) -> int:
        """
        Close Twilio subaccounts that are not tied to any firm (orphaned).

        Keeps: main account, pool subaccount (if set), and any subaccount SID
        present in firms.twilio_subaccount_sid. Closes all other active subaccounts.
        """
        try:
            from api_core.config import get_settings
            from api_core.services.twilio_service import get_twilio_service

            settings = get_settings()
            keep_sids: Set[str] = set()

            twilio_service = get_twilio_service()
            if twilio_service.main_account_sid:
                keep_sids.add(twilio_service.main_account_sid)
            if settings.twilio.pool_subaccount_sid and settings.twilio.pool_subaccount_sid.strip():
                keep_sids.add(settings.twilio.pool_subaccount_sid.strip())

            result = await self.session.execute(
                select(Firm.twilio_subaccount_sid).where(
                    Firm.twilio_subaccount_sid.isnot(None)
                )
            )
            for row in result.all():
                if row[0]:
                    keep_sids.add(row[0])

            subaccounts = await twilio_service.list_subaccounts()
            closed = 0
            for sub in subaccounts:
                if sub.status != "active":
                    continue
                if sub.sid in keep_sids:
                    continue
                try:
                    await twilio_service.close_subaccount(sub.sid)
                    closed += 1
                except Exception as e:
                    logger.warning(
                        f"Failed to close orphaned subaccount {sub.sid}: {e}. Continuing."
                    )
            return closed
        except Exception as e:
            logger.warning(
                f"Orphan Twilio subaccount cleanup failed: {e}. Continuing.",
                exc_info=True,
            )
            return 0

    async def _reclaim_orphaned_pool_numbers(self) -> int:
        """
        Reclaim pool numbers that are assigned to a firm that no longer exists.

        Sets status=available, firm_id=None, assigned_at=None for those rows.
        """
        try:
            result = await self.session.execute(
                select(PhoneNumberPool).where(
                    PhoneNumberPool.status == "assigned",
                    PhoneNumberPool.firm_id.isnot(None),
                )
            )
            pool_rows = list(result.scalars().all())
            if not pool_rows:
                return 0

            firm_ids = {r.firm_id for r in pool_rows if r.firm_id}
            firm_exists_result = await self.session.execute(
                select(Firm.id).where(Firm.id.in_(firm_ids))
            )
            existing_firm_ids = {row[0] for row in firm_exists_result.all()}

            reclaimed = 0
            for row in pool_rows:
                if not row.firm_id or row.firm_id in existing_firm_ids:
                    continue
                old_firm_id = row.firm_id
                row.status = "available"
                row.firm_id = None
                row.assigned_at = None
                reclaimed += 1
                logger.info(
                    f"Reclaimed orphaned pool number {row.phone_number} (was assigned to deleted firm {old_firm_id})"
                )
            if reclaimed:
                await self.session.flush()
            return reclaimed
        except Exception as e:
            logger.warning(
                f"Orphan pool number reclaim failed: {e}. Continuing.",
                exc_info=True,
            )
            return 0

    async def _delete_orphaned_qdrant_collections(self) -> int:
        """
        Delete Qdrant collections that are not tied to any firm (orphaned).

        Keeps only collections present in firms.qdrant_collection.
        """
        try:
            from api_core.services.qdrant_service import delete_collection as qdrant_delete_collection
            from api_core.services.qdrant_service import list_collections as qdrant_list_collections

            keep: Set[str] = set()
            result = await self.session.execute(
                select(Firm.qdrant_collection).where(
                    Firm.qdrant_collection.isnot(None)
                )
            )
            for row in result.all():
                if row[0] and row[0].strip():
                    keep.add(row[0].strip())

            collections = qdrant_list_collections()
            deleted = 0
            for name in collections:
                if not name or name in keep:
                    continue
                try:
                    qdrant_delete_collection(name)
                    deleted += 1
                except Exception as e:
                    logger.warning(f"Failed to delete orphaned Qdrant collection {name}: {e}. Continuing.")
            return deleted
        except Exception as e:
            logger.warning(
                f"Orphan Qdrant collection cleanup failed: {e}. Continuing.",
                exc_info=True,
            )
            return 0

    async def _delete_orphaned_redis_conversation_keys(self) -> int:
        """
        Delete Redis conversation:* keys whose conversation no longer exists in DB.
        """
        try:
            from api_core.config import get_settings

            settings = get_settings()
            if not (settings.redis.url and settings.redis.url.strip()):
                return 0

            result = await self.session.execute(select(User.id))
            valid_user_ids = {row[0] for row in result.all()}
            result = await self.session.execute(
                select(Conversation.id).where(Conversation.user_id.in_(valid_user_ids))
            )
            valid_conversation_ids: Set[str] = {row[0] for row in result.all()}

            import redis.asyncio as redis

            client = redis.from_url(
                settings.redis.url,
                password=settings.redis.password,
                decode_responses=settings.redis.decode_responses,
                socket_timeout=settings.redis.socket_timeout,
                socket_connect_timeout=settings.redis.socket_connect_timeout,
            )
            try:
                deleted = 0
                cursor = 0
                pattern = f"{CONVERSATION_KEY_PREFIX}*"
                while True:
                    cursor, keys = await client.scan(cursor=cursor, match=pattern, count=100)
                    for key in keys:
                        cid = key[len(CONVERSATION_KEY_PREFIX) :] if key.startswith(CONVERSATION_KEY_PREFIX) else ""
                        if cid and cid not in valid_conversation_ids:
                            try:
                                await client.delete(key)
                                deleted += 1
                            except Exception as e:
                                logger.warning(f"Redis delete key {key} failed: {e}")
                    if cursor == 0:
                        break
                if deleted:
                    logger.info(f"Deleted {deleted} orphaned Redis conversation keys")
                return deleted
            finally:
                await client.aclose()
        except Exception as e:
            logger.warning(
                f"Orphan Redis conversation key cleanup failed: {e}. Continuing.",
                exc_info=True,
            )
            return 0

    async def _delete_orphaned_user_data(self) -> int:
        """
        Delete user-scoped rows whose user_id no longer exists (orphaned).

        Order: UsageRecord, Invoice, Subscription (cancel Stripe first),
        CalendarIntegration (revoke webhook first), KnowledgeBaseFile (blob + Qdrant first).
        """
        try:
            result = await self.session.execute(select(User.id))
            valid_user_ids: Set[str] = {row[0] for row in result.all()}
            if not valid_user_ids:
                return 0

            # Rows where user_id no longer exists
            orphan_usage = await self.session.execute(
                select(UsageRecord.id).where(UsageRecord.user_id.notin_(valid_user_ids))
            )
            usage_ids = [row[0] for row in orphan_usage.all()]
            orphan_invoice = await self.session.execute(
                select(Invoice.id).where(Invoice.user_id.notin_(valid_user_ids))
            )
            invoice_ids = [row[0] for row in orphan_invoice.all()]
            orphan_sub = await self.session.execute(
                select(Subscription).where(Subscription.user_id.notin_(valid_user_ids))
            )
            orphan_subs = list(orphan_sub.scalars().all())
            orphan_cal = await self.session.execute(
                select(CalendarIntegration).where(
                    CalendarIntegration.user_id.notin_(valid_user_ids)
                )
            )
            orphan_cals = list(orphan_cal.scalars().all())
            orphan_kb = await self.session.execute(
                select(KnowledgeBaseFile).where(
                    KnowledgeBaseFile.user_id.notin_(valid_user_ids)
                )
            )
            orphan_kbs = list(orphan_kb.scalars().all())

            total = 0
            if usage_ids:
                await self.session.execute(delete(UsageRecord).where(UsageRecord.id.in_(usage_ids)))
                total += len(usage_ids)
            if invoice_ids:
                await self.session.execute(delete(Invoice).where(Invoice.id.in_(invoice_ids)))
                total += len(invoice_ids)

            for sub in orphan_subs:
                try:
                    from api_core.services.stripe_service import get_stripe_service

                    if sub.payment_provider == "stripe" and sub.payment_provider_subscription_id:
                        stripe_svc = get_stripe_service(self.session)
                        await stripe_svc.cancel_subscription(
                            stripe_subscription_id=sub.payment_provider_subscription_id,
                            cancel_at_period_end=False,
                        )
                except Exception as e:
                    logger.warning(f"Stripe cancel orphan subscription {sub.id}: {e}. Continuing.")
                await self.session.delete(sub)
                total += 1

            for integration in orphan_cals:
                try:
                    from api_core.services.calendar_integration_service import (
                        CalendarIntegrationService,
                    )

                    cal_svc = CalendarIntegrationService(self.session)
                    await cal_svc.delete_outlook_webhook_subscription(integration)
                except Exception as e:
                    logger.warning(
                        f"Calendar webhook delete orphan integration {integration.id}: {e}. Continuing."
                    )
                await self.session.delete(integration)
                total += 1

            storage = None
            for kb in orphan_kbs:
                try:
                    if kb.qdrant_collection and kb.qdrant_point_ids:
                        from api_core.services.qdrant_service import (
                            delete_points as qdrant_delete_points,
                        )

                        try:
                            point_ids = json.loads(kb.qdrant_point_ids)
                            if point_ids:
                                qdrant_delete_points(kb.qdrant_collection, point_ids)
                        except (json.JSONDecodeError, TypeError):
                            pass
                    if kb.storage_path:
                        if storage is None:
                            from api_core.services.storage_service import get_storage_service

                            storage = get_storage_service()
                        try:
                            parts = kb.storage_path.split("/", 1)
                            if len(parts) == 2:
                                await storage.delete_file(parts[0], parts[1])
                        except Exception as e:
                            logger.warning(f"Blob delete orphan file {kb.storage_path}: {e}. Continuing.")
                except Exception as e:
                    logger.warning(f"Orphan KB file cleanup {kb.id}: {e}. Continuing.")
                await self.session.delete(kb)
                total += 1

            if total:
                await self.session.flush()
            return total
        except Exception as e:
            logger.warning(
                f"Orphan user data cleanup failed: {e}. Continuing.",
                exc_info=True,
            )
            return 0
