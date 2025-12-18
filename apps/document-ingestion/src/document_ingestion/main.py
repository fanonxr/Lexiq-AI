"""FastAPI application entry point.

This module creates and configures the FastAPI application instance with:
- Application metadata and OpenAPI documentation
- Middleware (CORS, RequestID, Timing, ErrorLogging)
- Exception handlers
- API routers (v1)
- Health check endpoints (/health, /ready)
- Startup/shutdown lifecycle management (RabbitMQ connections)
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from document_ingestion.config import get_settings
from document_ingestion.utils.errors import IngestionException
from document_ingestion.utils.logging import get_logger, log_error, setup_logging

# Set up logging first
setup_logging()
logger = get_logger("main")

# Get settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifespan events.

    Handles startup and shutdown of:
    - RabbitMQ connection (for message queue)
    - Qdrant client (for vector storage)
    """
    # Startup
    logger.info("Starting Document Ingestion service...")
    try:
        # Small delay to ensure dependencies are fully ready (even if containers are healthy)
        if settings.is_development:
            import asyncio
            logger.info("Waiting 3 seconds for dependencies to be fully ready...")
            await asyncio.sleep(3)
        
        # Initialize RabbitMQ connection
        logger.info(f"Initializing RabbitMQ connection to {settings.rabbitmq.url}...")
        try:
            import aio_pika

            # Test connection with retry logic for development
            max_retries = 10 if settings.is_development else 3
            retry_delay = 3  # seconds
            connection = None
            
            for attempt in range(max_retries):
                try:
                    connection = await aio_pika.connect_robust(settings.rabbitmq.url)
                    # Test the connection by checking if it's open
                    if connection.is_closed:
                        raise Exception("Connection is closed")
                    logger.info(f"RabbitMQ connection successful on attempt {attempt + 1}")
                    break
                except Exception as retry_error:
                    error_msg = str(retry_error)
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"RabbitMQ connection attempt {attempt + 1}/{max_retries} failed: {error_msg}. "
                            f"Retrying in {retry_delay} seconds... (URL: {settings.rabbitmq.url})"
                        )
                        import asyncio
                        await asyncio.sleep(retry_delay)
                        # Close failed connection if it was created
                        if connection and not connection.is_closed:
                            try:
                                await connection.close()
                            except:
                                pass
                        connection = None
                    else:
                        logger.error(f"All RabbitMQ connection attempts failed. Last error: {error_msg}")
                        raise retry_error

            if connection is None or connection.is_closed:
                raise Exception("Failed to create RabbitMQ connection after all retries")

            # Store connection in app state for workers to use
            app.state.rabbitmq_connection = connection

            # Set up queues, exchanges, and dead-letter queues
            logger.info("Setting up RabbitMQ queues and exchanges...")
            try:
                from document_ingestion.services.queue_setup import setup_queues

                await setup_queues(connection)
                logger.info("RabbitMQ queue setup completed")
            except Exception as setup_error:
                logger.error(
                    f"Failed to set up RabbitMQ queues: {setup_error}",
                    exc_info=True,
                )
                if settings.is_production:
                    raise  # Fail fast in production
                else:
                    logger.warning(
                        "Queue setup failed in development mode. "
                        "Service will continue but queue operations may fail."
                    )

            logger.info("RabbitMQ connection initialized successfully")

            # Start queue consumer
            try:
                from document_ingestion.workers.queue_consumer import QueueConsumer

                consumer = QueueConsumer(connection)
                await consumer.start()
                app.state.queue_consumer = consumer
                logger.info("Queue consumer started successfully")
            except Exception as consumer_error:
                logger.error(
                    f"Failed to start queue consumer: {consumer_error}",
                    exc_info=True,
                )
                if settings.is_production:
                    raise  # Fail fast in production
                else:
                    logger.warning(
                        "Queue consumer failed to start in development mode. "
                        "Service will continue but messages won't be processed."
                    )

            # Start queue consumer
            if app.state.rabbitmq_connection:
                try:
                    from document_ingestion.workers.queue_consumer import QueueConsumer

                    consumer = QueueConsumer(app.state.rabbitmq_connection)
                    await consumer.start()
                    app.state.queue_consumer = consumer
                    logger.info("Queue consumer started successfully")
                except Exception as consumer_error:
                    logger.error(
                        f"Failed to start queue consumer: {consumer_error}",
                        exc_info=True,
                    )
                    if settings.is_production:
                        raise  # Fail fast in production
                    else:
                        logger.warning(
                            "Queue consumer failed to start in development mode. "
                            "Service will continue but messages won't be processed."
                        )
        except Exception as e:
            logger.error(f"Failed to initialize RabbitMQ connection: {e}", exc_info=True)
            logger.error(f"RabbitMQ URL: {settings.rabbitmq.url}")
            if settings.is_production:
                raise  # Fail fast in production
            else:
                # In development, log warning but continue (connection will be retried when needed)
                logger.warning(
                    "RabbitMQ connection failed in development mode. "
                    "Service will continue but queue operations will fail until connection is established. "
                    f"Check that RabbitMQ is running and accessible at {settings.rabbitmq.url}"
                )
                app.state.rabbitmq_connection = None

        # Initialize Qdrant client
        logger.info(f"Initializing Qdrant connection to {settings.qdrant.url}...")
        try:
            from qdrant_client import QdrantClient

            # Test connection with retry logic for development
            max_retries = 10 if settings.is_development else 3
            retry_delay = 3  # seconds
            qdrant_client = None
            
            for attempt in range(max_retries):
                try:
                    # Create Qdrant client (same as orchestrator)
                    qdrant_client = QdrantClient(
                        url=settings.qdrant.url,
                        api_key=settings.qdrant.api_key,
                        timeout=settings.qdrant.timeout,
                    )
                    # Test connection (same as orchestrator)
                    qdrant_client.get_collections()
                    logger.info(f"Qdrant connection successful on attempt {attempt + 1}")
                    break
                except Exception as retry_error:
                    error_msg = str(retry_error)
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Qdrant connection attempt {attempt + 1}/{max_retries} failed: {error_msg}. "
                            f"Retrying in {retry_delay} seconds... (URL: {settings.qdrant.url})"
                        )
                        import asyncio
                        await asyncio.sleep(retry_delay)
                        # Reset client for next attempt
                        qdrant_client = None
                    else:
                        logger.error(f"All Qdrant connection attempts failed. Last error: {error_msg}")
                        raise retry_error

            if qdrant_client is None:
                raise Exception("Failed to create Qdrant client after all retries")

            # Store Qdrant client in app state for services to use
            app.state.qdrant_client = qdrant_client

            logger.info("Qdrant connection initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant connection: {e}", exc_info=True)
            logger.error(f"Qdrant URL: {settings.qdrant.url}")
            if settings.is_production:
                raise  # Fail fast in production
            else:
                # In development, log warning but continue (connection will be retried when needed)
                logger.warning(
                    "Qdrant connection failed in development mode. "
                    "Service will continue but Qdrant operations will fail until connection is established. "
                    f"Check that Qdrant is running and accessible at {settings.qdrant.url}. "
                    "You can test connectivity with: curl http://qdrant:6333/collections"
                )
                app.state.qdrant_client = None

        logger.info("Document Ingestion service started successfully")
        yield

    except Exception as e:
        logger.error(f"Failed to start Document Ingestion service: {e}", exc_info=True)
        raise
    finally:
        # Shutdown
        logger.info("Shutting down Document Ingestion service...")

        # Stop queue consumer
        if hasattr(app.state, "queue_consumer"):
            try:
                consumer = app.state.queue_consumer
                await consumer.stop()
                logger.info("Queue consumer stopped")
            except Exception as e:
                logger.error(f"Error stopping queue consumer: {e}", exc_info=True)

        # Close RabbitMQ connection
        if hasattr(app.state, "rabbitmq_connection"):
            try:
                connection = app.state.rabbitmq_connection
                await connection.close()
                logger.info("RabbitMQ connection closed")
            except Exception as e:
                logger.error(f"Error closing RabbitMQ connection: {e}", exc_info=True)

        # Qdrant client doesn't need explicit closing
        logger.info("Document Ingestion service shut down")


