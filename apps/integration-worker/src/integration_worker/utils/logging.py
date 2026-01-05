"""Logging configuration."""

import logging
import sys

from integration_worker.config import get_settings


def setup_logging() -> None:
    """Configure logging for the service."""
    settings = get_settings()
    
    # Create logger
    logger = logging.getLogger("integration_worker")
    logger.setLevel(settings.log_level)
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(settings.log_level)
    
    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Get logger instance."""
    return logging.getLogger(f"integration_worker.{name}")

