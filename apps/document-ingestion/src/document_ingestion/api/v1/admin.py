"""Admin endpoints for queue management and monitoring."""

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from document_ingestion.config import get_settings
from document_ingestion.utils.logging import get_logger

logger = get_logger("admin")
settings = get_settings()

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/queues", status_code=status.HTTP_200_OK)
async def get_queue_status(request: Request):
    """
    Get status of RabbitMQ queues and exchanges.

    Returns information about:
    - Main queue (document-ingestion)
    - Dead-letter queue (document-ingestion-dlq)
    - Main exchange (document-ingestion-exchange)
    - Dead-letter exchange (document-ingestion-exchange-dlx)
    """
    logger.debug("Queue status check requested")

    try:
        # Get connection from app state
        if not hasattr(request.app.state, "rabbitmq_connection"):
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "error": {
                        "message": "RabbitMQ connection not available",
                        "code": "RABBITMQ_NOT_CONNECTED",
                    }
                },
            )

        connection = request.app.state.rabbitmq_connection
        if connection is None or connection.is_closed:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "error": {
                        "message": "RabbitMQ connection is closed",
                        "code": "RABBITMQ_CONNECTION_CLOSED",
                    }
                },
            )

        # Verify queues
        from document_ingestion.services.queue_setup import verify_queues

        queue_status = await verify_queues(connection)

        return {
            "status": "success",
            "queues": queue_status,
        }
    except Exception as e:
        logger.error(f"Failed to get queue status: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "message": f"Failed to get queue status: {str(e)}",
                    "code": "QUEUE_STATUS_ERROR",
                }
            },
        )

