"""Rate limiting service using Redis.

This service provides rate limiting functionality for API endpoints,
particularly for authentication endpoints to prevent brute force attacks.
"""

import logging
from typing import Optional
from datetime import datetime, timedelta

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None  # type: ignore

from api_core.config import get_settings
from api_core.exceptions import RateLimitError

logger = logging.getLogger(__name__)
settings = get_settings()


class RateLimitService:
    """Service for rate limiting using Redis."""

    def __init__(self):
        """Initialize rate limit service."""
        self._redis_client: Optional[redis.Redis] = None
        self._enabled = REDIS_AVAILABLE and settings.redis.url

    async def _get_redis_client(self) -> Optional[redis.Redis]:
        """Get or create Redis client."""
        if not self._enabled:
            return None

        if self._redis_client is None:
            try:
                self._redis_client = redis.from_url(
                    settings.redis.url,
                    password=settings.redis.password,
                    decode_responses=settings.redis.decode_responses,
                    socket_timeout=settings.redis.socket_timeout,
                    socket_connect_timeout=settings.redis.socket_connect_timeout,
                )
                # Test connection
                await self._redis_client.ping()
                logger.debug("Redis client connected for rate limiting")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis for rate limiting: {e}")
                self._enabled = False
                return None

        return self._redis_client

    async def check_rate_limit(
        self,
        key: str,
        max_attempts: int,
        window_seconds: int,
    ) -> tuple[bool, Optional[int]]:
        """
        Check if rate limit is exceeded.

        Args:
            key: Unique key for rate limiting (e.g., email address, IP address)
            max_attempts: Maximum number of attempts allowed
            window_seconds: Time window in seconds

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
            - is_allowed: True if request is allowed, False if rate limited
            - retry_after_seconds: Seconds until rate limit resets (None if allowed)
        """
        if not self._enabled:
            # If Redis is not available, allow the request (fail open)
            logger.debug("Rate limiting disabled (Redis not available), allowing request")
            return True, None

        try:
            client = await self._get_redis_client()
            if not client:
                return True, None

            # Use sliding window log algorithm
            now = datetime.utcnow()
            window_start = now - timedelta(seconds=window_seconds)

            # Get current count
            pipe = client.pipeline()
            # Remove old entries (older than window_start)
            pipe.zremrangebyscore(key, 0, window_start.timestamp())
            # Count current entries
            pipe.zcard(key)
            # Add current request
            pipe.zadd(key, {str(now.timestamp()): now.timestamp()})
            # Set expiration
            pipe.expire(key, window_seconds)
            results = await pipe.execute()

            current_count = results[1]  # Count after removing old entries

            if current_count >= max_attempts:
                # Rate limit exceeded
                # Get the oldest entry to calculate retry_after
                oldest = await client.zrange(key, 0, 0, withscores=True)
                if oldest:
                    oldest_timestamp = oldest[0][1]
                    retry_after = int(window_start.timestamp() + window_seconds - now.timestamp())
                    retry_after = max(1, retry_after)  # At least 1 second
                    return False, retry_after
                return False, window_seconds

            return True, None

        except Exception as e:
            # If Redis fails, allow the request (fail open)
            logger.warning(f"Rate limiting check failed: {e}, allowing request")
            return True, None

    async def increment_attempt(self, key: str, window_seconds: int) -> None:
        """
        Increment attempt counter for rate limiting.

        Args:
            key: Unique key for rate limiting
            window_seconds: Time window in seconds
        """
        if not self._enabled:
            return

        try:
            client = await self._get_redis_client()
            if not client:
                return

            now = datetime.utcnow()
            # Add current attempt
            await client.zadd(key, {str(now.timestamp()): now.timestamp()})
            # Set expiration
            await client.expire(key, window_seconds)

        except Exception as e:
            logger.warning(f"Failed to increment rate limit counter: {e}")

    async def reset_rate_limit(self, key: str) -> None:
        """
        Reset rate limit for a key.

        Args:
            key: Unique key for rate limiting
        """
        if not self._enabled:
            return

        try:
            client = await self._get_redis_client()
            if not client:
                return

            await client.delete(key)

        except Exception as e:
            logger.warning(f"Failed to reset rate limit: {e}")

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis_client:
            try:
                await self._redis_client.close()
                self._redis_client = None
            except Exception as e:
                logger.warning(f"Error closing Redis connection: {e}")


# Global rate limit service instance
_rate_limit_service: Optional[RateLimitService] = None


def get_rate_limit_service() -> RateLimitService:
    """Get global rate limit service instance."""
    global _rate_limit_service
    if _rate_limit_service is None:
        _rate_limit_service = RateLimitService()
    return _rate_limit_service

