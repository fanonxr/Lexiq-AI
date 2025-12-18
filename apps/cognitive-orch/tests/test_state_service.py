"""Unit tests for State Service."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cognitive_orch.models.conversation import ConversationMetadata, ConversationState, Message
from cognitive_orch.services.state_service import StateService
from cognitive_orch.utils.errors import StateError


@pytest.fixture
def mock_redis_pool():
    """Create a mock Redis connection pool."""
    pool = MagicMock()
    return pool


@pytest.fixture
def state_service(mock_redis_pool):
    """Create StateService instance with mocked Redis pool."""
    with patch("cognitive_orch.services.state_service.get_settings") as mock_settings:
        mock_settings.return_value.redis.conversation_ttl = 3600
        mock_settings.return_value.context_window.max_history_messages = 50
        service = StateService(redis_pool=mock_redis_pool)
        return service


@pytest.fixture
def sample_conversation_state():
    """Create a sample conversation state for testing."""
    metadata = ConversationMetadata(
        user_id="user-123",
        firm_id="firm-456",
        call_id="call-789",
    )
    return ConversationState(
        conversation_id="conv-001",
        metadata=metadata,
        messages=[
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!"),
        ],
    )


class TestStateService:
    """Test StateService methods."""

    def test_get_key(self, state_service):
        """Test Redis key generation."""
        key = state_service._get_key("conv-123")
        assert key == "conversation:conv-123"

    @pytest.mark.asyncio
    async def test_get_conversation_state_found(self, state_service, sample_conversation_state):
        """Test retrieving an existing conversation state."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            return_value=sample_conversation_state.model_dump_json()
        )
        
        with patch.object(state_service, "_get_redis_client", return_value=mock_client):
            result = await state_service.get_conversation_state("conv-001")
            
            assert result is not None
            assert result.conversation_id == "conv-001"
            assert len(result.messages) == 2
            mock_client.get.assert_called_once_with("conversation:conv-001")

    @pytest.mark.asyncio
    async def test_get_conversation_state_not_found(self, state_service):
        """Test retrieving a non-existent conversation state."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=None)
        
        with patch.object(state_service, "_get_redis_client", return_value=mock_client):
            result = await state_service.get_conversation_state("conv-999")
            
            assert result is None
            mock_client.get.assert_called_once_with("conversation:conv-999")

    @pytest.mark.asyncio
    async def test_save_conversation_state(self, state_service, sample_conversation_state):
        """Test saving conversation state."""
        mock_client = AsyncMock()
        mock_client.setex = AsyncMock(return_value=True)
        
        with patch.object(state_service, "_get_redis_client", return_value=mock_client):
            await state_service.save_conversation_state(sample_conversation_state)
            
            mock_client.setex.assert_called_once()
            call_args = mock_client.setex.call_args
            assert call_args[0][0] == "conversation:conv-001"
            assert call_args[0][1] == 3600  # TTL
            assert isinstance(call_args[0][2], str)  # JSON string

    @pytest.mark.asyncio
    async def test_append_message(self, state_service, sample_conversation_state):
        """Test appending a message to conversation."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            return_value=sample_conversation_state.model_dump_json()
        )
        mock_client.setex = AsyncMock(return_value=True)
        
        with patch.object(state_service, "_get_redis_client", return_value=mock_client):
            await state_service.append_message(
                conversation_id="conv-001",
                role="user",
                content="New message",
            )
            
            # Verify get was called to retrieve state
            mock_client.get.assert_called_once()
            # Verify setex was called to save updated state
            mock_client.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_append_message_conversation_not_found(self, state_service):
        """Test appending message to non-existent conversation."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=None)
        
        with patch.object(state_service, "_get_redis_client", return_value=mock_client):
            with pytest.raises(StateError) as exc_info:
                await state_service.append_message(
                    conversation_id="conv-999",
                    role="user",
                    content="Message",
                )
            
            assert "Conversation not found" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_create_conversation(self, state_service):
        """Test creating a new conversation."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=None)  # Conversation doesn't exist
        mock_client.setex = AsyncMock(return_value=True)
        
        with patch.object(state_service, "_get_redis_client", return_value=mock_client):
            state = await state_service.create_conversation(
                conversation_id="conv-new",
                user_id="user-123",
                firm_id="firm-456",
            )
            
            assert state.conversation_id == "conv-new"
            assert state.metadata.user_id == "user-123"
            assert state.metadata.firm_id == "firm-456"
            mock_client.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_conversation_already_exists(self, state_service, sample_conversation_state):
        """Test creating a conversation that already exists."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            return_value=sample_conversation_state.model_dump_json()
        )
        
        with patch.object(state_service, "_get_redis_client", return_value=mock_client):
            with pytest.raises(StateError) as exc_info:
                await state_service.create_conversation(
                    conversation_id="conv-001",
                    user_id="user-123",
                )
            
            assert "already exists" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_clear_conversation(self, state_service):
        """Test clearing a conversation."""
        mock_client = AsyncMock()
        mock_client.delete = AsyncMock(return_value=1)
        
        with patch.object(state_service, "_get_redis_client", return_value=mock_client):
            await state_service.clear_conversation("conv-001")
            
            mock_client.delete.assert_called_once_with("conversation:conv-001")

    @pytest.mark.asyncio
    async def test_extend_ttl(self, state_service):
        """Test extending conversation TTL."""
        mock_client = AsyncMock()
        mock_client.exists = AsyncMock(return_value=True)
        mock_client.ttl = AsyncMock(return_value=1800)  # 30 minutes remaining
        mock_client.expire = AsyncMock(return_value=True)
        
        with patch.object(state_service, "_get_redis_client", return_value=mock_client):
            await state_service.extend_ttl("conv-001", additional_seconds=3600)
            
            mock_client.expire.assert_called_once()
            # Should extend by 3600 seconds (1 hour)
            call_args = mock_client.expire.call_args
            assert call_args[0][0] == "conversation:conv-001"
            assert call_args[0][1] == 5400  # 1800 + 3600

    @pytest.mark.asyncio
    async def test_extend_ttl_conversation_not_found(self, state_service):
        """Test extending TTL for non-existent conversation."""
        mock_client = AsyncMock()
        mock_client.exists = AsyncMock(return_value=False)
        
        with patch.object(state_service, "_get_redis_client", return_value=mock_client):
            with pytest.raises(StateError) as exc_info:
                await state_service.extend_ttl("conv-999")
            
            assert "Conversation not found" in exc_info.value.message


class TestConversationState:
    """Test ConversationState model methods."""

    def test_add_message(self, sample_conversation_state):
        """Test adding a message to conversation state."""
        initial_count = len(sample_conversation_state.messages)
        
        sample_conversation_state.add_message(
            role="user",
            content="Test message",
        )
        
        assert len(sample_conversation_state.messages) == initial_count + 1
        assert sample_conversation_state.messages[-1].role == "user"
        assert sample_conversation_state.messages[-1].content == "Test message"

    def test_get_messages_for_llm(self, sample_conversation_state):
        """Test getting messages formatted for LLM."""
        messages = sample_conversation_state.get_messages_for_llm()
        
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "Hi there!"

    def test_get_messages_for_llm_with_limit(self, sample_conversation_state):
        """Test getting limited messages for LLM."""
        # Add more messages
        for i in range(5):
            sample_conversation_state.add_message(role="user", content=f"Message {i}")
        
        # Request only 3 most recent
        messages = sample_conversation_state.get_messages_for_llm(max_messages=3)
        
        assert len(messages) == 3
        # Should be the last 3 messages
        assert messages[0]["content"] == "Message 2"
        assert messages[1]["content"] == "Message 3"
        assert messages[2]["content"] == "Message 4"

    def test_truncate_old_messages(self, sample_conversation_state):
        """Test truncating old messages."""
        # Add many messages
        for i in range(10):
            sample_conversation_state.add_message(role="user", content=f"Message {i}")
        
        # Truncate to 5 messages
        removed = sample_conversation_state.truncate_old_messages(5)
        
        assert len(sample_conversation_state.messages) == 5
        assert removed == 7  # 12 total - 5 kept = 7 removed
        # Should keep the most recent messages
        assert sample_conversation_state.messages[0].content == "Message 5"

    def test_add_tool_execution(self, sample_conversation_state):
        """Test adding tool execution to history."""
        initial_count = len(sample_conversation_state.tool_execution_history)
        
        sample_conversation_state.add_tool_execution(
            tool_name="book_appointment",
            parameters={"date": "2024-01-01"},
            result={"success": True},
        )
        
        assert len(sample_conversation_state.tool_execution_history) == initial_count + 1
        execution = sample_conversation_state.tool_execution_history[-1]
        assert execution["tool_name"] == "book_appointment"
        assert execution["parameters"] == {"date": "2024-01-01"}
        assert execution["result"] == {"success": True}

