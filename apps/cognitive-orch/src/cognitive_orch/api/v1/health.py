"""Health check endpoints."""

from fastapi import APIRouter, status

from cognitive_orch.config import get_settings
from cognitive_orch.utils.logging import get_logger

logger = get_logger("health")
settings = get_settings()

router = APIRouter(tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Health check endpoint.
    
    Returns basic service health status. This endpoint does not check
    external dependencies and will always return healthy if the service is running.
    """
    logger.debug("Health check requested")
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "environment": settings.environment.value,
    }


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check():
    """
    Readiness check endpoint.
    
    Checks connectivity to external dependencies:
    - Redis (for conversation state)
    - Qdrant (for vector search)
    
    Returns 503 if any dependency is unavailable.
    """
    logger.debug("Readiness check requested")
    
    checks = {
        "redis": False,
        "qdrant": False,
    }
    
    # Check Redis connection
    try:
        import redis.asyncio as redis
        
        redis_client = redis.from_url(
            settings.redis.url,
            password=settings.redis.password,
            decode_responses=settings.redis.decode_responses,
            socket_timeout=settings.redis.socket_timeout,
            socket_connect_timeout=settings.redis.socket_connect_timeout,
        )
        await redis_client.ping()
        await redis_client.aclose()
        checks["redis"] = True
        logger.debug("Redis connection check passed")
    except Exception as e:
        logger.warning(f"Redis connection check failed: {e}")
        checks["redis"] = False
    
    # Check Qdrant connection
    try:
        from qdrant_client import QdrantClient
        
        qdrant_client = QdrantClient(
            url=settings.qdrant.url,
            api_key=settings.qdrant.api_key,
            timeout=settings.qdrant.timeout,
        )
        # Try to get collections list as a connectivity test
        qdrant_client.get_collections()
        checks["qdrant"] = True
        logger.debug("Qdrant connection check passed")
    except Exception as e:
        logger.warning(f"Qdrant connection check failed: {e}")
        checks["qdrant"] = False
    
    # Determine overall readiness
    all_ready = all(checks.values())
    
    if not all_ready:
        logger.warning(f"Readiness check failed: {checks}")
        return {
            "status": "not_ready",
            "app_name": settings.app_name,
            "environment": settings.environment.value,
            "checks": checks,
        }, status.HTTP_503_SERVICE_UNAVAILABLE
    
    logger.debug("Readiness check passed: all systems operational")
    return {
        "status": "ready",
        "app_name": settings.app_name,
        "environment": settings.environment.value,
        "checks": checks,
    }

