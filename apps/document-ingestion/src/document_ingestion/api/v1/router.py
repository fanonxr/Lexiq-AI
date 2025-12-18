"""API v1 router aggregation."""

from fastapi import APIRouter

from document_ingestion.api.v1 import admin, health

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
router.include_router(health.router)
router.include_router(admin.router)


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
        "service": "document-ingestion",
        "endpoints": {
            "health": "/api/v1/health",
            "ready": "/api/v1/ready",
            "admin": {
                "queues": "/api/v1/admin/queues",
            },
        },
    }

