"""Database connection and session management for cognitive-orch.

This module provides database connectivity for the Long-Term Memory feature,
allowing the cognitive orchestrator to store and retrieve client interaction history.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from cognitive_orch.config import get_settings

logger = logging.getLogger(__name__)

# Global engine instance
_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_database_url() -> str:
    """Get the async database URL from settings."""
    settings = get_settings()
    return settings.database.async_url


def create_engine() -> AsyncEngine:
    """Create and configure the SQLAlchemy async engine."""
    settings = get_settings()
    db_url = get_database_url()

    # Connection pool configuration
    pool_config = {
        "pool_size": settings.database.pool_size,
        "max_overflow": settings.database.max_overflow,
        "pool_timeout": settings.database.pool_timeout,
        "pool_recycle": settings.database.pool_recycle,
        "pool_pre_ping": True,  # Verify connections before using them
        "echo": settings.database.echo,  # Log SQL queries in debug mode
    }

    # Create async engine
    engine = create_async_engine(db_url, **pool_config)

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


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get or create the global session factory."""
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get an async database session.
    
    This is a FastAPI dependency that provides a database session per request.
    The session is automatically closed after the request completes.
    
    Usage:
        @app.get("/example")
        async def example(session: AsyncSession = Depends(get_session)):
            result = await session.execute(select(Client))
            return result.scalars().all()
    
    Yields:
        AsyncSession: Database session
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_session_context():
    """
    Get a database session as a context manager.
    
    This is useful for services that need to manage their own sessions
    outside of the FastAPI dependency injection system.
    
    Usage:
        async with get_session_context() as session:
            result = await session.execute(select(Client))
            clients = result.scalars().all()
    
    Yields:
        AsyncSession: Database session
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_engine() -> None:
    """Close the database engine and dispose of all connections."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database engine closed")


async def check_connection() -> bool:
    """Check if database connection is available."""
    try:
        from sqlalchemy import text

        engine = get_engine()
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            row = result.fetchone()
            if row is not None and len(row) > 0 and row[0] == 1:
                return True
            return False
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False

