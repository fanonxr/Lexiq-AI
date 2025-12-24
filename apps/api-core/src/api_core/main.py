"""FastAPI application entry point.

This module creates and configures the FastAPI application instance with:
- Application metadata and OpenAPI documentation
- Middleware (CORS, RequestID, Timing, ErrorLogging, SecurityHeaders)
- Exception handlers (APIException, HTTPException, ValidationError, general)
- API routers (v1)
- Health check endpoints (/health, /ready)
- Startup/shutdown lifecycle management (database, Redis, Azure AD B2C)
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from api_core.config import get_settings
from api_core.database import close_db, init_db
from api_core.exceptions import APIException
from api_core.middleware import setup_middleware
from api_core.services.ingestion_queue import publisher as ingestion_publisher
from api_core.utils.logging import get_logger, log_error, setup_logging

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
    - Database connection pool
    - Redis connection (if needed in future)
    - Azure AD B2C client (lazy initialization, no explicit startup needed)
    """
    # Startup
    logger.info("Starting API Core service...")
    try:
        # Initialize database connection pool
        logger.info("Initializing database connection...")
        await init_db()
        logger.info("Database connection initialized successfully")

        # Redis connection initialization
        # Note: Redis is currently used lazily (on-demand connections)
        # If connection pooling is needed, initialize here
        # For now, Redis connections are created when needed
        logger.info("Redis will be connected on-demand")

        # Azure AD B2C / Entra ID client initialization
        # Note: AzureADB2CClient uses lazy initialization for JWKS fetching
        # No explicit startup needed - JWKS are fetched on first token validation
        from api_core.config import get_settings
        settings = get_settings()
        if settings.azure_ad_b2c.is_configured:
            auth_type = "Azure AD B2C" if settings.azure_ad_b2c.is_b2c else "Microsoft Entra ID"
            logger.info(f"{auth_type} client will initialize on first use")
        else:
            logger.warning("Azure AD B2C / Entra ID is not configured - token validation will fail")

        # RabbitMQ publisher for ingestion jobs
        try:
            await ingestion_publisher.connect()
            app.state.ingestion_publisher = ingestion_publisher
            logger.info("RabbitMQ ingestion publisher initialized successfully")
        except Exception as e:
            # Don't fail startup in development; uploads will fail to enqueue instead
            logger.error(f"Failed to initialize RabbitMQ publisher: {e}", exc_info=True)
            app.state.ingestion_publisher = None

        logger.info("API Core service started successfully")
        yield
    except Exception as e:
        logger.error(f"Failed to start API Core service: {e}", exc_info=True)
        raise
    finally:
        # Shutdown
        logger.info("Shutting down API Core service...")
        try:
            # Close database connection pool
            await close_db()
            logger.info("Database connection closed successfully")

            # Close RabbitMQ publisher
            try:
                if hasattr(app.state, "ingestion_publisher") and app.state.ingestion_publisher:
                    await app.state.ingestion_publisher.close()
                    logger.info("RabbitMQ ingestion publisher closed successfully")
            except Exception as e:
                logger.error(f"Error closing RabbitMQ publisher: {e}", exc_info=True)

            # Close Redis connections if any were opened
            # (Currently not needed as connections are on-demand)

            logger.info("API Core service shut down successfully")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)


# Create FastAPI application
app = FastAPI(
    title="LexiqAI API Core",
    description=(
        "Enterprise-grade voice orchestration platform API for the legal industry. "
        "Provides authentication, user management, billing, and dashboard APIs."
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
            "name": "authentication",
            "description": "User authentication and authorization endpoints",
        },
        {
            "name": "users",
            "description": "User management and profile operations",
        },
        {
            "name": "billing",
            "description": "Billing, subscriptions, invoices, and usage tracking",
        },
        {
            "name": "dashboard",
            "description": "Dashboard statistics, activity feeds, and analytics",
        },
        {
            "name": "v1",
            "description": "API v1 information and metadata",
        },
    ],
    # Contact information (can be customized)
    contact={
        "name": "LexiqAI Support",
        "email": "support@lexiqai.com",  # Update with actual support email
    },
    # License information (can be customized)
    license_info={
        "name": "Proprietary",
        # "url": "https://example.com/license",  # Add if applicable
    },
)

# Set up middleware
setup_middleware(app)

# Include API routers
from api_core.api.v1.router import router as v1_router

app.include_router(v1_router)


# Exception handlers
@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """Handle custom API exceptions."""
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


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    logger.debug("Health check requested")
    from api_core.config import get_settings
    settings = get_settings()
    
    # Check auth configuration
    auth_config = {
        "configured": settings.azure_ad_b2c.is_configured,
        "type": "Azure AD B2C" if settings.azure_ad_b2c.is_b2c else "Microsoft Entra ID" if settings.azure_ad_b2c.is_configured else "Not configured",
        "has_tenant_id": bool(settings.azure_ad_b2c.tenant_id),
        "has_client_id": bool(settings.azure_ad_b2c.client_id),
    }
    
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "environment": settings.environment.value,
        "auth": auth_config,
    }


@app.get("/debug/storage")
async def debug_storage():
    """Debug endpoint to check storage configuration."""
    from api_core.config import get_settings
    settings = get_settings()
    storage = settings.storage
    
    return {
        "configured": storage.is_configured,
        "account_name": storage.account_name,
        "has_connection_string": bool(storage.connection_string),
        "connection_string_preview": storage.connection_string[:50] + "..." if storage.connection_string and len(storage.connection_string) > 50 else storage.connection_string,
        "has_account_key": bool(storage.account_key),
        "use_managed_identity": storage.use_managed_identity,
    }

@app.get("/debug/auth")
async def debug_auth_config():
    """Debug endpoint to check authentication configuration (development only)."""
    from api_core.config import get_settings
    settings = get_settings()
    
    if settings.is_production:
        return {"error": "This endpoint is only available in development"}
    
    auth_config = settings.azure_ad_b2c
    
    return {
        "configured": auth_config.is_configured,
        "is_b2c": auth_config.is_b2c,
        "type": "Azure AD B2C" if auth_config.is_b2c else "Microsoft Entra ID" if auth_config.is_configured else "Not configured",
        "tenant_id": auth_config.tenant_id,
        "client_id": auth_config.client_id,
        "has_policy": bool(auth_config.policy_signup_signin),
        "instance": auth_config.instance,
        "authority": auth_config.authority,
        "has_client_secret": bool(auth_config.client_secret),
        "client_secret_length": len(auth_config.client_secret) if auth_config.client_secret else 0,
        "jwks_url": None if not auth_config.is_configured else (
            f"{auth_config.instance}/{auth_config.tenant_id}/discovery/v2.0/keys" 
            if not auth_config.is_b2c 
            else f"{auth_config.instance.format(tenant=auth_config.tenant_id)}/{auth_config.tenant_id}/{auth_config.policy_signup_signin}/discovery/v2.0/keys"
        ),
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint with database connectivity check."""
    from api_core.database import check_connection

    logger.debug("Readiness check requested")
    db_connected = await check_connection()

    if not db_connected:
        logger.warning("Readiness check failed: database not connected")
        return {
            "status": "not_ready",
            "app_name": settings.app_name,
            "environment": settings.environment.value,
            "database": "disconnected",
        }, 503

    logger.debug("Readiness check passed: all systems operational")
    return {
        "status": "ready",
        "app_name": settings.app_name,
        "environment": settings.environment.value,
        "database": "connected",
    }
