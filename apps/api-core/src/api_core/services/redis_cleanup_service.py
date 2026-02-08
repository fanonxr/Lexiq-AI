"""Redis cleanup on account termination: delete conversation state keys (conversation:{id})."""

from __future__ import annotations

import logging
from typing import List

from api_core.config import get_settings

logger = logging.getLogger(__name__)

CONVERSATION_KEY_PREFIX = "conversation:"  # matches Cognitive Orchestrator state key


async def delete_conversation_keys(conversation_ids: List[str]) -> None:
    """Delete Redis keys for the given conversation IDs. No-op if empty or Redis not configured."""
    if not conversation_ids:
        return
    settings = get_settings()
    if not (settings.redis.url and settings.redis.url.strip()):
        return
    try:
        import redis.asyncio as redis

        client = redis.from_url(
            settings.redis.url,
            password=settings.redis.password,
            decode_responses=settings.redis.decode_responses,
            socket_timeout=settings.redis.socket_timeout,
            socket_connect_timeout=settings.redis.socket_connect_timeout,
        )
        try:
            keys = [f"{CONVERSATION_KEY_PREFIX}{cid}" for cid in conversation_ids]
            for key in keys:
                try:
                    await client.delete(key)
                except Exception as e:
                    logger.warning(f"Redis delete key {key} failed: {e}")
            logger.info(
                f"Deleted Redis conversation keys for {len(conversation_ids)} conversations"
            )
        finally:
            await client.aclose()
    except Exception as e:
        logger.warning(
            f"Redis cleanup failed for {len(conversation_ids)} conversations: {e}. Continuing."
        )
