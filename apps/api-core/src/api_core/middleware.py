"""Custom middleware for FastAPI."""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from api_core.config import get_settings
from api_core.utils.logging import get_logger, log_request, set_request_id

logger = get_logger("middleware")
settings = get_settings()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add request ID to all requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or get request ID from header
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        set_request_id(request_id)

        # Add request ID to response headers
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware to log request processing time."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log request
        log_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        # Add timing header
        response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"

        return response


class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log unhandled exceptions."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            from api_core.utils.logging import log_error

            log_error(
                e,
                context={
                    "method": request.method,
                    "path": request.url.path,
                    "client_ip": request.client.host if request.client else None,
                },
            )
            raise


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Only add Strict-Transport-Security in production (HTTPS required)
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Content Security Policy (can be customized per environment)
        if settings.is_production:
            # Strict CSP for production
            csp = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self'; "
                "frame-ancestors 'none';"
            )
        else:
            # More permissive CSP for development
            csp = "default-src 'self' 'unsafe-inline' 'unsafe-eval';"
        response.headers["Content-Security-Policy"] = csp

        return response


def setup_cors_middleware(app: ASGIApp) -> None:
    """Set up CORS middleware."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.origins,
        allow_credentials=settings.cors.allow_credentials,
        allow_methods=settings.cors.allow_methods,
        allow_headers=settings.cors.allow_headers,
        max_age=settings.cors.max_age,
    )
    logger.info(
        f"CORS middleware configured: origins={settings.cors.origins}, "
        f"methods={settings.cors.allow_methods}"
    )


def setup_middleware(app: ASGIApp) -> None:
    """Set up all middleware for the FastAPI application.
    
    Middleware order matters - they execute in reverse order:
    1. SecurityHeaders (last to execute, first to add) - adds security headers
    2. ErrorLogging (catches exceptions) - logs unhandled errors
    3. Timing (measures performance) - logs request duration
    4. RequestID (tracks requests) - generates/uses request IDs
    5. CORS (handles preflight) - first to execute, handles CORS
    """
    # Add middleware in reverse execution order
    # CORS must be first (last in list) to handle preflight requests
    setup_cors_middleware(app)
    # RequestID should be early to track all requests
    app.add_middleware(RequestIDMiddleware)
    # Timing measures the full request processing time
    app.add_middleware(TimingMiddleware)
    # ErrorLogging catches exceptions before they reach exception handlers
    app.add_middleware(ErrorLoggingMiddleware)
    # SecurityHeaders adds headers to all responses
    app.add_middleware(SecurityHeadersMiddleware)
    
    logger.info(
        "Middleware configured: CORS, RequestID, Timing, ErrorLogging, SecurityHeaders"
    )
