"""FastAPI application entry point.

This module creates and configures the FastAPI application instance with:
- Application metadata and OpenAPI documentation
- Middleware (CORS, RequestID, Timing, ErrorLogging, SecurityHeaders)
- Exception handlers (OrchestratorException, HTTPException, ValidationError, general)
- API routers (v1)
- Health check endpoints (/health, /ready)
- Startup/shutdown lifecycle management (Redis, Qdrant connections)
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from cognitive_orch.config import get_settings
from cognitive_orch.middleware import setup_middleware
from cognitive_orch.utils.errors import OrchestratorException
from cognitive_orch.utils.logging import get_logger, log_error, setup_logging

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
    - Redis connection pool (for conversation state)
    - Qdrant client (for vector search)
    - gRPC server (for Voice Gateway communication)
    """
    # Startup
    logger.info("Starting Cognitive Orchestrator service...")
    grpc_server = None
    try:
        # Initialize Redis connection pool
        logger.info("Initializing Redis connection...")
        try:
            import redis.asyncio as redis
            
            # Create Redis connection pool (will be used by state service)
            redis_pool = redis.ConnectionPool.from_url(
                settings.redis.url,
                password=settings.redis.password,
                decode_responses=settings.redis.decode_responses,
                socket_timeout=settings.redis.socket_timeout,
                socket_connect_timeout=settings.redis.socket_connect_timeout,
                max_connections=50,
            )
            # Test connection
            test_client = redis.Redis(connection_pool=redis_pool)
            await test_client.ping()
            await test_client.aclose()
            
            # Store Redis pool in app state for services to use
            app.state.redis_pool = redis_pool
            
            logger.info("Redis connection initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection: {e}", exc_info=True)
            if settings.is_production:
                raise  # Fail fast in production
        
        # Initialize Qdrant client
        logger.info("Initializing Qdrant connection...")
        try:
            from qdrant_client import QdrantClient
            
            # Create Qdrant client (will be used by RAG service)
            qdrant_client = QdrantClient(
                url=settings.qdrant.url,
                api_key=settings.qdrant.api_key,
                timeout=settings.qdrant.timeout,
                prefer_grpc=settings.qdrant.prefer_grpc,
            )
            # Test connection
            qdrant_client.get_collections()
            
            # Store Qdrant client in app state for services to use
            app.state.qdrant_client = qdrant_client
            
            logger.info("Qdrant connection initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant connection: {e}", exc_info=True)
            if settings.is_production:
                raise  # Fail fast in production
        
        # Initialize gRPC server
        if settings.grpc.enabled:
            logger.info("Initializing gRPC server...")
            logger.info(f"gRPC settings: enabled={settings.grpc.enabled}, port={settings.grpc.port}, max_workers={settings.grpc.max_workers}")
            try:
                from cognitive_orch.grpc.server import GRPCServer
                
                # Get Redis pool from app state (initialized earlier)
                redis_pool = getattr(app.state, "redis_pool", None)
                
                # Explicitly pass the port and redis_pool to ensure it's correct
                grpc_port = settings.grpc.port
                logger.info(f"Creating gRPC server with port: {grpc_port}")
                grpc_server = GRPCServer(port=grpc_port, redis_pool=redis_pool)
                await grpc_server.start()
                
                # Store gRPC server in app state
                app.state.grpc_server = grpc_server
                
                logger.info("gRPC server initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize gRPC server: {e}", exc_info=True)
                if settings.is_production:
                    raise  # Fail fast in production
        else:
            logger.info("gRPC server is disabled (GRPC_ENABLED=false)")
        
        logger.info("Cognitive Orchestrator service started successfully")
        yield
    except Exception as e:
        logger.error(f"Failed to start Cognitive Orchestrator service: {e}", exc_info=True)
        raise
    finally:
        # Shutdown
        logger.info("Shutting down Cognitive Orchestrator service...")
        try:
            # Stop gRPC server
            if grpc_server:
                logger.info("Stopping gRPC server...")
                await grpc_server.stop()
            
            # Close Redis connections
            # Note: Connection pool will be closed when service stops
            logger.info("Redis connections will be closed on service stop")
            
            # Qdrant client doesn't require explicit cleanup
            logger.info("Qdrant client cleanup completed")
            
            logger.info("Cognitive Orchestrator service shut down successfully")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)


