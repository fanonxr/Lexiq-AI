"""Firm configuration service (MVP firm personas)."""

from __future__ import annotations

import logging
import os
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api_core.database.models import Appointment, Firm, KnowledgeBaseFile, Lead
from api_core.exceptions import (
    AuthorizationError,
    ExternalServiceError,
    NotFoundError,
    ValidationError,
)
from api_core.models.firms import (
    FirmPersonaResponse,
    FirmPhoneNumberResponse,
    FirmSettingsResponse,
)
from api_core.repositories.firms_repository import FirmsRepository
from api_core.repositories.phone_number_pool_repository import PhoneNumberPoolRepository

logger = logging.getLogger(__name__)


class FirmsService:
    """Service for firm persona operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = FirmsRepository(session)
        self._pool_repo = PhoneNumberPoolRepository(session)
        self.session = session

    async def check_user_firm_access(self, user_id: str, firm_id: str) -> bool:
        """
        Check if a user has access to a firm by verifying they have resources for that firm.
        
        A user has access if they have:
        - User's firm_id matches the requested firm_id
        - Knowledge base files for the firm
        - Appointments for the firm
        - Leads for the firm
        - Or if firm_id == user_id (simple MVP: user is their own firm)
        - Or if firm_id is the user's own malformed ID (handle legacy cases)
        """
        logger.debug(
            f"[check_user_firm_access] Checking access: user_id={user_id}, firm_id={firm_id}, "
            f"user_id type={type(user_id)}, firm_id type={type(firm_id)}"
        )
        
        # Simple MVP: user is their own firm
        if firm_id == user_id:
            logger.debug(f"User {user_id} has access to firm {firm_id} (firm_id == user_id)")
            return True

        # Check if user's firm_id matches the requested firm_id
        from api_core.database.models import User
        # Try to find user by ID first, then by Azure AD object ID (in case user_id is Azure AD object ID)
        user_result = await self.session.execute(
            select(User.id, User.firm_id, User.azure_ad_object_id).where(
                (User.id == user_id) | (User.azure_ad_object_id == user_id)
            ).limit(1)
        )
        user_row = user_result.first()
        
        if user_row:
            db_user_id, user_firm_id, user_azure_ad_id = user_row
            logger.debug(
                f"User {user_id} firm_id check: db_user_id={db_user_id}, user_firm_id={user_firm_id}, "
                f"user_azure_ad_id={user_azure_ad_id}, requested firm_id={firm_id}, "
                f"match={user_firm_id == firm_id if user_firm_id else False}"
            )
            
            # Check if user's firm_id matches
            if user_firm_id and user_firm_id == firm_id:
                logger.debug(f"User {user_id} has access to firm {firm_id} (user.firm_id matches)")
                return True
            
            # Check if firm_id is the user's own ID (even if malformed)
            # This handles cases where frontend is using user.id as firm_id
            if firm_id == db_user_id:
                logger.debug(f"User {user_id} has access to firm {firm_id} (firm_id == db_user.id)")
                return True
        
        # If firm_id doesn't match user_id, check if firm_id is actually a user ID
        # (This handles cases where frontend sends user.id as firm_id but user_id from token is different)
        # This can happen when Azure AD object ID is used as user_id in token but database has different ID
        firm_as_user_result = await self.session.execute(
            select(User.id, User.firm_id, User.azure_ad_object_id).where(
                (User.id == firm_id) | (User.azure_ad_object_id == firm_id)
            ).limit(1)
        )
        firm_as_user_row = firm_as_user_result.first()
        if firm_as_user_row:
            firm_user_id, firm_user_firm_id, firm_user_azure_id = firm_as_user_row
            # If the firm_id matches a user ID, check if:
            # 1. The requesting user_id matches that user_id (user accessing their own "firm")
            # 2. The requesting user_id matches the user's Azure AD object ID
            # 3. Or the requesting user's firm_id matches the firm_user's firm_id (same firm)
            if firm_user_id == user_id:
                logger.debug(f"User {user_id} has access to firm {firm_id} (firm_id is user's own database ID)")
                return True
            if firm_user_azure_id and firm_user_azure_id == user_id:
                logger.debug(f"User {user_id} has access to firm {firm_id} (firm_id matches user's Azure AD ID)")
                return True
            # Check if the requesting user's Azure AD ID matches the firm_user's database ID
            if user_row and user_row[2] and user_row[2] == firm_user_id:
                logger.debug(f"User {user_id} has access to firm {firm_id} (token user_id matches firm_user's Azure AD ID)")
                return True
            # Check if the requesting user's database ID matches the firm_user's Azure AD ID
            if user_row and user_row[0] and firm_user_azure_id and user_row[0] == firm_user_azure_id:
                logger.debug(f"User {user_id} has access to firm {firm_id} (requesting user's DB ID matches firm_user's Azure AD ID)")
                return True
            # Most important: if firm_id is a user ID and the requesting user_id (Azure AD) matches that user's Azure AD ID
            if firm_user_azure_id and firm_user_azure_id == user_id:
                logger.debug(f"User {user_id} has access to firm {firm_id} (firm_id user's Azure AD ID matches token user_id)")
                return True
            if user_row and user_row[1] and firm_user_firm_id and user_row[1] == firm_user_firm_id:
                logger.debug(f"User {user_id} has access to firm {firm_id} (same firm_id)")
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
            logger.debug(f"User {user_id} has access to firm {firm_id} (has knowledge base files)")
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
            logger.debug(f"User {user_id} has access to firm {firm_id} (has leads)")
            return True

        logger.debug(f"User {user_id} does NOT have access to firm {firm_id} (all checks failed)")
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

    async def provision_phone_number(
        self,
        firm_id: str,
        area_code: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> FirmPhoneNumberResponse:
        """
        Provision a new Twilio phone number for a firm.
        
        This method:
        1. Creates or gets subaccount for firm
        2. Searches for available Twilio numbers (optionally by area code)
        3. Purchases the number via Twilio API
        4. Configures webhook automatically
        5. Stores number in database
        
        Args:
            firm_id: Firm ID
            area_code: Optional preferred area code (e.g., '415', '212')
            user_id: User ID for authorization check
            
        Returns:
            FirmPhoneNumberResponse with phone number details
            
        Raises:
            ValidationError: If firm_id is invalid or firm already has a number
            AuthorizationError: If user doesn't have access
            NotFoundError: If firm not found
            ExternalServiceError: If Twilio API fails
        """
        if not firm_id or not firm_id.strip():
            raise ValidationError("firm_id is required")

        # Check authorization
        if user_id is not None:
            has_access = await self.check_user_firm_access(user_id, firm_id)
            if not has_access:
                # Special case: if user doesn't have a firm_id, create one for them
                from api_core.database.models import User
                user_result = await self.session.execute(
                    select(User.id, User.firm_id, User.azure_ad_object_id).where(
                        (User.id == user_id) | (User.azure_ad_object_id == user_id)
                    ).limit(1)
                )
                user_row = user_result.first()
                
                if user_row:
                    db_user_id, user_firm_id, user_azure_ad_id = user_row
                    # If user doesn't have a firm_id, create one for them
                    if not user_firm_id:
                        logger.info(
                            f"[provision_phone_number] User {user_id} doesn't have firm_id, creating firm. "
                            f"db_user_id={db_user_id}, requested firm_id={firm_id}"
                        )
                        # Create a firm for the user
                        firm = await self._repo.create(
                            name=f"User {db_user_id}'s Firm",
                        )
                        # Update user with firm_id
                        user = await self.session.get(User, db_user_id)
                        if user:
                            user.firm_id = firm.id
                            await self.session.flush()
                            await self.session.refresh(user)
                            logger.info(f"Created firm {firm.id} for user {db_user_id}")
                            # Use the new firm_id instead of the requested one
                            firm_id = firm.id
                        else:
                            raise AuthorizationError(
                                f"User {user_id} does not have access to firm {firm_id}"
                            )
                    else:
                        # User has a firm_id but authorization failed - this is a real authorization error
                        raise AuthorizationError(
                            f"User {user_id} does not have access to firm {firm_id}"
                        )
                else:
                    raise AuthorizationError(
                        f"User {user_id} does not have access to firm {firm_id}"
                    )

        # Get firm
        firm = await self._repo.get_by_id(firm_id)
        if not firm:
            raise NotFoundError(resource="Firm", resource_id=firm_id)

        # If firm already has a phone number in database, return it
        if firm.twilio_phone_number and firm.twilio_phone_number_sid:
            logger.info(
                f"Firm {firm_id} already has phone number: {firm.twilio_phone_number}"
            )
            return FirmPhoneNumberResponse.from_phone_number(
                firm_id=firm.id,
                phone_number=firm.twilio_phone_number,
                twilio_phone_number_sid=firm.twilio_phone_number_sid,
                twilio_subaccount_sid=firm.twilio_subaccount_sid,
            )

        # Provision number via Twilio
        try:
            from api_core.services.twilio_service import get_twilio_service

            twilio_service = get_twilio_service()

            # Get or create subaccount for firm
            subaccount_sid = firm.twilio_subaccount_sid
            subaccount_friendly_name = f"Firm: {firm.name} ({firm_id})"

            if not subaccount_sid:
                # Try to find existing subaccount by name (in case it was created but SID wasn't saved)
                logger.info(
                    f"No subaccount SID found for firm {firm_id}. "
                    f"Searching for existing subaccount: {subaccount_friendly_name}"
                )
                existing_subaccount = await twilio_service.find_subaccount_by_name(
                    subaccount_friendly_name
                )

                if existing_subaccount:
                    logger.info(
                        f"Found existing subaccount: {existing_subaccount.sid} for firm {firm_id}"
                    )
                    subaccount_sid = existing_subaccount.sid
                    # Update firm with found subaccount SID
                    firm = await self._repo.update_firm_subaccount_sid(
                        firm_id, subaccount_sid
                    )
                else:
                    # Try to create new subaccount
                    try:
                        logger.info(
                            f"Creating new subaccount for firm {firm_id}: {subaccount_friendly_name}"
                        )
                        subaccount = await twilio_service.create_subaccount(
                            friendly_name=subaccount_friendly_name
                        )
                        subaccount_sid = subaccount.sid
                        # Update firm with new subaccount SID
                        firm = await self._repo.update_firm_subaccount_sid(
                            firm_id, subaccount_sid
                        )
                    except ExternalServiceError as e:
                        # If creation failed due to max subaccounts, try to find it again
                        # (create_subaccount should have already tried this, but just in case)
                        error_str = str(e.details) if isinstance(e.details, dict) else str(e.details)
                        if "maximum number of subaccounts" in error_str.lower():
                            logger.warning(
                                f"Subaccount creation failed due to max limit. "
                                f"Trying to find existing subaccount again (more flexible search)."
                            )
                            # Try more flexible search - just get the first/only subaccount
                            all_subaccounts = await twilio_service.list_subaccounts()
                            if all_subaccounts:
                                # Use the first subaccount (or only one if trial account)
                                existing_subaccount = all_subaccounts[0]
                                logger.info(
                                    f"Using existing subaccount (found {len(all_subaccounts)} total): "
                                    f"{existing_subaccount.friendly_name} ({existing_subaccount.sid})"
                                )
                                subaccount_sid = existing_subaccount.sid
                                firm = await self._repo.update_firm_subaccount_sid(
                                    firm_id, subaccount_sid
                                )
                            else:
                                raise
                        else:
                            raise

            # Get subaccount auth token for provisioning
            subaccount_auth_token = await twilio_service.get_subaccount_auth_token(
                subaccount_sid
            )

            # Get webhook URL from environment variable (for both existing and new numbers)
            # For development, use a public URL (e.g., ngrok) or leave None
            # Twilio requires publicly accessible URLs - localhost won't work
            api_base_url = os.getenv("API_BASE_URL")
            webhook_url = None
            if api_base_url:
                # Only use webhook URL if it's publicly accessible
                if not any(
                    host in api_base_url.lower()
                    for host in ["localhost", "127.0.0.1", "0.0.0.0", "::1"]
                ):
                    webhook_url = f"{api_base_url}/api/v1/twilio/webhook"
                else:
                    logger.warning(
                        f"API_BASE_URL is set to localhost ({api_base_url}). "
                        "Twilio requires publicly accessible URLs for webhooks. "
                        "Webhook will not be configured automatically. "
                        "Configure it manually in Twilio console or use a public URL (e.g., ngrok)."
                    )

            # Try pool first (production best practice: assign from pool before buying new)
            available_from_pool = await self._pool_repo.get_available_for_update(limit=1)
            if available_from_pool:
                pool_row = available_from_pool[0]
                try:
                    await twilio_service.transfer_phone_number_to_account(
                        phone_number_sid=pool_row.twilio_phone_number_sid,
                        source_account_sid=pool_row.pool_account_sid,
                        target_account_sid=subaccount_sid,
                    )
                    firm = await self._repo.set_phone_number(
                        firm_id,
                        pool_row.phone_number,
                        pool_row.twilio_phone_number_sid,
                        subaccount_sid,
                    )
                    await self._pool_repo.mark_assigned(pool_row.id, firm_id)
                    if webhook_url:
                        try:
                            await twilio_service.update_phone_number_webhook(
                                phone_number_sid=pool_row.twilio_phone_number_sid,
                                webhook_url=webhook_url,
                                account_sid=subaccount_sid,
                                auth_token=subaccount_auth_token,
                            )
                        except Exception as e:
                            logger.warning(
                                f"Could not configure webhook for pooled number: {e}"
                            )
                    logger.info(
                        f"Assigned number {pool_row.phone_number} from pool to firm {firm_id}"
                    )
                    return FirmPhoneNumberResponse.from_phone_number(
                        firm_id=firm.id,
                        phone_number=firm.twilio_phone_number,
                        twilio_phone_number_sid=firm.twilio_phone_number_sid,
                        twilio_subaccount_sid=firm.twilio_subaccount_sid,
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to assign from pool for firm {firm_id}: {e}. Falling back to purchase."
                    )
                    # Fall through to existing-numbers / purchase flow

            # Check if subaccount already has a phone number
            logger.info(
                f"Checking for existing phone numbers in subaccount {subaccount_sid}"
            )
            existing_numbers = await twilio_service.list_phone_numbers(
                account_sid=subaccount_sid, auth_token=subaccount_auth_token
            )

            if existing_numbers:
                # Use the first existing number
                logger.info(
                    f"Found existing phone number in subaccount: {existing_numbers[0].phone_number}"
                )
                twilio_number = existing_numbers[0]
            else:
                # No existing number, purchase a new one
                logger.info(
                    f"No existing phone number found. Purchasing new number for subaccount {subaccount_sid}"
                )

                # Purchase new number in subaccount
                twilio_number = await twilio_service.provision_phone_number(
                    area_code=area_code,
                    webhook_url=webhook_url,  # Will be None if localhost
                    account_sid=subaccount_sid,  # Use subaccount SID for provisioning
                    auth_token=subaccount_auth_token,  # Use subaccount auth token
                )

            if webhook_url and twilio_number.sid:
                try:
                    await twilio_service.update_phone_number_webhook(
                        phone_number_sid=twilio_number.sid,
                        webhook_url=webhook_url,
                        account_sid=subaccount_sid,
                        auth_token=subaccount_auth_token,
                    )
                    logger.info(
                        f"Configured webhook URL for phone number {twilio_number.phone_number}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Could not configure webhook URL: {e}. "
                        "Please configure it manually in Twilio console."
                    )

            # Store in database
            firm = await self._repo.set_phone_number(
                firm_id,
                twilio_number.phone_number,
                twilio_number.sid,
                subaccount_sid,
            )

            # Use the helper method from FirmPhoneNumberResponse
            return FirmPhoneNumberResponse.from_phone_number(
                firm_id=firm.id,
                phone_number=firm.twilio_phone_number,
                twilio_phone_number_sid=firm.twilio_phone_number_sid,
                twilio_subaccount_sid=firm.twilio_subaccount_sid,
            )

        except (ValidationError, AuthorizationError, NotFoundError):
            raise
        except Exception as e:
            logger.error(f"Failed to provision phone number for firm {firm_id}: {e}", exc_info=True)
            error_details = {"error": str(e)}
            if hasattr(e, "status_code"):
                error_details["status_code"] = e.status_code
            if hasattr(e, "code"):
                error_details["code"] = e.code
            raise ExternalServiceError(
                message="Failed to provision phone number",
                service="Twilio",
                details=error_details,
            ) from e

    async def get_firm_phone_number(
        self, firm_id: str, user_id: Optional[str] = None
    ) -> FirmPhoneNumberResponse:
        """
        Get firm's Twilio phone number.
        
        Args:
            firm_id: Firm ID
            user_id: User ID for authorization check
            
        Returns:
            FirmPhoneNumberResponse with phone number details
            
        Raises:
            ValidationError: If firm_id is invalid
            AuthorizationError: If user doesn't have access
            NotFoundError: If firm not found
        """
        if not firm_id or not firm_id.strip():
            raise ValidationError("firm_id is required")

        # First, ensure user has a firm_id (create one if they don't)
        # This happens BEFORE authorization check to ensure user always has a firm_id
        if user_id is not None:
            from api_core.database.models import User
            user_result = await self.session.execute(
                select(User.id, User.firm_id, User.azure_ad_object_id).where(
                    (User.id == user_id) | (User.azure_ad_object_id == user_id)
                ).limit(1)
            )
            user_row = user_result.first()
            
            if user_row:
                db_user_id, user_firm_id, user_azure_ad_id = user_row
                # If user doesn't have a firm_id, create one for them
                if not user_firm_id:
                    logger.info(
                        f"[get_firm_phone_number] User {user_id} doesn't have firm_id, creating firm. "
                        f"db_user_id={db_user_id}, requested firm_id={firm_id}"
                    )
                    try:
                        # Create a firm for the user
                        firm = await self._repo.create(
                            name=f"User {db_user_id}'s Firm",
                        )
                        # Update user with firm_id
                        user = await self.session.get(User, db_user_id)
                        if user:
                            user.firm_id = firm.id
                            await self.session.flush()
                            await self.session.refresh(user)
                            logger.info(f"[get_firm_phone_number] Created firm {firm.id} for user {db_user_id}")
                            # If the requested firm_id was the user's own ID (any form), use the new firm_id
                            if firm_id == db_user_id or (user_azure_ad_id and firm_id == user_azure_ad_id):
                                firm_id = firm.id
                                logger.info(f"[get_firm_phone_number] Using new firm_id: {firm_id} (was user's own ID)")
                        else:
                            logger.error(f"[get_firm_phone_number] Could not find user {db_user_id} after creating firm")
                    except Exception as e:
                        logger.error(f"[get_firm_phone_number] Error creating firm for user: {e}", exc_info=True)
                        # Continue with authorization check - might still work if firm_id matches

        # Check authorization
        if user_id is not None:
            has_access = await self.check_user_firm_access(user_id, firm_id)
            logger.debug(
                f"[get_firm_phone_number] Authorization check result: has_access={has_access}, "
                f"user_id={user_id}, firm_id={firm_id}"
            )
            if not has_access:
                # Special case: if user doesn't have a firm_id and firm_id looks like a user ID,
                # create a firm for them and allow access
                from api_core.database.models import User
                logger.info(
                    f"[get_firm_phone_number] Authorization failed, checking if user needs firm created. "
                    f"user_id={user_id}, firm_id={firm_id}"
                )
                user_result = await self.session.execute(
                    select(User.id, User.firm_id, User.azure_ad_object_id).where(
                        (User.id == user_id) | (User.azure_ad_object_id == user_id)
                    ).limit(1)
                )
                user_row = user_result.first()
                
                if user_row:
                    db_user_id, user_firm_id, user_azure_ad_id = user_row
                    logger.debug(
                        f"[get_firm_phone_number] Found user: db_user_id={db_user_id}, "
                        f"user_firm_id={user_firm_id}, user_azure_ad_id={user_azure_ad_id}"
                    )
                    # If user doesn't have a firm_id, create one for them
                    if not user_firm_id:
                        logger.info(
                            f"[get_firm_phone_number] User {user_id} doesn't have firm_id, creating firm. "
                            f"db_user_id={db_user_id}, requested firm_id={firm_id}"
                        )
                        try:
                            # Create a firm for the user
                            firm = await self._repo.create(
                                name=f"User {db_user_id}'s Firm",
                            )
                            # Update user with firm_id
                            user = await self.session.get(User, db_user_id)
                            if user:
                                user.firm_id = firm.id
                                await self.session.flush()
                                await self.session.refresh(user)
                                logger.info(f"[get_firm_phone_number] Created firm {firm.id} for user {db_user_id}")
                                # Use the new firm_id instead of the requested one
                                firm_id = firm.id
                                logger.info(f"[get_firm_phone_number] Using new firm_id: {firm_id}")
                            else:
                                logger.error(f"[get_firm_phone_number] Could not find user {db_user_id} after creating firm")
                                raise AuthorizationError(
                                    f"User {user_id} does not have access to firm {firm_id}"
                                )
                        except Exception as e:
                            logger.error(f"[get_firm_phone_number] Error creating firm for user: {e}", exc_info=True)
                            raise AuthorizationError(
                                f"User {user_id} does not have access to firm {firm_id}"
                            ) from e
                    else:
                        # User has a firm_id but authorization failed - this is a real authorization error
                        logger.warning(
                            f"[get_firm_phone_number] User {user_id} has firm_id {user_firm_id} but "
                            f"authorization failed for firm_id {firm_id}"
                        )
                        raise AuthorizationError(
                            f"User {user_id} does not have access to firm {firm_id}"
                        )
                else:
                    logger.error(f"[get_firm_phone_number] Could not find user with user_id={user_id}")
                    raise AuthorizationError(
                        f"User {user_id} does not have access to firm {firm_id}"
                    )

        firm = await self._repo.get_by_id(firm_id)
        if not firm:
            raise NotFoundError(resource="Firm", resource_id=firm_id)

        # Return response using helper method
        if firm.twilio_phone_number:
            return FirmPhoneNumberResponse.from_phone_number(
                firm_id=firm.id,
                phone_number=firm.twilio_phone_number,
                twilio_phone_number_sid=firm.twilio_phone_number_sid or "",
                twilio_subaccount_sid=firm.twilio_subaccount_sid or "",
            )
        else:
            # Return empty response if no phone number
            return FirmPhoneNumberResponse(
                firm_id=firm.id,
                phone_number="",
                twilio_phone_number_sid="",
                twilio_subaccount_sid="",
                formatted_phone_number="",
                area_code=None,
            )

    async def get_firm_by_phone_number(
        self, phone_number: str
    ) -> Optional[Firm]:
        """
        Get firm by Twilio phone number (for webhook lookups).
        
        Args:
            phone_number: Phone number in E.164 format
            
        Returns:
            Firm instance or None if not found
        """
        return await self._repo.get_firm_by_phone_number(phone_number)

    async def release_phone_number(
        self,
        firm_id: str,
        user_id: Optional[str] = None,
        release_from_twilio: bool = True,
    ) -> None:
        """
        Release (delete) a firm's phone number.
        
        This method:
        1. Releases the phone number from Twilio (if release_from_twilio=True)
        2. Clears the phone number fields from the database
        3. Keeps the subaccount SID (in case firm wants to provision a new number later)
        
        Args:
            firm_id: Firm ID
            user_id: User ID for authorization (optional, but recommended)
            release_from_twilio: If True, release the number from Twilio. If False, only clear from database.
            
        Raises:
            NotFoundError: If firm not found or firm has no phone number
            AuthorizationError: If user is not authorized
            ExternalServiceError: If Twilio API fails
        """
        # Get firm
        firm = await self._repo.get_by_id(firm_id)
        if not firm:
            raise NotFoundError(resource="Firm", resource_id=firm_id)

        # Check if firm has a phone number
        if not firm.twilio_phone_number_sid:
            logger.info(f"Firm {firm_id} has no phone number to release")
            return

        # Authorization check (if user_id provided)
        if user_id:
            has_access = await self.check_user_firm_access(user_id, firm_id)
            if not has_access:
                raise AuthorizationError(
                    f"User {user_id} does not have access to firm {firm_id}"
                )

        # Get Twilio service
        from api_core.services.twilio_service import get_twilio_service

        twilio_service = get_twilio_service()

        # Release from Twilio if requested
        if release_from_twilio:
            try:
                # Get subaccount auth token if we have a subaccount
                account_sid = None
                auth_token = None
                
                if firm.twilio_subaccount_sid:
                    try:
                        account_sid = firm.twilio_subaccount_sid
                        auth_token = await twilio_service.get_subaccount_auth_token(
                            firm.twilio_subaccount_sid
                        )
                        logger.info(
                            f"Releasing phone number from subaccount: {firm.twilio_subaccount_sid}"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Could not get subaccount auth token: {e}. "
                            f"Attempting to release from main account."
                        )
                        # Fall back to main account

                # Release the phone number from Twilio
                await twilio_service.release_phone_number(
                    phone_number_sid=firm.twilio_phone_number_sid,
                    account_sid=account_sid,
                    auth_token=auth_token,
                )
                logger.info(
                    f"Successfully released phone number {firm.twilio_phone_number} "
                    f"({firm.twilio_phone_number_sid}) from Twilio"
                )
            except NotFoundError:
                # Number already released or not found - that's okay, continue
                logger.info(
                    f"Phone number {firm.twilio_phone_number_sid} not found in Twilio. "
                    f"May have already been released."
                )
            except ExternalServiceError as e:
                logger.error(
                    f"Error releasing phone number from Twilio: {e}. "
                    f"Continuing to clear database fields."
                )
                # Continue to clear database even if Twilio release fails
                # This ensures database consistency

        # Clear phone number fields from database
        await self._repo.clear_phone_number(firm_id)
        logger.info(f"Cleared phone number fields for firm: {firm_id}")

        # Note: We intentionally keep twilio_subaccount_sid in case the firm
        # wants to provision a new number later using the same subaccount


def get_firms_service(session: AsyncSession) -> FirmsService:
    return FirmsService(session=session)


