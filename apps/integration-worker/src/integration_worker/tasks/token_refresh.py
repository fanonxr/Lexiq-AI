"""Token refresh Celery tasks."""

import logging
from datetime import datetime, timedelta, timezone

from celery import shared_task

from integration_worker.database.session import get_session
from integration_worker.services.outlook_service import OutlookService
from integration_worker.utils.async_helpers import run_async
from integration_worker.utils.errors import TokenRefreshError

logger = logging.getLogger(__name__)


@shared_task(
    name="integration_worker.tasks.token_refresh.refresh_expiring_tokens",
)
def refresh_expiring_tokens() -> dict:
    """
    Refresh tokens that are expiring within 24 hours.
    
    This task is triggered by Celery Beat every hour.
    """
    async def _run_refresh():
        async with get_session() as session:
            from integration_worker.database.repositories import (
                CalendarIntegrationRepository,
            )
            
            repo = CalendarIntegrationRepository(session)
            
            # Find integrations with tokens expiring in next 24 hours
            expiring_soon = datetime.now(timezone.utc) + timedelta(hours=24)
            integrations = await repo.get_with_expiring_tokens(expiring_soon)
            
            logger.info(f"Found {len(integrations)} integrations with expiring tokens")
            
            refreshed = 0
            errors = 0
            
            for integration in integrations:
                try:
                    if integration.integration_type == "outlook":
                        service = OutlookService(session)
                        result = await service.refresh_access_token(str(integration.id))
                        if result.success:
                            refreshed += 1
                            logger.info(f"Refreshed token for integration {integration.id}")
                        else:
                            errors += 1
                            logger.error(f"Failed to refresh token for {integration.id}: {result.error}")
                    elif integration.integration_type == "google":
                        # Google token refresh (Phase 5)
                        logger.info(f"Skipping Google token refresh for {integration.id} (Phase 5)")
                        pass
                except TokenRefreshError as e:
                    logger.error(
                        f"Token refresh error for {integration.id}: {e}",
                        exc_info=True,
                    )
                    errors += 1
                except Exception as e:
                    logger.error(
                        f"Unexpected error refreshing token for {integration.id}: {e}",
                        exc_info=True,
                    )
                    errors += 1
            
            return {"refreshed": refreshed, "errors": errors}
    
    result = run_async(_run_refresh())
    
    logger.info(
        f"Refreshed {result['refreshed']} tokens ({result['errors']} errors)"
    )
    
    return result

