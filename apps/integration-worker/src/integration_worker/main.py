"""
Integration Worker - Main entry point.

This module serves as the entry point for the webhook server.
For Celery worker, use: celery -A integration_worker.celery_app worker
"""

from integration_worker.workers.webhook_server import app

# Export app for uvicorn
__all__ = ["app"]

