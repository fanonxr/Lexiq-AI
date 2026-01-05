"""Google Calendar service for integration worker.

This service handles Google Calendar synchronization, similar to OutlookService.
"""

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.ext.asyncio import AsyncSession

from integration_worker.config import get_settings
from integration_worker.database.repositories import (
    AppointmentsRepository,
    CalendarIntegrationRepository,
)
from integration_worker.models.sync_result import SyncResult, TokenRefreshResult
from integration_worker.utils.errors import SyncError, TokenRefreshError, ExternalAPIError

# Import models from api-core (shared database)
try:
    from api_core.database.models import CalendarIntegration, User
except ImportError:
    raise ImportError(
        "Cannot import api_core models. "
        "Ensure api-core is in PYTHONPATH or installed as a package."
    )

logger = logging.getLogger(__name__)
settings = get_settings()

# Google Calendar API scopes
GOOGLE_CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]


class GoogleService:
    """Service for Google Calendar operations."""
    
    def __init__(self, session: AsyncSession):
        """Initialize Google service."""
        self.session = session
        self.calendar_repo = CalendarIntegrationRepository(session)
        self.appointments_repo = AppointmentsRepository(session)
        self.calendar_api_version = "v3"
    
    def _get_credentials(self, integration: CalendarIntegration) -> Credentials:
        """
        Get Google OAuth credentials from integration.
        
        Args:
            integration: Calendar integration with stored tokens
        
        Returns:
            Google Credentials object
        
        Raises:
            SyncError: If tokens are invalid or missing
        """
        if not integration.access_token:
            raise SyncError(f"Integration {integration.id} has no access token")
        
        # Create credentials from stored tokens
        credentials = Credentials(
            token=integration.access_token,
            refresh_token=integration.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            scopes=GOOGLE_CALENDAR_SCOPES,
        )
        
        return credentials
    
    async def get_valid_access_token(self, integration: CalendarIntegration) -> str:
        """
        Get a valid access token, refreshing if necessary.
        
        Args:
            integration: Calendar integration
        
        Returns:
            Valid access token
        
        Raises:
            TokenRefreshError: If token refresh fails
        """
        credentials = self._get_credentials(integration)
        
        # Check if token is expired or about to expire (within 5 minutes)
        if credentials.expired or (
            integration.token_expires_at
            and integration.token_expires_at <= datetime.now(timezone.utc) + timedelta(minutes=5)
        ):
            logger.info(f"Token for integration {integration.id} is expiring, refreshing...")
            result = await self.refresh_access_token(str(integration.id))
            # Refresh the integration object to get the new token
            await self.session.refresh(integration)
            return integration.access_token
        
        return integration.access_token
    
    async def sync_calendar(
        self,
        integration_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> SyncResult:
        """
        Sync appointments from Google Calendar.
        
        Args:
            integration_id: Calendar integration ID
            start_date: Optional start date for sync range
            end_date: Optional end date for sync range
        
        Returns:
            SyncResult with sync statistics
        
        Raises:
            SyncError: If sync fails
        """
        started_at = datetime.now(timezone.utc)
        result = SyncResult(
            success=False,
            integration_id=integration_id,
            started_at=started_at,
        )
        
        try:
            # Get integration from database
            integration = await self.calendar_repo.get_by_id(integration_id)
            if not integration:
                raise SyncError(f"Integration {integration_id} not found")
            
            if not integration.is_active:
                raise SyncError(f"Integration {integration_id} is not active")
            
            # Get valid access token
            access_token = await self.get_valid_access_token(integration)
            
            # Build Google Calendar API service
            credentials = self._get_credentials(integration)
            service = build("calendar", self.calendar_api_version, credentials=credentials)
            
            # Set default date range if not provided
            if not start_date:
                start_date = datetime.now(timezone.utc) - timedelta(days=settings.sync_lookback_days)
            if not end_date:
                end_date = datetime.now(timezone.utc) + timedelta(days=settings.sync_lookahead_days)
            
            # Normalize dates to UTC
            start_date_utc = self._normalize_to_utc(start_date)
            end_date_utc = self._normalize_to_utc(end_date)
            
            # Get calendar ID (default to primary calendar)
            calendar_id = integration.calendar_id or "primary"
            
            # Fetch events from Google Calendar
            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=start_date_utc.isoformat(),
                timeMax=end_date_utc.isoformat(),
                singleEvents=True,
                orderBy="startTime",
                maxResults=settings.sync_batch_size,
            ).execute()
            
            events = events_result.get("items", [])
            
            # Get user and firm info
            user = await self.session.get(User, integration.user_id)
            if not user:
                raise SyncError(f"User {integration.user_id} not found")
            
            firm_id = user.firm_id
            
            # Process each event
            for event in events:
                try:
                    await self._process_event(
                        event,
                        integration.user_id,
                        firm_id,
                        integration_id,
                        result,
                    )
                except Exception as e:
                    logger.warning(
                        f"Error processing Google Calendar event {event.get('id', 'unknown')}: {e}",
                        exc_info=True,
                    )
                    result.errors.append(f"Event {event.get('id', 'unknown')}: {str(e)}")
            
            # Update integration sync status
            integration.last_synced_at = datetime.now(timezone.utc)
            integration.sync_error = None
            await self.session.flush()
            
            result.success = True
            result.completed_at = datetime.now(timezone.utc)
            
            logger.info(
                f"Synced {result.appointments_synced} appointments "
                f"({result.appointments_updated} updated) for Google Calendar integration {integration_id}"
            )
            
            return result
            
        except HttpError as e:
            error_msg = f"Google Calendar API error: {e.resp.status} {e.content.decode()}"
            logger.error(error_msg, exc_info=True)
            result.errors.append(error_msg)
            result.completed_at = datetime.now(timezone.utc)
            
            # Update integration with error
            try:
                integration = await self.calendar_repo.get_by_id(integration_id)
                if integration:
                    integration.sync_error = error_msg
                    await self.session.flush()
            except Exception:
                pass  # Don't fail if we can't update the error
            
            raise SyncError(error_msg) from e
        except Exception as e:
            error_msg = f"Error syncing Google Calendar: {str(e)}"
            logger.error(error_msg, exc_info=True)
            result.errors.append(error_msg)
            result.completed_at = datetime.now(timezone.utc)
            raise SyncError(error_msg) from e
    
    async def _process_event(
        self,
        event: dict,
        user_id: str,
        firm_id: Optional[str],
        calendar_integration_id: str,
        result: SyncResult,
    ) -> None:
        """Process a single calendar event and create/update appointment."""
        # Skip cancelled events
        if event.get("status") == "cancelled":
            return
        
        # Parse event data
        start_data = event.get("start", {})
        end_data = event.get("end", {})
        
        # Handle dateTime (for timed events) or date (for all-day events)
        if "dateTime" in start_data:
            start_time_str = start_data["dateTime"]
            end_time_str = end_data.get("dateTime", start_time_str)
            is_all_day = False
        elif "date" in start_data:
            # All-day event - use start of day in UTC
            start_time_str = f"{start_data['date']}T00:00:00+00:00"
            end_time_str = f"{end_data.get('date', start_data['date'])}T23:59:59+00:00"
            is_all_day = True
        else:
            logger.warning(f"Skipping event {event.get('id')}: missing start/end time")
            return
        
        # Handle timezone-aware datetime strings
        if start_time_str.endswith("Z"):
            start_time_str = start_time_str.replace("Z", "+00:00")
        if end_time_str.endswith("Z"):
            end_time_str = end_time_str.replace("Z", "+00:00")
        
        start_time = datetime.fromisoformat(start_time_str)
        end_time = datetime.fromisoformat(end_time_str)
        duration_minutes = int((end_time - start_time).total_seconds() / 60)
        
        # Get contact info
        organizer = event.get("organizer", {})
        contact_name = organizer.get("displayName", "Unknown")
        contact_email = organizer.get("email")
        
        # Generate idempotency key
        event_id = event.get("id")
        if not event_id:
            logger.warning("Skipping event: missing ID field")
            return
        
        idempotency_key = self._generate_idempotency_key(event_id)
        
        # Check if appointment already exists
        existing = await self.appointments_repo.get_by_idempotency_key(idempotency_key)
        
        event_timezone = start_data.get("timeZone", "UTC")
        title = event.get("summary", "Untitled Event")
        notes = event.get("description", "").strip() or None
        
        if not existing:
            # Create new appointment
            await self.appointments_repo.create(
                firm_id=firm_id,
                created_by_user_id=user_id,
                timezone=event_timezone,
                start_at=start_time,
                end_at=end_time,
                duration_minutes=duration_minutes,
                title=title,
                notes=notes,
                status="booked",
                contact_full_name=contact_name,
                contact_email=contact_email,
                contact_phone=None,
                idempotency_key=idempotency_key,
                source_calendar_id=calendar_integration_id,
                source_event_id=event_id,
            )
            result.appointments_synced += 1
            logger.info(
                f"Created appointment from Google Calendar event {event_id} "
                f"(title: {title}, start: {start_time.isoformat()})"
            )
        else:
            # Update existing appointment
            existing.start_at = start_time
            existing.end_at = end_time
            existing.duration_minutes = duration_minutes
            existing.title = title
            existing.notes = notes
            existing.contact_full_name = contact_name
            existing.contact_email = contact_email
            # Don't update status if it's cancelled (preserve cancellation)
            if existing.status != "cancelled":
                existing.status = "booked"
            
            await self.session.flush()
            result.appointments_updated += 1
            logger.info(
                f"Updated appointment from Google Calendar event {event_id} "
                f"(title: {title}, start: {start_time.isoformat()})"
            )
    
    async def sync_single_event(
        self,
        integration_id: str,
        event_id: str,
    ) -> SyncResult:
        """
        Sync a single calendar event by ID (optimized for webhook processing).
        
        Args:
            integration_id: Calendar integration ID
            event_id: Google Calendar event ID
        
        Returns:
            SyncResult with sync statistics
        
        Raises:
            SyncError: If sync fails
        """
        started_at = datetime.now(timezone.utc)
        result = SyncResult(
            success=False,
            integration_id=integration_id,
            started_at=started_at,
        )
        
        try:
            # Get integration from database
            integration = await self.calendar_repo.get_by_id(integration_id)
            if not integration:
                raise SyncError(f"Integration {integration_id} not found")
            
            if not integration.is_active:
                raise SyncError(f"Integration {integration_id} is not active")
            
            # Get valid access token
            access_token = await self.get_valid_access_token(integration)
            
            # Build Google Calendar API service
            credentials = self._get_credentials(integration)
            service = build("calendar", self.calendar_api_version, credentials=credentials)
            
            # Get calendar ID (default to primary calendar)
            calendar_id = integration.calendar_id or "primary"
            
            # Fetch single event from Google Calendar
            try:
                event = service.events().get(
                    calendarId=calendar_id,
                    eventId=event_id,
                ).execute()
            except HttpError as e:
                if e.resp.status == 404:
                    # Event not found (may have been deleted)
                    logger.warning(
                        f"Event {event_id} not found in Google Calendar "
                        f"(may have been deleted)"
                    )
                    result.success = True
                    result.errors.append(f"Event {event_id} not found (may be deleted)")
                    return result
                raise
            
            # Get user and firm info
            user = await self.session.get(User, integration.user_id)
            if not user:
                raise SyncError(f"User {integration.user_id} not found")
            
            firm_id = user.firm_id
            
            # Process the single event
            await self._process_event(
                event,
                integration.user_id,
                firm_id,
                integration_id,
                result,
            )
            
            result.success = True
            result.completed_at = datetime.now(timezone.utc)
            
            logger.info(
                f"Synced single event {event_id} for integration {integration_id}: "
                f"{result.appointments_synced} created, {result.appointments_updated} updated"
            )
            
            return result
            
        except HttpError as e:
            error_msg = f"Google Calendar API error fetching event {event_id}: {e.resp.status} {e.content.decode()}"
            logger.error(error_msg, exc_info=True)
            result.errors.append(error_msg)
            result.completed_at = datetime.now(timezone.utc)
            raise SyncError(error_msg) from e
        except Exception as e:
            error_msg = f"Error syncing single event {event_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            result.errors.append(error_msg)
            result.completed_at = datetime.now(timezone.utc)
            raise SyncError(error_msg) from e
    
    async def delete_synced_event(
        self,
        integration_id: str,
        event_id: str,
    ) -> bool:
        """
        Mark appointment as cancelled when Google Calendar event is deleted.
        
        Args:
            integration_id: Calendar integration ID
            event_id: Google Calendar event ID
        
        Returns:
            True if appointment was found and cancelled, False otherwise
        """
        try:
            # Generate idempotency key (same as in _process_event)
            idempotency_key = self._generate_idempotency_key(event_id)
            
            # Find appointment by idempotency key
            appointment = await self.appointments_repo.get_by_idempotency_key(idempotency_key)
            
            if appointment:
                # Mark as cancelled instead of deleting (preserve history)
                appointment.status = "cancelled"
                await self.session.flush()
                
                logger.info(
                    f"Marked appointment {appointment.id} as cancelled "
                    f"(Google Calendar event {event_id} was deleted)"
                )
                
                return True
            else:
                logger.warning(
                    f"Appointment for deleted event {event_id} not found "
                    f"(may not have been synced yet or already cancelled)"
                )
                return False
                
        except Exception as e:
            logger.error(
                f"Error marking appointment as cancelled for event {event_id}: {e}",
                exc_info=True,
            )
            raise
    
    async def refresh_access_token(self, integration_id: str) -> TokenRefreshResult:
        """
        Refresh the access token for an integration.
        
        Args:
            integration_id: Calendar integration ID
        
        Returns:
            TokenRefreshResult with refresh status
        
        Raises:
            TokenRefreshError: If refresh fails
        """
        result = TokenRefreshResult(
            success=False,
            integration_id=integration_id,
        )
        
        try:
            # Get integration
            integration = await self.calendar_repo.get_by_id(integration_id)
            if not integration:
                raise TokenRefreshError(f"Integration {integration_id} not found")
            
            if not integration.refresh_token:
                raise TokenRefreshError("No refresh token available for this integration")
            
            # Create credentials from stored tokens
            credentials = Credentials(
                token=integration.access_token,
                refresh_token=integration.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret,
                scopes=GOOGLE_CALENDAR_SCOPES,
            )
            
            # Refresh token
            credentials.refresh(Request())
            
            # Update integration with new tokens
            integration.access_token = credentials.token
            if credentials.refresh_token:
                integration.refresh_token = credentials.refresh_token
            integration.token_expires_at = credentials.expiry
            await self.session.flush()
            await self.session.refresh(integration)
            
            result.success = True
            result.expires_at = integration.token_expires_at
            
            logger.info(
                f"Refreshed token for integration {integration_id}, "
                f"expires at {result.expires_at.isoformat()}"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Failed to refresh token: {str(e)}"
            logger.error(error_msg, exc_info=True)
            result.error = error_msg
            raise TokenRefreshError(error_msg) from e
    
    def _normalize_to_utc(self, dt: datetime) -> datetime:
        """Normalize datetime to UTC timezone."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    
    def _generate_idempotency_key(self, event_id: str) -> str:
        """
        Generate idempotency key for event.
        
        Google Calendar event IDs can be very long, so we hash if needed.
        Max length is 128 characters.
        """
        base_key = f"google_{event_id}"
        if len(base_key) > 128:
            # Hash the event ID to keep it under 128 chars
            event_hash = hashlib.sha256(event_id.encode()).hexdigest()[:32]
            return f"google_{event_hash}"
        return base_key

