"""State Service for managing conversation state in Redis."""

import json
from datetime import datetime
from typing import Optional

import redis.asyncio as redis
from redis.asyncio import ConnectionPool, Redis

from cognitive_orch.config import get_settings
from cognitive_orch.models.conversation import ConversationState
from cognitive_orch.utils.errors import StateError
from cognitive_orch.utils.logging import get_logger

logger = get_logger("state_service")
settings = get_settings()


class StateService:
    """Service for managing conversation state in Redis.

    This service handles:
    - Storing and retrieving conversation state
    - Managing conversation history
    - TTL-based expiration
    - Context window management
    """

    def __init__(self, redis_pool: Optional[ConnectionPool] = None):
        """Initialize State Service with Redis connection.

        Args:
            redis_pool: Optional Redis connection pool. If not provided,
                       creates a new one from settings.
        """
        self.settings = get_settings()
        
        if redis_pool:
            self.redis_pool = redis_pool
        else:
            # Create connection pool from settings
            self.redis_pool = redis.ConnectionPool.from_url(
                self.settings.redis.url,
                password=self.settings.redis.password,
                decode_responses=self.settings.redis.decode_responses,
                socket_timeout=self.settings.redis.socket_timeout,
                socket_connect_timeout=self.settings.redis.socket_connect_timeout,
                max_connections=50,
            )
        
        self.ttl = self.settings.redis.conversation_ttl
        self.max_history_messages = self.settings.context_window.max_history_messages

    def _get_redis_client(self) -> Redis:
        """Get a Redis client from the connection pool."""
        return redis.Redis(connection_pool=self.redis_pool)

    def _get_key(self, conversation_id: str) -> str:
        """Generate Redis key for conversation state.
        
        Args:
            conversation_id: Unique conversation identifier.
        
        Returns:
            Redis key string.
        """
        return f"conversation:{conversation_id}"

    async def get_conversation_state(
        self, conversation_id: str
    ) -> Optional[ConversationState]:
        """Retrieve conversation state from Redis.

        Args:
            conversation_id: Unique conversation identifier.

        Returns:
            ConversationState if found, None otherwise.

        Raises:
            StateError: If Redis operation fails.
        """
        try:
            client = self._get_redis_client()
            key = self._get_key(conversation_id)
            
            data = await client.get(key)
            if data is None:
                logger.debug(f"Conversation state not found: {conversation_id}")
                return None
            
            # Parse JSON data
            state_dict = json.loads(data)
            state = ConversationState(**state_dict)
            
            logger.debug(f"Retrieved conversation state: {conversation_id}")
            return state

        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to parse conversation state JSON: {conversation_id}",
                extra={"error": str(e)},
            )
            raise StateError(
                message=f"Failed to parse conversation state: {str(e)}",
                details={"conversation_id": conversation_id},
            ) from e
        except Exception as e:
            logger.error(
                f"Failed to retrieve conversation state: {conversation_id}",
                extra={"error": str(e), "conversation_id": conversation_id},
                exc_info=True,
            )
            raise StateError(
                message=f"Failed to retrieve conversation state: {str(e)}",
                details={"conversation_id": conversation_id},
            ) from e

    async def save_conversation_state(
        self, state: ConversationState
    ) -> None:
        """Save conversation state to Redis with TTL.

        Args:
            state: ConversationState to save.

        Raises:
            StateError: If Redis operation fails.
        """
        try:
            client = self._get_redis_client()
            key = self._get_key(state.conversation_id)
            
            # Update metadata timestamp
            from datetime import datetime
            state.metadata.updated_at = state.metadata.updated_at or datetime.utcnow()
            
            # Truncate old messages if needed
            if len(state.messages) > self.max_history_messages:
                removed = state.truncate_old_messages(self.max_history_messages)
                logger.debug(
                    f"Truncated {removed} old messages from conversation: {state.conversation_id}"
                )
            
            # Serialize to JSON (handles datetime serialization)
            data = state.model_dump_json()
            
            # Save with TTL
            await client.setex(key, self.ttl, data)
            
            logger.debug(
                f"Saved conversation state: {state.conversation_id}, TTL: {self.ttl}s"
            )

        except Exception as e:
            logger.error(
                f"Failed to save conversation state: {state.conversation_id}",
                extra={"error": str(e), "conversation_id": state.conversation_id},
                exc_info=True,
            )
            raise StateError(
                message=f"Failed to save conversation state: {str(e)}",
                details={"conversation_id": state.conversation_id},
            ) from e

    async def append_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        tool_calls: Optional[list] = None,
        tool_call_id: Optional[str] = None,
        model: Optional[str] = None,
        tokens: Optional[int] = None,
    ) -> None:
        """Append a message to conversation history.

        This method retrieves the current state, adds the message, and saves it back.

        Args:
            conversation_id: Unique conversation identifier.
            role: Message role (user, assistant, system, tool).
            content: Message content.
            tool_calls: Optional tool calls (for assistant messages).
            tool_call_id: Optional tool call ID (for tool messages).
            model: Optional model name used.
            tokens: Optional token count.

        Raises:
            StateError: If conversation doesn't exist or Redis operation fails.
        """
        try:
            # Get existing state or create new
            state = await self.get_conversation_state(conversation_id)
            
            if state is None:
                raise StateError(
                    message=f"Conversation not found: {conversation_id}",
                    details={"conversation_id": conversation_id},
                )
            
            # Add message
            state.add_message(
                role=role,
                content=content,
                tool_calls=tool_calls,
                tool_call_id=tool_call_id,
                model=model,
                tokens=tokens,
            )
            
            # Update token count if provided
            if tokens:
                state.metadata.total_tokens += tokens
            
            # Save updated state
            await self.save_conversation_state(state)
            
            logger.debug(
                f"Appended {role} message to conversation: {conversation_id}"
            )

        except StateError:
            raise
        except Exception as e:
            logger.error(
                f"Failed to append message to conversation: {conversation_id}",
                extra={"error": str(e), "conversation_id": conversation_id},
                exc_info=True,
            )
            raise StateError(
                message=f"Failed to append message: {str(e)}",
                details={"conversation_id": conversation_id},
            ) from e

    async def create_conversation(
        self,
        conversation_id: str,
        user_id: str,
        firm_id: Optional[str] = None,
        call_id: Optional[str] = None,
    ) -> ConversationState:
        """Create a new conversation state.

        Args:
            conversation_id: Unique conversation identifier.
            user_id: User ID.
            firm_id: Optional firm/Organization ID.
            call_id: Optional call ID (if from voice call).

        Returns:
            New ConversationState instance.

        Raises:
            StateError: If conversation already exists or Redis operation fails.
        """
        try:
            # Check if conversation already exists
            existing = await self.get_conversation_state(conversation_id)
            if existing is not None:
                raise StateError(
                    message=f"Conversation already exists: {conversation_id}",
                    details={"conversation_id": conversation_id},
                )
            
            # Create new state
            from cognitive_orch.models.conversation import ConversationMetadata
            
            metadata = ConversationMetadata(
                user_id=user_id,
                firm_id=firm_id,
                call_id=call_id,
            )
            
            state = ConversationState(
                conversation_id=conversation_id,
                metadata=metadata,
            )
            
            # Save to Redis
            await self.save_conversation_state(state)
            
            logger.info(f"Created new conversation: {conversation_id}")
            return state

        except StateError:
            raise
        except Exception as e:
            logger.error(
                f"Failed to create conversation: {conversation_id}",
                extra={"error": str(e), "conversation_id": conversation_id},
                exc_info=True,
            )
            raise StateError(
                message=f"Failed to create conversation: {str(e)}",
                details={"conversation_id": conversation_id},
            ) from e

    async def clear_conversation(self, conversation_id: str) -> None:
        """Clear conversation state from Redis.

        Args:
            conversation_id: Unique conversation identifier.

        Raises:
            StateError: If Redis operation fails.
        """
        try:
            client = self._get_redis_client()
            key = self._get_key(conversation_id)
            
            deleted = await client.delete(key)
            
            if deleted:
                logger.info(f"Cleared conversation state: {conversation_id}")
            else:
                logger.debug(f"Conversation not found for deletion: {conversation_id}")

        except Exception as e:
            logger.error(
                f"Failed to clear conversation: {conversation_id}",
                extra={"error": str(e), "conversation_id": conversation_id},
                exc_info=True,
            )
            raise StateError(
                message=f"Failed to clear conversation: {str(e)}",
                details={"conversation_id": conversation_id},
            ) from e

    async def extend_ttl(self, conversation_id: str, additional_seconds: Optional[int] = None) -> None:
        """Extend the TTL of a conversation.

        Args:
            conversation_id: Unique conversation identifier.
            additional_seconds: Additional seconds to add to TTL. If None, resets to default TTL.

        Raises:
            StateError: If conversation doesn't exist or Redis operation fails.
        """
        try:
            client = self._get_redis_client()
            key = self._get_key(conversation_id)
            
            # Check if key exists
            exists = await client.exists(key)
            if not exists:
                raise StateError(
                    message=f"Conversation not found: {conversation_id}",
                    details={"conversation_id": conversation_id},
                )
            
            # Calculate new TTL
            if additional_seconds is not None:
                current_ttl = await client.ttl(key)
                if current_ttl > 0:
                    new_ttl = current_ttl + additional_seconds
                else:
                    new_ttl = self.ttl + additional_seconds
            else:
                new_ttl = self.ttl
            
            # Extend TTL
            await client.expire(key, new_ttl)
            
            logger.debug(
                f"Extended TTL for conversation: {conversation_id}, new TTL: {new_ttl}s"
            )

        except StateError:
            raise
        except Exception as e:
            logger.error(
                f"Failed to extend TTL for conversation: {conversation_id}",
                extra={"error": str(e), "conversation_id": conversation_id},
                exc_info=True,
            )
            raise StateError(
                message=f"Failed to extend TTL: {str(e)}",
                details={"conversation_id": conversation_id},
            ) from e

    async def close(self) -> None:
        """Close Redis connection pool."""
        try:
            await self.redis_pool.aclose()
            logger.debug("State service Redis connection pool closed")
        except Exception as e:
            logger.warning(f"Error closing Redis connection pool: {e}")


# Global service instance
_state_service: Optional[StateService] = None


def get_state_service(redis_pool: Optional[ConnectionPool] = None) -> StateService:
    """Get the global State service instance.
    
    Args:
        redis_pool: Optional Redis connection pool. Only used on first call.
    
    Returns:
        StateService instance.
    """
    global _state_service
    if _state_service is None:
        _state_service = StateService(redis_pool=redis_pool)
    return _state_service

