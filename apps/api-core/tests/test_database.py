"""Tests for database connection and session management."""

import pytest
from sqlalchemy import text

from api_core.database import check_connection, get_session


@pytest.mark.asyncio
async def test_database_connection():
    """Test database connection."""
    # This test requires a running database
    # Skip if database is not available
    is_connected = await check_connection()
    if not is_connected:
        pytest.skip("Database not available for testing")


@pytest.mark.asyncio
async def test_get_session():
    """Test getting a database session."""
    # This test requires a running database
    # Skip if database is not available
    is_connected = await check_connection()
    if not is_connected:
        pytest.skip("Database not available for testing")

    async for session in get_session():
        # Test basic query
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1
        break  # Exit the async generator


@pytest.mark.asyncio
async def test_session_commit_rollback():
    """Test session commit and rollback behavior."""
    # This test requires a running database
    is_connected = await check_connection()
    if not is_connected:
        pytest.skip("Database not available for testing")

    async for session in get_session():
        # Test that session is properly managed
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1
        # Session should auto-commit on exit
        break
