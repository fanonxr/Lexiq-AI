"""API v1 router aggregation.

This module aggregates all v1 API routers and applies common configuration.
All v1 endpoints are prefixed with `/api/v1`.
"""

from fastapi import APIRouter

from cognitive_orch.api.v1 import health, orchestrator, test

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
router.include_router(test.router)
router.include_router(orchestrator.router)


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
        "service": "cognitive-orch",
        "endpoints": {
            "health": "/api/v1/health",
            "ready": "/api/v1/ready",
            "orchestrator": {
                "chat": "/api/v1/orchestrator/chat",
                "conversations": "/api/v1/orchestrator/conversations/{id}",
            },
            "test": {
                "llm": "/api/v1/test/llm",
                "llm_stream": "/api/v1/test/llm/stream",
                "tools": "/api/v1/test/tools/definitions",
                "tool_loop": "/api/v1/test/llm/tools",
            },
        },
    }

