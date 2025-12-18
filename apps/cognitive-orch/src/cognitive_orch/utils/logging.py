"""Logging configuration for the Cognitive Orchestrator service."""

import json
import logging
import sys
from contextvars import ContextVar
from typing import Any, Dict, Optional

from cognitive_orch.config import get_settings

# Request ID context variable for tracking requests across async operations
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)

# Logger instance
_logger: Optional[logging.Logger] = None


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging in production."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add request ID if available
        request_id = request_id_var.get()
        if request_id:
            log_data["request_id"] = request_id

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        # Add any additional attributes
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
                "extra_fields",
            ]:
                log_data[key] = value

        return json.dumps(log_data, default=str)


class StandardFormatter(logging.Formatter):
    """Standard formatter for development (human-readable)."""

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with request ID."""
        # Add request ID to record if available
        request_id = request_id_var.get()
        if not hasattr(record, "request_id"):
            record.request_id = request_id or "N/A"

        return super().format(record)


def setup_logging() -> logging.Logger:
    """Set up logging configuration based on environment."""
    global _logger

    if _logger is not None:
        return _logger

    settings = get_settings()

    # Get root logger
    logger = logging.getLogger("cognitive_orch")
    logger.setLevel(getattr(logging, settings.log_level))

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.log_level))

    # Choose formatter based on environment
    if settings.is_production:
        # Use JSON formatter in production for structured logging
        formatter = JSONFormatter()
    else:
        # Use standard formatter in development for readability
        formatter = StandardFormatter()

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Set log level for third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("litellm").setLevel(logging.INFO if settings.debug else logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # Prevent duplicate logs from propagating to root logger
    logger.propagate = False

    _logger = logger
    logger.info(
        f"Logging configured: level={settings.log_level}, "
        f"environment={settings.environment.value}, "
        f"format={'JSON' if settings.is_production else 'Standard'}"
    )

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance."""
    if name:
        return logging.getLogger(f"cognitive_orch.{name}")
    return logging.getLogger("cognitive_orch")


def set_request_id(request_id: str) -> None:
    """Set the request ID for the current context."""
    request_id_var.set(request_id)


def get_request_id() -> Optional[str]:
    """Get the current request ID."""
    return request_id_var.get()


def log_request(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    **kwargs: Any,
) -> None:
    """Log an HTTP request."""
    logger = get_logger("http")
    extra_fields = {
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": duration_ms,
        **kwargs,
    }
    logger.info(
        f"{method} {path} - {status_code} - {duration_ms:.2f}ms",
        extra={"extra_fields": extra_fields},
    )


def log_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> None:
    """Log an error with context."""
    logger = get_logger("error")
    extra_fields = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context or {},
        **kwargs,
    }
    logger.error(
        f"Error: {type(error).__name__}: {str(error)}",
        exc_info=True,
        extra={"extra_fields": extra_fields},
    )


# Initialize logging on module import
# Note: This will be called when the module is imported
# In production, you may want to delay this until after settings are loaded
try:
    setup_logging()
except Exception:
    # If settings aren't available yet, logging will be set up later
    pass

