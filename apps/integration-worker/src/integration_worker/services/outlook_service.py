"""Outlook calendar service for integration worker.

This service contains sync logic migrated from api-core's CalendarIntegrationService.
"""

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from msal import ConfidentialClientApplication
from sqlalchemy import select
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


class OutlookService:
    """Service for Outlook calendar operations."""
    
    def __init__(self, session: AsyncSession):
        """Initialize Outlook service."""
        self.session = session
        self.calendar_repo = CalendarIntegrationRepository(session)
        self.appointments_repo = AppointmentsRepository(session)
        self.graph_api_url = "https://graph.microsoft.com/v1.0"
    
    async def sync_calendar(
        self,
        integration_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> SyncResult:
        """
        Sync appointments from Outlook calendar.
        
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
            
            # Get valid access token (will refresh if needed)
            access_token = await self.get_valid_access_token(integration)
            
            # Build Microsoft Graph API query
            url = f"{self.graph_api_url}/me/calendar/events"
            
            # Set default date range if not provided
            if not start_date:
                start_date = datetime.now(timezone.utc) - timedelta(days=settings.sync_lookback_days)
            if not end_date:
                end_date = datetime.now(timezone.utc) + timedelta(days=settings.sync_lookahead_days)
            
            # Normalize dates to UTC
            start_date_utc = self._normalize_to_utc(start_date)
            end_date_utc = self._normalize_to_utc(end_date)
            
            # Fetch events from Microsoft Graph
            params = {
                "$select": "id,subject,start,end,body,organizer,attendees,isCancelled",
                "$orderby": "start/dateTime",
                "$top": settings.sync_batch_size,
            }
            
            logger.info(
                f"Syncing Outlook calendar for integration {integration_id} "
                f"from {start_date_utc.isoformat()} to {end_date_utc.isoformat()}"
            )
            
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
            
            # Get user info for firm_id
            user_result = await self.session.execute(
                select(User.id, User.firm_id).where(User.id == integration.user_id)
            )
            user_row = user_result.first()
            if not user_row:
                raise SyncError(f"User {integration.user_id} not found")
            
            user_id_value = user_row[0]
            user_firm_id = user_row[1]
            calendar_integration_id = str(integration.id)
            
            # Filter events by date range
            filtered_events = self._filter_events_by_date_range(
                events, start_date_utc, end_date_utc
            )
            
            logger.info(
                f"Filtered to {len(filtered_events)} events within date range "
                f"({start_date_utc.isoformat()} to {end_date_utc.isoformat()})"
            )
            
            # Process each event
            for event in filtered_events:
                try:
                    await self._process_event(
                        event,
                        user_id_value,
                        user_firm_id,
                        calendar_integration_id,
                        result,
                    )
                except Exception as e:
                    error_msg = f"Failed to process event {event.get('id')}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    result.errors.append(error_msg)
            
            # Update integration status
            integration.last_synced_at = datetime.now(timezone.utc)
            integration.sync_error = None
            await self.session.flush()
            await self.session.refresh(integration)
            
            # Mark as successful
            result.success = True
            result.completed_at = datetime.now(timezone.utc)
            
            logger.info(
                f"Sync completed for integration {integration_id}: "
                f"{result.appointments_synced} synced, {len(result.errors)} errors"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Error syncing Outlook calendar: {str(e)}"
            logger.error(error_msg, exc_info=True)
            result.errors.append(error_msg)
            result.completed_at = datetime.now(timezone.utc)
            
            # Update integration with error
            try:
                integration = await self.calendar_repo.get_by_id(integration_id)
                if integration:
                    integration.sync_error = str(e)
                    await self.session.flush()
            except Exception:
                pass  # Don't fail if we can't update the error
            
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
        # Parse event data
        start_time_str = event["start"]["dateTime"]
        end_time_str = event["end"]["dateTime"]
        
        # Handle timezone-aware datetime strings
        if start_time_str.endswith("Z"):
            start_time_str = start_time_str.replace("Z", "+00:00")
        if end_time_str.endswith("Z"):
            end_time_str = end_time_str.replace("Z", "+00:00")
        
        start_time = datetime.fromisoformat(start_time_str)
        end_time = datetime.fromisoformat(end_time_str)
        duration_minutes = int((end_time - start_time).total_seconds() / 60)
        
        # Get contact info
        organizer = event.get("organizer", {}).get("emailAddress", {})
        contact_name = organizer.get("name", "Unknown")
        contact_email = organizer.get("address")
        
        # Generate idempotency key
        event_id = event.get("id")
        if not event_id:
            logger.warning("Skipping event: missing ID field")
            return
        
        idempotency_key = self._generate_idempotency_key(event_id)
        
        # Check if appointment already exists
        existing = await self.appointments_repo.get_by_idempotency_key(idempotency_key)
        
        event_timezone = event["start"].get("timeZone", "UTC")
        title = event.get("subject", "Untitled Event")
        notes = event.get("body", {}).get("content", "").strip() or None
        
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
                f"Created appointment from Outlook event {event_id} "
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
                f"Updated appointment from Outlook event {event_id} "
                f"(title: {title}, start: {start_time.isoformat()})"
            )
    
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
            
            # Create MSAL app
            app = ConfidentialClientApplication(
                client_id=settings.azure_ad_client_id,
                client_credential=settings.azure_ad_client_secret,
                authority=f"https://login.microsoftonline.com/{settings.azure_ad_tenant_id}",
            )
            
            # Refresh token
            token_result = app.acquire_token_by_refresh_token(
                refresh_token=integration.refresh_token,
                scopes=["https://graph.microsoft.com/Calendars.ReadWrite"],
            )
            
            if "error" in token_result:
                error_desc = token_result.get("error_description", "Unknown error")
                raise TokenRefreshError(f"Token refresh error: {error_desc}")
            
            # Update integration with new tokens
            integration.access_token = token_result["access_token"]
            if "refresh_token" in token_result:
                integration.refresh_token = token_result["refresh_token"]
            integration.token_expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=token_result.get("expires_in", 3600)
            )
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
    
    async def sync_single_event(
        self,
        integration_id: str,
        event_id: str,
    ) -> SyncResult:
        """
        Sync a single calendar event by ID (optimized for webhook processing).
        
        This method fetches only the specific event from Microsoft Graph and syncs it.
        More efficient than full calendar sync for webhook-triggered updates.
        
        Args:
            integration_id: Calendar integration ID
            event_id: Microsoft Graph event ID
        
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
            
            # Fetch single event from Microsoft Graph
            url = f"{self.graph_api_url}/me/events/{event_id}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    url,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Prefer": 'outlook.timezone="UTC"',
                    },
                )
                
                if response.status_code == 404:
                    # Event not found (may have been deleted)
                    logger.warning(
                        f"Event {event_id} not found in Outlook calendar "
                        f"(may have been deleted)"
                    )
                    result.success = True
                    result.errors.append(f"Event {event_id} not found (may be deleted)")
                    return result
                
                response.raise_for_status()
                event = response.json()
            
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
            
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error fetching event {event_id}: {e.response.status_code} {e.response.text}"
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
        Mark appointment as cancelled when Outlook event is deleted.
        
        Args:
            integration_id: Calendar integration ID
            event_id: Microsoft Graph event ID
        
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
                    f"(Outlook event {event_id} was deleted)"
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
        # Check if token is expired or about to expire (within 5 minutes)
        if (
            integration.token_expires_at
            and integration.token_expires_at <= datetime.now(timezone.utc) + timedelta(minutes=5)
        ):
            logger.info(f"Token for integration {integration.id} is expiring, refreshing...")
            result = await self.refresh_access_token(str(integration.id))
            # Refresh the integration object to get the new token
            await self.session.refresh(integration)
            return integration.access_token
        
        return integration.access_token
    
    def _normalize_to_utc(self, dt: datetime) -> datetime:
        """Normalize datetime to UTC timezone."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    
    def _filter_events_by_date_range(
        self,
        events: list,
        start_date_utc: datetime,
        end_date_utc: datetime,
    ) -> list:
        """Filter events by date range."""
        filtered_events = []
        
        for event in events:
            # Skip cancelled events
            if event.get("isCancelled"):
                continue
            
            # Validate event has required fields
            if not event.get("start") or not event.get("start").get("dateTime"):
                continue
            if not event.get("end") or not event.get("end").get("dateTime"):
                continue
            
            # Parse event times
            start_time_str = event["start"]["dateTime"]
            end_time_str = event["end"]["dateTime"]
            
            if start_time_str.endswith("Z"):
                start_time_str = start_time_str.replace("Z", "+00:00")
            if end_time_str.endswith("Z"):
                end_time_str = end_time_str.replace("Z", "+00:00")
            
            try:
                event_start = datetime.fromisoformat(start_time_str)
                event_end = datetime.fromisoformat(end_time_str)
                
                # Normalize to UTC
                event_start_utc = self._normalize_to_utc(event_start)
                event_end_utc = self._normalize_to_utc(event_end)
                
                # Include events that overlap with the date range
                if event_start_utc <= end_date_utc and event_end_utc >= start_date_utc:
                    filtered_events.append(event)
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse event date: {e}")
                continue
        
        return filtered_events
    
    def _generate_idempotency_key(self, event_id: str) -> str:
        """
        Generate idempotency key for event.
        
        Outlook event IDs can be very long, so we hash if needed.
        Max length is 128 characters.
        """
        base_key = f"outlook_{event_id}"
        if len(base_key) > 128:
            # Hash the event ID to keep it under 128 chars
            event_hash = hashlib.sha256(event_id.encode()).hexdigest()[:32]
            return f"outlook_{event_hash}"
        return base_key

