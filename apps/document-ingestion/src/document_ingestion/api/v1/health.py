"""Health check endpoints."""

from fastapi import APIRouter, Request, status

from document_ingestion.config import get_settings
from document_ingestion.utils.logging import get_logger

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
async def readiness_check(request: Request):
    """
    Readiness check endpoint.

    Checks connectivity to external dependencies:
    - RabbitMQ (for message queue)
    - Azure Blob Storage (for file downloads)
    - Qdrant (for vector storage)
    - API Core (for status updates)

    Returns 503 if any critical dependency is unavailable.
    """
    logger.debug("Readiness check requested")

    checks = {
        "rabbitmq": False,
        "storage": False,
        "embeddings": False,
        "qdrant": False,
        "api_core": False,
    }

    # Check RabbitMQ connection and queues
    try:
        import aio_pika

        # Use existing connection from app state if available
        connection = None
        if hasattr(request.app.state, "rabbitmq_connection"):
            connection = request.app.state.rabbitmq_connection
            if connection and not connection.is_closed:
                checks["rabbitmq"] = True
                logger.debug("RabbitMQ connection check passed (using existing connection)")
            else:
                # Fallback to new connection
                connection = await aio_pika.connect_robust(settings.rabbitmq.url)
                await connection.close()
                checks["rabbitmq"] = True
                logger.debug("RabbitMQ connection check passed (new connection)")
        else:
            # Fallback to new connection
            connection = await aio_pika.connect_robust(settings.rabbitmq.url)
            await connection.close()
            checks["rabbitmq"] = True
            logger.debug("RabbitMQ connection check passed (new connection)")
    except Exception as e:
        logger.warning(f"RabbitMQ connection check failed: {e}")
        checks["rabbitmq"] = False

    # Check Azure Blob Storage connection
    try:
        from azure.identity import DefaultAzureCredential
        from azure.storage.blob.aio import BlobServiceClient

        if settings.storage.use_managed_identity:
            account_url = f"https://{settings.storage.account_name}.blob.core.windows.net"
            credential = DefaultAzureCredential()
            client = BlobServiceClient(account_url=account_url, credential=credential)
        elif settings.storage.connection_string:
            client = BlobServiceClient.from_connection_string(settings.storage.connection_string)
        else:
            raise ValueError("Storage not configured")

        # Try to list containers as a connectivity test
        async with client:
            async for _ in client.list_containers(max_results=1):
                break
        checks["storage"] = True
        logger.debug("Storage connection check passed")
    except Exception as e:
        logger.warning(f"Storage connection check failed: {e}")
        checks["storage"] = False

    # Check embeddings configuration (provider keys present)
    try:
        checks["embeddings"] = settings.embedding.is_configured
        if checks["embeddings"]:
            logger.debug(
                "Embeddings configuration check passed",
                extra={
                    "provider": settings.embedding.provider.value,
                    "model": settings.embedding.resolved_model_name,
                },
            )
        else:
            logger.warning(
                "Embeddings configuration check failed: missing required env vars",
                extra={"provider": settings.embedding.provider.value},
            )
    except Exception as e:
        logger.warning(f"Embeddings configuration check failed: {e}")
        checks["embeddings"] = False

    # Check Qdrant connection
    try:
        from qdrant_client import QdrantClient

        qdrant_client = QdrantClient(
            url=settings.qdrant.url,
            api_key=settings.qdrant.api_key,
            timeout=5,  # Shorter timeout for health check
        )
        # Try to get collections list as a connectivity test
        qdrant_client.get_collections()
        checks["qdrant"] = True
        logger.debug("Qdrant connection check passed")
    except Exception as e:
        logger.warning(f"Qdrant connection check failed: {e}")
        checks["qdrant"] = False

    # Check API Core connection
    try:
        import httpx

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.api_core.url}/health")
            if response.status_code == 200:
                checks["api_core"] = True
                logger.debug("API Core connection check passed")
            else:
                checks["api_core"] = False
    except Exception as e:
        logger.warning(f"API Core connection check failed: {e}")
        checks["api_core"] = False

    # Determine overall readiness
    # RabbitMQ, Storage, and Embeddings are critical. Qdrant and API Core are important but not blocking.
    critical_ready = checks["rabbitmq"] and checks["storage"] and checks["embeddings"]
    all_ready = all(checks.values())

    if not critical_ready:
        logger.warning(f"Readiness check failed (critical): {checks}")
        return {
            "status": "not_ready",
            "app_name": settings.app_name,
            "environment": settings.environment.value,
            "checks": checks,
        }, status.HTTP_503_SERVICE_UNAVAILABLE

    if not all_ready:
        logger.warning(f"Readiness check partial (non-critical): {checks}")

    logger.debug("Readiness check passed: all systems operational")
    return {
        "status": "ready",
        "app_name": settings.app_name,
        "environment": settings.environment.value,
        "checks": checks,
    }

