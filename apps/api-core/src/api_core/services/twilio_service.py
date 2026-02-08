"""Twilio API service for phone number validation and management."""

from __future__ import annotations

import logging
import os
from typing import Optional

from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from api_core.exceptions import ExternalServiceError, NotFoundError

logger = logging.getLogger(__name__)


class TwilioPhoneNumber:
    """Represents a Twilio phone number."""

    def __init__(self, sid: str, phone_number: str, status: str):
        self.sid = sid
        self.phone_number = phone_number
        self.status = status


class TwilioSubaccount:
    """Represents a Twilio subaccount."""

    def __init__(self, sid: str, friendly_name: str, status: str):
        self.sid = sid
        self.friendly_name = friendly_name
        self.status = status


class TwilioService:
    """Service for interacting with Twilio API."""

    def __init__(self):
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")

        if not account_sid or not auth_token:
            logger.warning(
                "Twilio credentials not configured. Twilio features will be disabled."
            )
            self.client = None
            self.main_account_sid = None
        else:
            # Validate Account SID format (should start with "AC")
            if not account_sid.startswith("AC"):
                logger.warning(
                    f"TWILIO_ACCOUNT_SID does not start with 'AC'. "
                    f"Account SIDs start with 'AC', API Key SIDs start with 'SK'. "
                    f"Got: {account_sid[:3]}..."
                )
            self.client = Client(account_sid, auth_token)
            self.main_account_sid = account_sid

    async def create_subaccount(self, friendly_name: str) -> TwilioSubaccount:
        """
        Create a new Twilio subaccount for a firm.
        
        Args:
            friendly_name: Friendly name for the subaccount (e.g., "Firm: ABC Law")
            
        Returns:
            TwilioSubaccount object with subaccount details
            
        Raises:
            ExternalServiceError: If Twilio API fails
        """
        if not self.client:
            raise ValueError("Twilio client not configured.")
            
        try:
            subaccount = self.client.api.accounts.create(friendly_name=friendly_name)

            return TwilioSubaccount(
                sid=subaccount.sid,
                friendly_name=subaccount.friendly_name,
                status=subaccount.status,
            )
        except TwilioRestException as e:
            # Handle "max subaccounts" error gracefully - try to find existing subaccount
            if e.status == 400 and "maximum number of subaccounts" in str(e).lower():
                logger.warning(
                    f"Reached maximum number of subaccounts. "
                    f"Attempting to find existing subaccount with name: {friendly_name}"
                )
                # Try to find existing subaccount by name
                existing = await self.find_subaccount_by_name(friendly_name)
                if existing:
                    logger.info(
                        f"Found existing subaccount: {existing.sid} for {friendly_name}"
                    )
                    return existing
                # If not found, re-raise the error
                logger.error(
                    f"Maximum subaccounts reached and no existing subaccount found with name: {friendly_name}"
                )
            logger.error(f"Twilio API error creating subaccount: {e}")
            raise ExternalServiceError(
                message="Failed to create Twilio subaccount",
                service="Twilio",
                details={"error": str(e), "status_code": e.status, "code": e.code},
            ) from e

    async def list_subaccounts(self) -> list[TwilioSubaccount]:
        """
        List all subaccounts in Twilio account.
        
        Returns:
            List of TwilioSubaccount objects
            
        Raises:
            ExternalServiceError: If Twilio API fails
        """
        if not self.client:
            raise ValueError("Twilio client not configured.")

        try:
            # List all accounts (subaccounts are accounts with parent_account_sid set)
            accounts = self.client.api.accounts.list()
            subaccounts = [
                TwilioSubaccount(
                    sid=acc.sid,
                    friendly_name=acc.friendly_name,
                    status=acc.status,
                )
                for acc in accounts
                if acc.sid != self.main_account_sid  # Exclude main account
            ]
            return subaccounts
        except TwilioRestException as e:
            logger.error(f"Twilio API error listing subaccounts: {e}")
            raise ExternalServiceError(
                message="Failed to list subaccounts",
                service="Twilio",
                details={"error": str(e), "status_code": e.status, "code": e.code},
            ) from e

    async def find_subaccount_by_name(
        self, friendly_name: str
    ) -> Optional[TwilioSubaccount]:
        """
        Find a subaccount by friendly name (exact or partial match).
        
        Args:
            friendly_name: Friendly name to search for
            
        Returns:
            TwilioSubaccount if found, None otherwise
        """
        try:
            subaccounts = await self.list_subaccounts()
            if not subaccounts:
                logger.info("No subaccounts found")
                return None
            
            # Try exact match first
            for subaccount in subaccounts:
                if subaccount.friendly_name == friendly_name:
                    logger.info(f"Found exact match: {subaccount.friendly_name} ({subaccount.sid})")
                    return subaccount
            
            # Try partial match (in case name changed slightly)
            # Extract firm ID from friendly_name if present
            firm_id_in_name = None
            if "(" in friendly_name and ")" in friendly_name:
                try:
                    firm_id_in_name = friendly_name.split("(")[1].split(")")[0]
                except:
                    pass
            
            for subaccount in subaccounts:
                # Check if firm ID matches (if present in both names)
                if firm_id_in_name and firm_id_in_name in subaccount.friendly_name:
                    logger.info(
                        f"Found partial match by firm ID: {subaccount.friendly_name} ({subaccount.sid})"
                    )
                    return subaccount
                
                # Check if subaccount name contains key parts of the search name
                # (e.g., "Firm:" prefix and firm name)
                if "Firm:" in friendly_name and "Firm:" in subaccount.friendly_name:
                    # Extract firm name part (after "Firm: ")
                    search_firm_part = friendly_name.split("Firm: ")[-1].split(" (")[0].lower()
                    account_firm_part = subaccount.friendly_name.split("Firm: ")[-1].split(" (")[0].lower()
                    if search_firm_part in account_firm_part or account_firm_part in search_firm_part:
                        logger.info(
                            f"Found partial match by firm name: {subaccount.friendly_name} ({subaccount.sid})"
                        )
                        return subaccount
            
            # If only one subaccount exists and we're on trial (max 1), use it
            if len(subaccounts) == 1:
                logger.info(
                    f"Only one subaccount exists, using it: {subaccounts[0].friendly_name} ({subaccounts[0].sid})"
                )
                return subaccounts[0]
            
            logger.warning(
                f"No matching subaccount found. Searched for: {friendly_name}, "
                f"Found {len(subaccounts)} subaccounts: {[s.friendly_name for s in subaccounts]}"
            )
            return None
        except Exception as e:
            logger.warning(f"Error finding subaccount by name: {e}")
            return None

    async def get_subaccount(self, subaccount_sid: str) -> TwilioSubaccount:
        """
        Get subaccount details from Twilio.
        
        Args:
            subaccount_sid: Twilio Subaccount SID
            
        Returns:
            TwilioSubaccount object
            
        Raises:
            NotFoundError: If subaccount not found
            ExternalServiceError: If Twilio API fails
        """
        if not self.client:
            raise ValueError("Twilio client not configured.")

        try:
            subaccount = self.client.api.accounts(subaccount_sid).fetch()

            return TwilioSubaccount(
                sid=subaccount.sid,
                friendly_name=subaccount.friendly_name,
                status=subaccount.status,
            )
        except TwilioRestException as e:
            if e.status == 404:
                raise NotFoundError(
                    resource="TwilioSubaccount",
                    resource_id=subaccount_sid,
                )
            logger.error(f"Twilio API error getting subaccount: {e}")
            raise ExternalServiceError(
                message="Failed to get Twilio subaccount",
                service="Twilio",
                details={"error": str(e), "status_code": e.status, "code": e.code},
            ) from e

    async def get_subaccount_auth_token(self, subaccount_sid: str) -> str:
        """
        Get subaccount auth token from Twilio.
        
        Args:
            subaccount_sid: Twilio Subaccount SID
            
        Returns:
            Auth token for the subaccount
            
        Raises:
            NotFoundError: If subaccount not found
            ExternalServiceError: If Twilio API fails
        """
        if not self.client:
            raise ValueError("Twilio client not configured.")

        try:
            subaccount = self.client.api.accounts(subaccount_sid).fetch()
            return subaccount.auth_token
        except TwilioRestException as e:
            if e.status == 404:
                raise NotFoundError(
                    resource="TwilioSubaccount",
                    resource_id=subaccount_sid,
                )
            logger.error(f"Twilio API error getting subaccount auth token: {e}")
            raise ExternalServiceError(
                message="Failed to get Twilio subaccount auth token",
                service="Twilio",
                details={"error": str(e), "status_code": e.status, "code": e.code},
            ) from e

    async def close_subaccount(self, subaccount_sid: str) -> None:
        """
        Permanently close a Twilio subaccount (status=closed).

        Use main-account credentials. Call after moving any phone numbers
        to the pool (e.g. on account termination). Logs and swallows errors.
        """
        if not self.client:
            return
        try:
            self.client.api.accounts(subaccount_sid).update(status="closed")
            logger.info(f"Closed Twilio subaccount {subaccount_sid}")
        except TwilioRestException as e:
            if e.status == 404:
                logger.debug(f"Twilio subaccount {subaccount_sid} already gone or not found")
                return
            logger.warning(
                f"Failed to close Twilio subaccount {subaccount_sid}: {e}. Continuing."
            )
        except Exception as e:
            logger.warning(
                f"Failed to close Twilio subaccount {subaccount_sid}: {e}. Continuing."
            )

    async def provision_phone_number(
        self,
        area_code: Optional[str] = None,
        webhook_url: Optional[str] = None,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
    ) -> TwilioPhoneNumber:
        """
        Search for and purchase an available Twilio phone number.
        
        Args:
            area_code: Optional area code to search (e.g., '415', '212')
            webhook_url: Webhook URL to configure for incoming calls
            account_sid: Optional account SID to purchase number in (if None, uses main account)
            auth_token: Optional auth token for the account (required if account_sid is provided)
            
        Returns:
            TwilioPhoneNumber object with purchased number details
            
        Raises:
            ExternalServiceError: If Twilio API fails or no numbers available
        """
        if not self.client:
            raise ValueError(
                "Twilio client not configured. Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN."
            )

        try:
            # Determine which client to use
            if account_sid and auth_token:
                # Use subaccount client
                client = Client(account_sid, auth_token)
            else:
                # Use main account client
                client = self.client

            # Search for available numbers
            search_params = {}
            if area_code:
                search_params["area_code"] = area_code

            # Search for local numbers (not toll-free)
            # Note: Available numbers search uses main account, but purchase happens in specified account
            available_numbers = client.available_phone_numbers("US").local.list(
                **search_params
            )

            if not available_numbers:
                # If no numbers in preferred area code, search without area code
                available_numbers = client.available_phone_numbers("US").local.list(
                    limit=10
                )

            if not available_numbers:
                raise ExternalServiceError(
                    message="No phone numbers available",
                    service="Twilio",
                    details="No available numbers found. Try a different area code or try again later.",
                )

            # Purchase the first available number
            number_to_buy = available_numbers[0].phone_number

            # Purchase the number
            # Note: We don't set webhook_url during purchase if it's localhost
            # because Twilio requires publicly accessible URLs. We'll configure it after purchase.
            purchase_params = {
                "phone_number": number_to_buy,
            }

            # Only configure webhook if provided AND it's a publicly accessible URL
            # (not localhost, 127.0.0.1, or private IP)
            if webhook_url:
                # Check if URL is publicly accessible
                is_public = not any(
                    host in webhook_url.lower()
                    for host in ["localhost", "127.0.0.1", "0.0.0.0", "::1"]
                )
                if is_public:
                    purchase_params["voice_url"] = webhook_url
                    purchase_params["status_callback"] = webhook_url
                else:
                    logger.warning(
                        f"Webhook URL '{webhook_url}' is not publicly accessible. "
                        "Skipping webhook configuration during purchase. "
                        "Configure it manually in Twilio console or use a public URL (e.g., ngrok)."
                    )

            # Purchase the number
            purchased_number = client.incoming_phone_numbers.create(**purchase_params)
            
            # If webhook URL was provided but not set during purchase (due to localhost),
            # try to update it after purchase (this will still fail if URL is not public,
            # but at least we tried)
            if webhook_url and "voice_url" not in purchase_params:
                try:
                    purchased_number.update(voice_url=webhook_url, status_callback=webhook_url)
                    logger.info(f"Updated webhook URL for number {purchased_number.phone_number}")
                except Exception as e:
                    logger.warning(
                        f"Could not update webhook URL after purchase: {e}. "
                        "Please configure it manually in Twilio console."
                    )

            return TwilioPhoneNumber(
                sid=purchased_number.sid,
                phone_number=purchased_number.phone_number,
                status="active",
            )

        except TwilioRestException as e:
            # Provide helpful error message for trial account verification requirement
            if e.status == 400 and "verify a phone number" in str(e).lower():
                logger.error(
                    f"Twilio trial account requires phone number verification: {e}. "
                    "Please verify a phone number in your Twilio console before purchasing numbers."
                )
                raise ExternalServiceError(
                    message="Phone number verification required",
                    service="Twilio",
                    details={
                        "error": str(e),
                        "status_code": e.status,
                        "code": e.code,
                        "help": (
                            "Trial accounts must verify a phone number before purchasing numbers. "
                            "Go to https://console.twilio.com/us1/develop/phone-numbers/manage/verified "
                            "to verify a phone number in your main account."
                        ),
                    },
                ) from e
            logger.error(f"Twilio API error provisioning phone number: {e}")
            raise ExternalServiceError(
                message="Failed to provision phone number",
                service="Twilio",
                details={"error": str(e), "status_code": e.status, "code": e.code},
            ) from e

    async def update_phone_number_webhook(
        self,
        phone_number_sid: str,
        webhook_url: str,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
    ) -> TwilioPhoneNumber:
        """
        Update the webhook URL for an existing phone number.
        
        Args:
            phone_number_sid: Twilio Phone Number SID
            webhook_url: Webhook URL to configure for incoming calls
            account_sid: Optional account SID (if None, uses main account)
            auth_token: Optional auth token (required if account_sid is provided)
            
        Returns:
            Updated TwilioPhoneNumber object
            
        Raises:
            NotFoundError: If phone number not found
            ExternalServiceError: If Twilio API fails
        """
        if not self.client:
            raise ValueError("Twilio client not configured.")

        try:
            # Determine which client to use
            if account_sid and auth_token:
                client = Client(account_sid, auth_token)
            else:
                client = self.client

            # Update the phone number
            number = client.incoming_phone_numbers(phone_number_sid).update(
                voice_url=webhook_url,
                status_callback=webhook_url,
            )

            return TwilioPhoneNumber(
                sid=number.sid,
                phone_number=number.phone_number,
                status=number.status or "active",
            )
        except TwilioRestException as e:
            if e.status == 404:
                raise NotFoundError(
                    resource="TwilioPhoneNumber",
                    resource_id=phone_number_sid,
                )
            logger.error(f"Twilio API error updating phone number webhook: {e}")
            raise ExternalServiceError(
                message="Failed to update phone number webhook",
                service="Twilio",
                details={"error": str(e), "status_code": e.status, "code": e.code},
            ) from e

    async def list_phone_numbers(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
    ) -> list[TwilioPhoneNumber]:
        """
        List all phone numbers in Twilio account or subaccount.
        
        Args:
            account_sid: Optional account SID (if None, uses main account)
            auth_token: Optional auth token (required if account_sid is provided)
        
        Returns:
            List of TwilioPhoneNumber objects
            
        Raises:
            ExternalServiceError: If Twilio API fails
        """
        if not self.client:
            raise ValueError("Twilio client not configured.")

        try:
            # Determine which client to use
            if account_sid and auth_token:
                client = Client(account_sid, auth_token)
            else:
                client = self.client

            numbers = client.incoming_phone_numbers.list()
            return [
                TwilioPhoneNumber(
                    sid=n.sid,
                    phone_number=n.phone_number,
                    status=n.status or "active",
                )
                for n in numbers
            ]
        except TwilioRestException as e:
            logger.error(f"Error listing Twilio numbers: {e}")
            raise ExternalServiceError(
                message="Failed to list phone numbers",
                service="Twilio",
                details={"error": str(e), "status_code": e.status, "code": e.code},
            ) from e

    async def transfer_phone_number_to_account(
        self,
        phone_number_sid: str,
        source_account_sid: str,
        target_account_sid: str,
    ) -> TwilioPhoneNumber:
        """
        Transfer a phone number from one Twilio account (subaccount) to another.

        Uses the main account's credentials; the number is moved from source to target.
        Used for the number pool: return number to pool (target=pool/main) or assign
        from pool to firm (source=pool/main, target=firm subaccount).

        Args:
            phone_number_sid: Twilio Phone Number SID (e.g., PN...)
            source_account_sid: Account SID where the number currently lives
            target_account_sid: Account SID to move the number to (pool or firm subaccount)

        Returns:
            TwilioPhoneNumber with updated details

        Raises:
            ValueError: If Twilio client not configured
            NotFoundError: If phone number not found
            ExternalServiceError: If Twilio API fails
        """
        if not self.client:
            raise ValueError("Twilio client not configured.")

        try:
            # Use main account client; target the source account's IncomingPhoneNumbers resource
            # and update AccountSid to move the number to target account
            number_resource = self.client.api.accounts(source_account_sid).incoming_phone_numbers(
                phone_number_sid
            )
            number = number_resource.update(account_sid=target_account_sid)

            logger.info(
                f"Transferred phone number {phone_number_sid} from {source_account_sid} to {target_account_sid}"
            )
            return TwilioPhoneNumber(
                sid=number.sid,
                phone_number=number.phone_number,
                status=number.status or "active",
            )
        except TwilioRestException as e:
            if e.status == 404:
                raise NotFoundError(
                    resource="TwilioPhoneNumber",
                    resource_id=phone_number_sid,
                )
            logger.error(f"Twilio API error transferring phone number: {e}")
            raise ExternalServiceError(
                message="Failed to transfer phone number",
                service="Twilio",
                details={"error": str(e), "status_code": e.status, "code": e.code},
            ) from e

    async def release_phone_number(
        self,
        phone_number_sid: str,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
    ) -> bool:
        """
        Release (delete) a Twilio phone number.
        
        This permanently removes the phone number from the Twilio account.
        The number will be immediately unavailable and cannot be recovered.
        
        Args:
            phone_number_sid: Twilio Phone Number SID (e.g., PNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx)
            account_sid: Optional account SID to release number from (if None, uses main account)
            auth_token: Optional auth token for the account (required if account_sid is provided)
            
        Returns:
            True if number was successfully released, False otherwise
            
        Raises:
            NotFoundError: If phone number not found
            ExternalServiceError: If Twilio API fails
        """
        if not self.client:
            raise ValueError("Twilio client not configured.")
        
        # Use subaccount client if provided, otherwise use main account
        client = self.client
        if account_sid and auth_token:
            client = Client(account_sid, auth_token)
        
        try:
            # Delete the phone number from Twilio
            # This permanently releases the number
            client.incoming_phone_numbers(phone_number_sid).delete()
            logger.info(f"Successfully released Twilio phone number: {phone_number_sid}")
            return True
        except TwilioRestException as e:
            if e.status == 404:
                logger.warning(
                    f"Phone number {phone_number_sid} not found in Twilio. "
                    f"It may have already been released."
                )
                # Return True since the goal (number not in account) is achieved
                return True
            logger.error(f"Twilio API error releasing phone number: {e}")
            raise ExternalServiceError(
                message="Failed to release Twilio phone number",
                service="Twilio",
                details={"error": str(e), "status_code": e.status, "code": e.code},
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error releasing phone number: {e}")
            raise ExternalServiceError(
                message="Unexpected error releasing Twilio phone number",
                service="Twilio",
                details={"error": str(e)},
            ) from e

    async def search_phone_number(
        self, phone_number: str
    ) -> Optional[TwilioPhoneNumber]:
        """
        Search for a phone number in Twilio account by E.164 format.
        
        Args:
            phone_number: Phone number in E.164 format (e.g., +15551234567)
            
        Returns:
            TwilioPhoneNumber if found, None otherwise
        """
        if not self.client:
            return None

        try:
            numbers = self.client.incoming_phone_numbers.list(phone_number=phone_number)
            if numbers:
                n = numbers[0]
                return TwilioPhoneNumber(
                    sid=n.sid,
                    phone_number=n.phone_number,
                    status=n.status or "active",
                )
            return None
        except TwilioRestException as e:
            logger.error(f"Error searching Twilio number: {e}")
            return None


def get_twilio_service() -> TwilioService:
    """Get Twilio service instance."""
    return TwilioService()

