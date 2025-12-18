"""FastAPI dependencies for the Cognitive Orchestrator service."""

from typing import Optional

from fastapi import Header, Request, HTTPException, status
from redis.asyncio import ConnectionPool

from cognitive_orch.config import get_settings
from cognitive_orch.services.state_service import StateService, get_state_service
from cognitive_orch.utils.logging import get_logger

logger = get_logger("dependencies")
settings = get_settings()


async def get_request_id(
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID")
) -> Optional[str]:
    """
    Extract request ID from header.
    
    If not provided, the middleware will generate one.
    This dependency is optional and mainly for documentation purposes.
    """
    return x_request_id


async def get_state_service_dependency(request: Request) -> StateService:
    """
    Get StateService instance from app state.
    
    The Redis connection pool is stored in app.state.redis_pool during startup.
    This dependency retrieves it and returns a StateService instance.
    
    Args:
        request: FastAPI request object.
    
    Returns:
        StateService instance.
    
    Raises:
        HTTPException: If Redis pool is not available.
    """
    redis_pool: Optional[ConnectionPool] = getattr(request.app.state, "redis_pool", None)
    
    if redis_pool is None:
        logger.error("Redis pool not available in app state")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="State service is not available (Redis connection not initialized)",
        )
    
    # Get or create state service with the Redis pool
    return get_state_service(redis_pool=redis_pool)


# Future dependencies will be added here:
# - Authentication/authorization (when integrated with Core API)
# - Rate limiting
# - Request validation helpers

