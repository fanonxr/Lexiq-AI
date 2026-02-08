"""API v1 router aggregation.

This module aggregates all v1 API routers and applies common configuration.
All v1 endpoints are prefixed with `/api/v1`.

Routers included:
- Authentication (`/api/v1/auth/*`)
- User Management (`/api/v1/users/*`)
- Billing & Subscriptions (`/api/v1/billing/*`)
- Dashboard (`/api/v1/dashboard/*`)
- Knowledge Base (`/api/v1/knowledge/*`)

Common middleware (applied at application level in main.py):
- CORS: Cross-origin resource sharing
- RequestID: Request tracking and correlation
- Timing: Request processing time measurement
- ErrorLogging: Unhandled exception logging
- SecurityHeaders: Security headers (CSP, HSTS, etc.)

Authentication:
- Most endpoints require authentication via `get_current_active_user` dependency
- Public endpoints: `/api/v1/auth/*` (login, signup), `/api/v1/billing/plans`

Rate Limiting:
- Rate limiting middleware is not yet implemented
- Structure is ready for future implementation (RateLimitError exception exists)
- Consider implementing with slowapi or similar library
"""

from fastapi import APIRouter

from api_core.api.v1 import (
    agent,
    appointments,
    auth,
    auth_google,
    billing,
    calendar_integrations,
    calls,
    conversations,
    dashboard,
    firms,
    jobs,
    knowledge,
    leads,
    notifications,
    twilio,
    users,
)

# Create v1 API router with version prefix
router = APIRouter(
    prefix="/api/v1",
    tags=["v1"],
    responses={
        404: {"description": "Not found"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)

# Include all v1 API sub-routers
# Order matters for OpenAPI documentation grouping
router.include_router(auth.router)
router.include_router(auth_google.router)
router.include_router(users.router)
router.include_router(billing.router)
router.include_router(dashboard.router)
router.include_router(knowledge.router)
router.include_router(agent.router)
router.include_router(appointments.router)
router.include_router(calendar_integrations.router)
router.include_router(leads.router)
router.include_router(notifications.router)
router.include_router(firms.router)
router.include_router(conversations.router)
router.include_router(calls.router)
router.include_router(twilio.router)
router.include_router(jobs.router)


@router.get(
    "/",
    summary="API Information",
    description="Get API version and status information",
    tags=["v1"],
)
async def api_info():
    """
    Get API v1 information.

    Returns the API version and status. This endpoint is public and does not
    require authentication.

    Returns:
        dict: API version and status information
    """
    return {
        "version": "v1",
        "status": "active",
        "endpoints": {
            "auth": "/api/v1/auth",
            "users": "/api/v1/users",
            "billing": "/api/v1/billing",
            "dashboard": "/api/v1/dashboard",
            "knowledge": "/api/v1/knowledge",
            "agent": "/api/v1/agent",
            "appointments": "/api/v1/appointments",
            "calendar-integrations": "/api/v1/calendar-integrations",
            "leads": "/api/v1/leads",
            "notifications": "/api/v1/notifications",
            "firms": "/api/v1/firms",
            "conversations": "/api/v1/conversations",
            "calls": "/api/v1/calls",
            "twilio": "/api/v1/twilio",
        },
    }
