"""Tests for logging configuration."""

import logging

from integration_worker.utils.logging import get_logger, setup_logging


def test_get_logger():
    """Test that get_logger returns correct logger."""
    logger = get_logger("test")
    
    assert isinstance(logger, logging.Logger)
    assert logger.name == "integration_worker.test"


def test_setup_logging(monkeypatch):
    """Test that logging is configured correctly."""
    # Clear log_level env var to use default
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    
    # Clear singleton to get fresh settings
    import integration_worker.config
    integration_worker.config._settings = None
    
    setup_logging()
    
    logger = logging.getLogger("integration_worker")
    assert logger.level == logging.INFO  # Default log level
    assert len(logger.handlers) > 0