# Create FastAPI application
app = FastAPI(
    title="Document Ingestion Service",
    description="LexiqAI Document Ingestion Service - Processes knowledge base files for RAG",
    version="0.1.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure via environment in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)


# Exception handlers
@app.exception_handler(IngestionException)
async def ingestion_exception_handler(request: Request, exc: IngestionException):
    """Handle IngestionException."""
    log_error(exc, context={"path": request.url.path, "method": request.method})
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions."""
    log_error(exc, context={"path": request.url.path, "method": request.method})
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.detail,
                "code": "HTTP_ERROR",
                "status_code": exc.status_code,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    log_error(exc, context={"path": request.url.path, "method": request.method})
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "message": "Validation error",
                "code": "VALIDATION_ERROR",
                "status_code": 422,
                "details": exc.errors(),
            }
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions."""
    log_error(exc, context={"path": request.url.path, "method": request.method})
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "message": "Internal server error",
                "code": "INTERNAL_ERROR",
                "status_code": 500,
            }
        },
    )


# Include API routers
from document_ingestion.api.v1.router import router as v1_router

app.include_router(v1_router)


# Include health check endpoints at root level (for Kubernetes/Docker health checks)
# These are also available at /api/v1/health and /api/v1/ready
@app.get("/health", tags=["health"], include_in_schema=False)
async def root_health_check():
    """Root-level health check endpoint (for Kubernetes/Docker)."""
    from document_ingestion.api.v1.health import health_check
    return await health_check()


@app.get("/ready", tags=["health"], include_in_schema=False)
async def root_readiness_check():
    """Root-level readiness check endpoint (for Kubernetes/Docker)."""
    from document_ingestion.api.v1.health import readiness_check
    return await readiness_check()


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint."""
    return {
        "service": "document-ingestion",
        "version": "0.1.0",
        "status": "running",
        "environment": settings.environment.value,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "document_ingestion.main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.server.reload and settings.is_development,
        log_level=settings.log_level.lower(),
    )

