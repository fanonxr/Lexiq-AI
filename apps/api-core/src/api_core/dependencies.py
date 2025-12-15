"""FastAPI dependencies."""

from api_core.database.session import get_session

# Re-export database session dependency for convenience
__all__ = ["get_session"]
