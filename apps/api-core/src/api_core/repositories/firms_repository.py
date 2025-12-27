"""Firm configuration repository (MVP firm personas)."""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from api_core.database.models import Firm, FirmPersona
from api_core.exceptions import ConflictError, DatabaseError, NotFoundError

logger = logging.getLogger(__name__)


class FirmsRepository:
    """Repository for firm persona records."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, firm_id: str) -> Optional[Firm]:
        """
        Get firm by ID.
        
        Args:
            firm_id: Firm ID
            
        Returns:
            Firm instance or None if not found
        """
        try:
            result = await self.session.execute(
                select(Firm).where(Firm.id == firm_id)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting firm by ID: {e}")
            raise DatabaseError("Failed to retrieve firm") from e

    async def get_firm_by_phone_number(
        self, phone_number: str
    ) -> Optional[Firm]:
        """
        Get firm by Twilio phone number.
        
        Args:
            phone_number: Phone number in E.164 format
            
        Returns:
            Firm instance or None if not found
        """
        try:
            result = await self.session.execute(
                select(Firm).where(Firm.twilio_phone_number == phone_number)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting firm by phone number: {e}")
            raise DatabaseError("Failed to retrieve firm by phone number") from e

    async def set_phone_number(
        self,
        firm_id: str,
        phone_number: str,
        twilio_phone_number_sid: str,
        twilio_subaccount_sid: str,
    ) -> Firm:
        """
        Set firm's Twilio phone number and subaccount.
        
        Args:
            firm_id: Firm ID
            phone_number: Phone number in E.164 format
            twilio_phone_number_sid: Twilio Phone Number SID
            twilio_subaccount_sid: Twilio Subaccount SID
            
        Returns:
            Updated Firm instance
            
        Raises:
            NotFoundError: If firm not found
            ConflictError: If phone number already assigned to another firm
        """
        try:
            firm = await self.get_by_id(firm_id)
            if not firm:
                raise NotFoundError(resource="Firm", resource_id=firm_id)

            # Check if phone number is already assigned to another firm
            existing = await self.get_firm_by_phone_number(phone_number)
            if existing and existing.id != firm_id:
                raise ConflictError(
                    f"Phone number {phone_number} is already assigned to firm {existing.id}"
                )

            firm.twilio_phone_number = phone_number
            firm.twilio_phone_number_sid = twilio_phone_number_sid
            firm.twilio_subaccount_sid = twilio_subaccount_sid

            await self.session.flush()
            await self.session.refresh(firm)

            return firm
        except (NotFoundError, ConflictError):
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error setting phone number: {e}")
            raise DatabaseError("Failed to set phone number") from e

    async def update_firm_subaccount_sid(
        self, firm_id: str, twilio_subaccount_sid: str
    ) -> Firm:
        """
        Update firm's Twilio subaccount SID.
        
        Args:
            firm_id: Firm ID
            twilio_subaccount_sid: Twilio Subaccount SID
            
        Returns:
            Updated Firm instance
            
        Raises:
            NotFoundError: If firm not found
        """
        try:
            firm = await self.get_by_id(firm_id)
            if not firm:
                raise NotFoundError(resource="Firm", resource_id=firm_id)

            firm.twilio_subaccount_sid = twilio_subaccount_sid

            await self.session.flush()
            await self.session.refresh(firm)

            return firm
        except NotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error updating firm subaccount SID: {e}")
            raise DatabaseError("Failed to update firm subaccount SID") from e

    async def clear_phone_number(self, firm_id: str) -> Firm:
        """
        Clear firm's Twilio phone number and related fields.
        
        This removes the phone number association from the database but does NOT
        release the number from Twilio. Use FirmsService.release_phone_number()
        to also release the number from Twilio.
        
        Args:
            firm_id: Firm ID
            
        Returns:
            Updated Firm instance with phone number fields cleared
            
        Raises:
            NotFoundError: If firm not found
        """
        try:
            firm = await self.get_by_id(firm_id)
            if not firm:
                raise NotFoundError(resource="Firm", resource_id=firm_id)

            # Clear phone number fields
            firm.twilio_phone_number = None
            firm.twilio_phone_number_sid = None
            # Note: We keep twilio_subaccount_sid in case the firm wants to provision
            # a new number later using the same subaccount

            await self.session.flush()
            await self.session.refresh(firm)

            logger.info(f"Cleared phone number for firm: {firm_id}")
            return firm
        except NotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error clearing phone number: {e}")
            raise DatabaseError("Failed to clear phone number") from e

    async def get_persona(self, firm_id: str) -> Optional[FirmPersona]:
        try:
            result = await self.session.execute(
                select(FirmPersona).where(FirmPersona.firm_id == firm_id)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting firm persona: {e}")
            raise DatabaseError("Failed to retrieve firm persona") from e

    async def create(self, name: str, **kwargs) -> Firm:
        """
        Create a new firm.
        
        Args:
            name: Firm name
            **kwargs: Additional firm fields
            
        Returns:
            Created Firm instance
        """
        try:
            firm = Firm(name=name, **kwargs)
            self.session.add(firm)
            await self.session.flush()
            await self.session.refresh(firm)
            logger.info(f"Created firm: {firm.id} ({firm.name})")
            return firm
        except SQLAlchemyError as e:
            logger.error(f"Error creating firm: {e}")
            await self.session.rollback()
            raise DatabaseError("Failed to create firm") from e

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


