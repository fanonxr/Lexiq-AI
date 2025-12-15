"""Database engine and connection pool for Azure PostgreSQL Flexible Server."""

import logging
from typing import Optional

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from api_core.config import get_settings

logger = logging.getLogger(__name__)

# Global engine instance
_engine: Optional[AsyncEngine] = None


def get_database_url() -> str:
    """Get the database URL, converting to async format if needed."""
    settings = get_settings()
    db_url = settings.database.url

    # Convert postgresql:// to postgresql+asyncpg:// for async operations
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgresql+psycopg2://"):
        db_url = db_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)

    return db_url


def create_engine() -> AsyncEngine:
    """Create and configure the SQLAlchemy async engine."""
    settings = get_settings()
    db_url = get_database_url()

    # Connection pool configuration for async engines
    # For async engines, we use NullPool or AsyncAdaptedQueuePool
    # AsyncAdaptedQueuePool is the default for asyncpg, so we don't need to specify it
    pool_config = {
        "pool_size": settings.database.pool_size,
        "max_overflow": settings.database.max_overflow,
        "pool_timeout": settings.database.pool_timeout,
        "pool_recycle": settings.database.pool_recycle,
        "pool_pre_ping": True,  # Verify connections before using them
        # Don't specify poolclass - asyncpg uses AsyncAdaptedQueuePool by default
        "echo": settings.database.echo,  # Log SQL queries in debug mode
    }

    # For Azure PostgreSQL, asyncpg automatically uses AsyncAdaptedQueuePool
    # which provides connection pooling for async operations
    if settings.is_development and settings.debug:
        logger.info("Using async connection pooling for development")
    else:
        logger.info("Using async connection pooling for production")

    # Create async engine
    # Note: For async engines, SQLAlchemy automatically uses AsyncAdaptedQueuePool
    # when using asyncpg, so we don't need to specify poolclass
    engine = create_async_engine(
        db_url,
        **pool_config,
    )

    # Note: Event listeners for async engines work differently
    # For asyncpg, connection-level settings can be set via connection URL parameters
    # or in the connection initialization
    # Event listeners on sync_engine don't work the same way for async engines

    logger.info(
        f"Database engine created: pool_size={pool_config['pool_size']}, "
        f"max_overflow={pool_config['max_overflow']}"
    )

    return engine


def get_engine() -> AsyncEngine:
    """Get or create the global database engine."""
    global _engine
    if _engine is None:
        _engine = create_engine()
    return _engine


async def close_engine() -> None:
    """Close the database engine and dispose of all connections."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        logger.info("Database engine closed")


async def check_connection() -> bool:
    """Check if database connection is available."""
    try:
        from sqlalchemy import text

        engine = get_engine()
        async with engine.connect() as conn:
            # Execute the query - conn.execute() is async
            result = await conn.execute(text("SELECT 1"))
            # Fetch the result - fetchone() is synchronous, don't await it
            row = result.fetchone()
            # Verify we got the expected result
            if row is not None and len(row) > 0 and row[0] == 1:
                return True
            return False
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False
