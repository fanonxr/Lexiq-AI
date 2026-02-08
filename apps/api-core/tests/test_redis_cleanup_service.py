"""Unit tests for Redis cleanup (terminate-account conversation keys)."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from api_core.services.redis_cleanup_service import (
    CONVERSATION_KEY_PREFIX,
    delete_conversation_keys,
)


@pytest.mark.asyncio
async def test_delete_conversation_keys_empty_list_no_op():
    """Empty conversation_ids returns without connecting to Redis."""
    await delete_conversation_keys([])
    # No exception, no Redis connection (get_settings not required to return valid url)


@pytest.mark.asyncio
async def test_delete_conversation_keys_skips_when_redis_url_empty():
    """When Redis URL is empty, returns without connecting."""
    with patch("api_core.services.redis_cleanup_service.get_settings") as mock_settings:
        mock_settings.return_value.redis = MagicMock(
            url="",
            password=None,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
        )
        await delete_conversation_keys(["conv-1", "conv-2"])
    # No redis.from_url call (we return early)


@pytest.mark.asyncio
async def test_delete_conversation_keys_deletes_keys():
    """Calls Redis delete for each conversation key and closes client."""
    mock_client = MagicMock()
    mock_client.delete = AsyncMock(return_value=1)
    mock_client.aclose = AsyncMock()

    with patch("api_core.services.redis_cleanup_service.get_settings") as mock_settings:
        mock_settings.return_value.redis = MagicMock(
            url="redis://localhost:6379/0",
            password=None,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
        )
        with patch(
            "redis.asyncio.from_url",
            return_value=mock_client,
        ):
            await delete_conversation_keys(["cid-a", "cid-b"])

    assert mock_client.delete.await_count == 2
    calls = [c[0][0] for c in mock_client.delete.call_args_list]
    assert calls == [
        f"{CONVERSATION_KEY_PREFIX}cid-a",
        f"{CONVERSATION_KEY_PREFIX}cid-b",
    ]
    mock_client.aclose.assert_awaited_once()
