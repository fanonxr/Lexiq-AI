"""Repository for phone number pool (Twilio number pool for terminate/provision)."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from api_core.database.models import PhoneNumberPool
from api_core.exceptions import ConflictError, DatabaseError, NotFoundError

logger = logging.getLogger(__name__)


class PhoneNumberPoolRepository:
    """Repository for phone number pool records."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_available_for_update(
        self,
        limit: int = 1,
    ) -> list[PhoneNumberPool]:
        """
        Claim an available number from the pool (FOR UPDATE SKIP LOCKED).

        Use in a transaction; call mark_assigned after transferring in Twilio.

        Args:
            limit: Max number of rows to return (default 1).

        Returns:
            List of pool rows (usually one) with status=available.
        """
        try:
            result = await self.session.execute(
                select(PhoneNumberPool)
                .where(PhoneNumberPool.status == "available")
                .with_for_update(skip_locked=True)
                .limit(limit)
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting available pool number: {e}")
            raise DatabaseError("Failed to get available pool number") from e

    async def add_to_pool(
        self,
        phone_number: str,
        twilio_phone_number_sid: str,
        pool_account_sid: str,
    ) -> PhoneNumberPool:
        """
        Add a number to the pool (status=available).

        Idempotent: if a row with this twilio_phone_number_sid exists and is available, no-op.
        If it exists and is assigned, or sid differs, treat as conflict or update.

        Args:
            phone_number: E.164 phone number.
            twilio_phone_number_sid: Twilio Phone Number SID.
            pool_account_sid: Account SID where the number lives in Twilio (pool or main).

        Returns:
            The pool row (existing or newly created).
        """
        try:
            existing = await self._get_by_sid(twilio_phone_number_sid)
            if existing:
                if existing.status == "available":
                    return existing
                # Was assigned; return to pool
                existing.status = "available"
                existing.firm_id = None
                existing.assigned_at = None
                existing.pool_account_sid = pool_account_sid
                await self.session.flush()
                await self.session.refresh(existing)
                logger.info(
                    f"Returned number {phone_number} to pool (sid={twilio_phone_number_sid})"
                )
                return existing
            row = PhoneNumberPool(
                phone_number=phone_number,
                twilio_phone_number_sid=twilio_phone_number_sid,
                pool_account_sid=pool_account_sid,
                status="available",
            )
            self.session.add(row)
            await self.session.flush()
            await self.session.refresh(row)
            logger.info(f"Added number {phone_number} to pool (sid={twilio_phone_number_sid})")
            return row
        except SQLAlchemyError as e:
            logger.error(f"Error adding to pool: {e}")
            raise DatabaseError("Failed to add number to pool") from e

    async def mark_assigned(
        self,
        pool_row_id: str,
        firm_id: str,
    ) -> PhoneNumberPool:
        """Mark a pool row as assigned to a firm."""
        try:
            result = await self.session.execute(
                select(PhoneNumberPool).where(PhoneNumberPool.id == pool_row_id)
            )
            row = result.scalar_one_or_none()
            if not row:
                raise NotFoundError(resource="PhoneNumberPool", resource_id=pool_row_id)
            if row.status != "available":
                raise ConflictError(
                    f"Pool number {row.phone_number} is not available (status={row.status})"
                )
            row.status = "assigned"
            row.firm_id = firm_id
            row.assigned_at = datetime.utcnow()
            await self.session.flush()
            await self.session.refresh(row)
            return row
        except (NotFoundError, ConflictError):
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error marking pool number assigned: {e}")
            raise DatabaseError("Failed to mark pool number assigned") from e

    async def _get_by_sid(self, twilio_phone_number_sid: str) -> Optional[PhoneNumberPool]:
        """Get pool row by Twilio Phone Number SID."""
        try:
            result = await self.session.execute(
                select(PhoneNumberPool).where(
                    PhoneNumberPool.twilio_phone_number_sid == twilio_phone_number_sid
                )
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting pool by SID: {e}")
            raise DatabaseError("Failed to get pool by SID") from e