# Create FastAPI application
app = FastAPI(
    title="LexiqAI Cognitive Orchestrator",
    description=(
        "The Brain of LexiqAI - handles LLM routing, RAG, conversation state management, "
        "and tool execution for the enterprise voice orchestration platform."
    ),
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,  # Hide docs in production
    redoc_url="/redoc" if settings.debug else None,  # Hide redoc in production
    openapi_url="/openapi.json" if settings.debug else None,  # Hide OpenAPI schema in production
    debug=settings.debug,
    lifespan=lifespan,
    # OpenAPI metadata customization
    openapi_tags=[
        {
            "name": "health",
            "description": "Health check and readiness endpoints",
        },
        {
            "name": "v1",
            "description": "API v1 information and metadata",
        },
    ],
    # Contact information
    contact={
        "name": "LexiqAI Support",
        "email": "support@lexiqai.com",
    },
    # License information
    license_info={
        "name": "Proprietary",
    },
)

# Set up middleware
setup_middleware(app)

# Include API routers
from cognitive_orch.api.v1.router import router as v1_router

app.include_router(v1_router)

# Include health check endpoints at root level (for Kubernetes/Docker health checks)
# These are also available at /api/v1/health and /api/v1/ready
@app.get("/health", tags=["health"], include_in_schema=False)
async def root_health_check():
    """Root-level health check endpoint (for Kubernetes/Docker)."""
    from cognitive_orch.api.v1.health import health_check
    return await health_check()


@app.get("/ready", tags=["health"], include_in_schema=False)
async def root_readiness_check():
    """Root-level readiness check endpoint (for Kubernetes/Docker)."""
    from cognitive_orch.api.v1.health import readiness_check
    return await readiness_check()


# Exception handlers
@app.exception_handler(OrchestratorException)
async def orchestrator_exception_handler(
    request: Request, exc: OrchestratorException
) -> JSONResponse:
    """Handle custom Orchestrator exceptions."""
    log_error(
        exc,
        context={
            "method": request.method,
            "path": request.url.path,
            "status_code": exc.status_code,
            "code": exc.code,
        },
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle HTTP exceptions (404, etc.)."""
    # Don't log 404s as errors, just as warnings
    if exc.status_code == 404:
        logger.warning(
            f"404 Not Found: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": 404,
            },
        )
    else:
        log_error(
            exc,
            context={
                "method": request.method,
                "path": request.url.path,
                "status_code": exc.status_code,
            },
        )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.detail,
                "code": "HTTP_ERROR",
                "status_code": exc.status_code,
                "details": {},
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle request validation errors."""
    errors = []
    for error in exc.errors():
        errors.append(
            {
                "field": ".".join(str(loc) for loc in error.get("loc", [])),
                "message": error.get("msg"),
                "type": error.get("type"),
            }
        )

    logger.warning(
        f"Validation error: {request.method} {request.url.path}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "validation_errors": errors,
        },
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "message": "Validation failed",
                "code": "VALIDATION_ERROR",
                "status_code": 422,
                "details": {
                    "validation_errors": errors,
                },
            }
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all other unhandled exceptions."""
    log_error(
        exc,
        context={
            "method": request.method,
            "path": request.url.path,
            "unhandled": True,
        },
    )

    # Don't expose internal error details in production
    if settings.is_production:
        message = "An internal server error occurred"
    else:
        message = str(exc)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "message": message,
                "code": "INTERNAL_SERVER_ERROR",
                "status_code": 500,
                "details": {} if settings.is_production else {"exception_type": type(exc).__name__},
            }
        },
    )

