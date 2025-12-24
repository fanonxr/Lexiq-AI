"""Calendar integration service for Outlook/Google Calendar."""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import httpx
from msal import ConfidentialClientApplication
from sqlalchemy.ext.asyncio import AsyncSession

from api_core.database.models import CalendarIntegration, User
from api_core.exceptions import AuthorizationError, NotFoundError, ValidationError
from api_core.repositories.appointments_repository import AppointmentsRepository
from api_core.repositories.calendar_integration_repository import CalendarIntegrationRepository

logger = logging.getLogger(__name__)


class CalendarIntegrationService:
    """Service for calendar integration operations."""

    def __init__(self, session: AsyncSession):
        """Initialize calendar integration service."""
        self.repository = CalendarIntegrationRepository(session)
        self.session = session
        # Microsoft Graph API base URL
        self.graph_api_url = "https://graph.microsoft.com/v1.0"

    async def initiate_outlook_oauth(self, user_id: str, redirect_uri: str) -> str:
        """
        Initiate Outlook OAuth flow.

        Returns authorization URL for user to visit.
        """
        from api_core.config import get_settings

        settings = get_settings()

        # Validate configuration
        if not settings.azure_ad_b2c.client_id:
            raise ValidationError("Azure AD client ID is not configured")
        if not settings.azure_ad_b2c.tenant_id:
            raise ValidationError("Azure AD tenant ID is not configured")

        # Use client_secret (AZURE_AD_B2C_CLIENT_SECRET)
        client_secret = settings.azure_ad_b2c.client_secret
        if not client_secret:
            raise ValidationError("Azure AD client secret is not configured. Please set AZURE_AD_B2C_CLIENT_SECRET environment variable.")

        # Build authority URL
        authority = f"https://login.microsoftonline.com/{settings.azure_ad_b2c.tenant_id}"
        logger.info(
            f"Initializing MSAL app - "
            f"client_id={settings.azure_ad_b2c.client_id}, "
            f"tenant_id={settings.azure_ad_b2c.tenant_id}, "
            f"redirect_uri={redirect_uri}"
        )

        # Create MSAL app instance
        app = ConfidentialClientApplication(
            client_id=settings.azure_ad_b2c.client_id,
            client_credential=client_secret,
            authority=authority,
        )

        # Generate authorization URL
        # Note: offline_access is automatically included by MSAL for refresh tokens
        # Do not include it explicitly as it's a reserved scope
        try:
            auth_url = app.get_authorization_request_url(
                scopes=["https://graph.microsoft.com/Calendars.ReadWrite"],
                redirect_uri=redirect_uri,
                state=user_id,  # Pass user_id in state for callback
            )
            
            if not auth_url:
                raise ValidationError("Failed to generate authorization URL: MSAL returned None")
            
            if not isinstance(auth_url, str) or not auth_url.startswith("http"):
                raise ValidationError(f"Invalid authorization URL format: {auth_url}")
            
            logger.info(f"Generated authorization URL: {auth_url[:100]}...")
            return auth_url
            
        except Exception as e:
            logger.error(f"Error generating authorization URL: {e}", exc_info=True)
            raise ValidationError(f"Failed to generate authorization URL: {str(e)}") from e

    async def handle_outlook_oauth_callback(
        self,
        user_id: str,
        authorization_code: str,
        redirect_uri: str,
    ) -> CalendarIntegration:
        """
        Handle OAuth callback and store tokens.
        """
        from api_core.config import get_settings

        settings = get_settings()

        # Use client_secret (AZURE_AD_B2C_CLIENT_SECRET)
        client_secret = settings.azure_ad_b2c.client_secret
        if not client_secret:
            raise ValidationError("Azure AD client secret is not configured. Please set AZURE_AD_B2C_CLIENT_SECRET environment variable.")

        # Exchange authorization code for tokens
        logger.info(
            f"OAuth callback - "
            f"client_id={settings.azure_ad_b2c.client_id}, "
            f"tenant_id={settings.azure_ad_b2c.tenant_id}"
        )
        app = ConfidentialClientApplication(
            client_id=settings.azure_ad_b2c.client_id,
            client_credential=client_secret,
            authority=f"https://login.microsoftonline.com/{settings.azure_ad_b2c.tenant_id}",
        )

        # Note: offline_access is automatically included by MSAL for refresh tokens
        result = app.acquire_token_by_authorization_code(
            code=authorization_code,
            scopes=["https://graph.microsoft.com/Calendars.ReadWrite"],
            redirect_uri=redirect_uri,
        )

        if "error" in result:
            raise ValidationError(f"OAuth error: {result.get('error_description')}")

        # Get user's email from token
        user_info = result.get("id_token_claims", {})
        email = user_info.get("email") or user_info.get("preferred_username")

        # Encrypt tokens before storing (use your encryption service)
        # For now, storing as-is (NOT RECOMMENDED FOR PRODUCTION)
        access_token = result["access_token"]
        refresh_token = result.get("refresh_token")
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=result.get("expires_in", 3600))

        # Get default calendar ID
        calendar_id = await self._get_default_calendar_id(access_token, email)

        # Create or update integration
        existing = await self.repository.get_by_user_and_type(user_id, "outlook")
        if existing:
            existing.access_token = access_token
            existing.refresh_token = refresh_token
            existing.token_expires_at = expires_at
            existing.calendar_id = calendar_id
            existing.email = email
            existing.is_active = True
            existing.sync_error = None
            await self.session.flush()
            await self.session.refresh(existing)
            return existing
        else:
            return await self.repository.create(
                user_id=user_id,
                integration_type="outlook",
                access_token=access_token,
                refresh_token=refresh_token,
                token_expires_at=expires_at,
                calendar_id=calendar_id,
                email=email,
            )

    async def _get_default_calendar_id(self, access_token: str, email: str) -> str:
        """Get the default calendar ID for the user."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.graph_api_url}/me/calendars",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            calendars = response.json().get("value", [])

            # Find default calendar (usually the first one or one named "Calendar")
            for calendar in calendars:
                if calendar.get("isDefaultCalendar") or calendar.get("name") == "Calendar":
                    return calendar["id"]

            # Fallback to first calendar
            if calendars:
                return calendars[0]["id"]

            raise ValidationError("No calendars found for user")

    async def refresh_access_token(self, integration: CalendarIntegration) -> str:
        """Refresh the access token using refresh token."""
        from api_core.config import get_settings

        settings = get_settings()

        if not integration.refresh_token:
            raise ValidationError("No refresh token available for this integration")

        # Use client_secret (AZURE_AD_B2C_CLIENT_SECRET)
        client_secret = settings.azure_ad_b2c.client_secret
        if not client_secret:
            raise ValidationError("Azure AD client secret is not configured. Please set AZURE_AD_B2C_CLIENT_SECRET environment variable.")
        
        # Log detailed info for debugging (without exposing the actual secret)
        logger.info(
            f"Token refresh configuration - "
            f"client_id={settings.azure_ad_b2c.client_id}, "
            f"tenant_id={settings.azure_ad_b2c.tenant_id}, "
            f"secret_length={len(client_secret)}, "
            f"secret_preview={client_secret[:10]}...{client_secret[-5:] if len(client_secret) > 15 else ''}"
        )

        app = ConfidentialClientApplication(
            client_id=settings.azure_ad_b2c.client_id,
            client_credential=client_secret,
            authority=f"https://login.microsoftonline.com/{settings.azure_ad_b2c.tenant_id}",
        )

        # Note: offline_access is automatically included by MSAL for refresh tokens
        result = app.acquire_token_by_refresh_token(
            refresh_token=integration.refresh_token,
            scopes=["https://graph.microsoft.com/Calendars.ReadWrite"],
        )

        if "error" in result:
            raise ValidationError(f"Token refresh error: {result.get('error_description')}")

        # Update tokens
        integration.access_token = result["access_token"]
        if "refresh_token" in result:
            integration.refresh_token = result["refresh_token"]
        integration.token_expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=result.get("expires_in", 3600)
        )
        await self.session.flush()
        await self.session.refresh(integration)

        return integration.access_token

    async def get_valid_access_token(self, integration: CalendarIntegration) -> str:
        """Get a valid access token, refreshing if necessary."""
        # Check if token is expired or about to expire (within 5 minutes)
        if (
            integration.token_expires_at
            and integration.token_expires_at <= datetime.now(timezone.utc) + timedelta(minutes=5)
        ):
            return await self.refresh_access_token(integration)
        return integration.access_token

    async def sync_outlook_calendar(
        self,
        integration: CalendarIntegration,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """
        Sync appointments from Outlook calendar.

        Returns number of appointments synced.
        """
        try:
            # Get valid access token
            access_token = await self.get_valid_access_token(integration)

            # Build Microsoft Graph API query
            # Get events from the default calendar
            # Use /me/calendar/events for the default calendar (simpler and more reliable)
            url = f"{self.graph_api_url}/me/calendar/events"

            # Set default date range if not provided (last 30 days to next 90 days)
            if not start_date:
                start_date = datetime.now(timezone.utc) - timedelta(days=30)
            if not end_date:
                end_date = datetime.now(timezone.utc) + timedelta(days=90)
            
            # Normalize dates to UTC for consistent comparison
            if start_date.tzinfo is None:
                start_date_utc = start_date.replace(tzinfo=timezone.utc)
            else:
                start_date_utc = start_date.astimezone(timezone.utc)
            
            if end_date.tzinfo is None:
                end_date_utc = end_date.replace(tzinfo=timezone.utc)
            else:
                end_date_utc = end_date.astimezone(timezone.utc)

            # Use a simpler approach: fetch events and filter in Python
            # This avoids Graph API filter syntax issues
            params = {
                "$select": "id,subject,start,end,body,organizer,attendees,isCancelled",
                "$orderby": "start/dateTime",
                # Use a wider date range to ensure we get all relevant events
                # Filter will be done in Python for more control
                "$top": 1000,  # Maximum events to fetch
            }

            # Fetch events from Microsoft Graph
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {access_token}"},
                    params=params,
                )
                response.raise_for_status()
                events_data = response.json()
                events = events_data.get("value", [])
                
                logger.info(f"Fetched {len(events)} events from Outlook calendar")

            # Transform and store appointments
            synced_count = 0
            appointments_repo = AppointmentsRepository(self.session)

            # Load user to get firm_id - select only the fields we need to avoid relationship loading
            from sqlalchemy import select

            user_result = await self.session.execute(
                select(User.id, User.firm_id).where(User.id == integration.user_id)
            )
            user_row = user_result.first()
            if not user_row:
                raise NotFoundError(resource="User", resource_id=integration.user_id)
            
            user_id_value = user_row[0]
            user_firm_id = user_row[1]
            
            # Get the calendar integration ID as a string to avoid SQLAlchemy relationship issues
            calendar_integration_id = str(integration.id)

            # Filter events by date range in Python (more reliable than Graph API filter)
            filtered_events = []
            for event in events:
                # Skip cancelled events
                if event.get("isCancelled"):
                    continue
                
                # Check if event is within date range
                if not event.get("start") or not event.get("start").get("dateTime"):
                    continue
                if not event.get("end") or not event.get("end").get("dateTime"):
                    continue
                
                start_time_str = event["start"]["dateTime"]
                end_time_str = event["end"]["dateTime"]
                
                # Handle timezone-aware datetime strings
                if start_time_str.endswith("Z"):
                    start_time_str = start_time_str.replace("Z", "+00:00")
                if end_time_str.endswith("Z"):
                    end_time_str = end_time_str.replace("Z", "+00:00")
                
                try:
                    event_start = datetime.fromisoformat(start_time_str)
                    event_end = datetime.fromisoformat(end_time_str)
                    
                    # Ensure both datetimes are timezone-aware and normalized to UTC
                    if event_start.tzinfo is None:
                        event_start_utc = event_start.replace(tzinfo=timezone.utc)
                    else:
                        event_start_utc = event_start.astimezone(timezone.utc)
                    
                    if event_end.tzinfo is None:
                        event_end_utc = event_end.replace(tzinfo=timezone.utc)
                    else:
                        event_end_utc = event_end.astimezone(timezone.utc)
                    
                    # Include events that overlap with the date range
                    # (start is before end_date and end is after start_date)
                    if event_start_utc <= end_date_utc and event_end_utc >= start_date_utc:
                        filtered_events.append(event)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse event date: {e}", exc_info=True)
                    continue
            
            logger.info(f"Filtered to {len(filtered_events)} events within date range ({start_date_utc.isoformat()} to {end_date_utc.isoformat()})")

            for event in filtered_events:
                # Parse event data (already validated in filtering step)
                start_time_str = event["start"]["dateTime"]
                end_time_str = event["end"]["dateTime"]

                # Handle timezone-aware datetime strings (already done in filtering, but ensure consistency)
                if start_time_str.endswith("Z"):
                    start_time_str = start_time_str.replace("Z", "+00:00")
                if end_time_str.endswith("Z"):
                    end_time_str = end_time_str.replace("Z", "+00:00")

                start_time = datetime.fromisoformat(start_time_str)
                end_time = datetime.fromisoformat(end_time_str)
                duration_minutes = int((end_time - start_time).total_seconds() / 60)

                # Get contact info from organizer or first attendee
                organizer = event.get("organizer", {}).get("emailAddress", {})
                contact_name = organizer.get("name", "Unknown")
                contact_email = organizer.get("address")

                # Use event ID as idempotency key
                event_id = event.get("id")
                if not event_id:
                    logger.warning(f"Skipping event: missing ID field")
                    continue
                
                # Create idempotency key - Outlook event IDs can be very long, so hash if needed
                # Max length is 128 characters, so we'll use a hash if the key would be too long
                import hashlib
                base_key = f"outlook_{event_id}"
                if len(base_key) > 128:
                    # Hash the event ID to keep it under 128 chars
                    event_hash = hashlib.sha256(event_id.encode()).hexdigest()[:32]
                    idempotency_key = f"outlook_{event_hash}"
                else:
                    idempotency_key = base_key

                # Check if appointment already exists
                existing = await appointments_repo.get_by_idempotency_key(idempotency_key)

                if not existing:
                    # Create new appointment
                    event_timezone = event["start"].get("timeZone", "UTC")
                    title = event.get("subject", "Untitled Event")

                    try:
                        created = await appointments_repo.create(
                            firm_id=user_firm_id,  # Use the firm_id we extracted earlier
                            created_by_user_id=user_id_value,  # IMPORTANT: Set user_id so appointments are returned in queries
                            timezone=event_timezone,
                            start_at=start_time,
                            end_at=end_time,
                            duration_minutes=duration_minutes,
                            title=title,
                            notes=None,  # Could extract from event["body"]["content"] if needed
                            status="booked",
                            contact_full_name=contact_name,
                            contact_email=contact_email,
                            contact_phone=None,
                            idempotency_key=idempotency_key,
                            source_calendar_id=calendar_integration_id,  # Use the string ID we extracted earlier
                            source_event_id=event_id,
                        )
                        synced_count += 1
                        logger.info(
                            f"Synced appointment {created.id} from Outlook event {event_id} (title: {title}, start: {start_time.isoformat()})"
                        )
                    except Exception as create_error:
                        logger.error(
                            f"Failed to create appointment from event {event_id}: {create_error}",
                            exc_info=True
                        )
                        # Continue with next event instead of failing entire sync
                        continue

            # Update integration status
            integration.last_synced_at = datetime.now(timezone.utc)
            integration.sync_error = None
            await self.session.flush()
            await self.session.refresh(integration)

            return synced_count

        except Exception as e:
            logger.error(f"Error syncing Outlook calendar: {e}", exc_info=True)
            integration.sync_error = str(e)
            await self.session.flush()
            await self.session.refresh(integration)
            raise

    async def disconnect_integration(self, integration_id: str, user_id: str) -> None:
        """Disconnect a calendar integration."""
        integration = await self.repository.get_by_id(integration_id)
        if not integration:
            raise NotFoundError(resource="CalendarIntegration", resource_id=integration_id)

        if integration.user_id != user_id:
            raise AuthorizationError("User does not have access to this integration")

        integration.is_active = False
        integration.access_token = None
        integration.refresh_token = None
        await self.session.flush()
        await self.session.refresh(integration)

