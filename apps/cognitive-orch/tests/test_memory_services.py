"""Unit tests for Long-Term Memory services.

These tests demonstrate how to test the Memory Service, Post-Call Worker,
and Prompt Builder components.

Run with: pytest apps/cognitive-orch/tests/test_memory_services.py -v
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

# Note: In production, ensure api-core is in PYTHONPATH
# from api_core.database.models import Client, ClientMemory


@pytest.fixture
def mock_session():
    """Mock database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def mock_client():
    """Mock client object."""
    client = MagicMock()
    client.id = "client-123"
    client.firm_id = "firm-456"
    client.phone_number = "+15551234567"
    client.first_name = None
    client.last_name = None
    client.created_at = datetime.utcnow() - timedelta(days=30)
    client.last_called_at = datetime.utcnow() - timedelta(days=2)
    return client


@pytest.fixture
def mock_memories():
    """Mock client memories."""
    memories = []
    for i in range(3):
        memory = MagicMock()
        memory.id = f"memory-{i}"
        memory.client_id = "client-123"
        memory.summary_text = f"Memory {i}: Client called about case."
        memory.created_at = datetime.utcnow() - timedelta(days=i + 1)
        memories.append(memory)
    return memories


class TestMemoryService:
    """Tests for MemoryService."""

    @pytest.mark.asyncio
    async def test_identify_new_client(self, mock_session):
        """Test identifying a new client creates a record."""
        from cognitive_orch.services.memory_service import MemoryService

        # Mock database query returning no client
        result = AsyncMock()
        result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result

        # Test
        service = MemoryService(session=mock_session)
        client = await service.identify_client("firm-456", "+15551234567")

        # Assertions
        assert mock_session.add.called
        assert mock_session.commit.called

    @pytest.mark.asyncio
    async def test_identify_existing_client(self, mock_session, mock_client):
        """Test identifying an existing client updates last_called_at."""
        from cognitive_orch.services.memory_service import MemoryService

        # Mock database query returning existing client
        result = AsyncMock()
        result.scalar_one_or_none.return_value = mock_client
        mock_session.execute.return_value = result

        # Test
        service = MemoryService(session=mock_session)
        client = await service.identify_client("firm-456", "+15551234567")

        # Assertions
        assert client == mock_client
        assert mock_session.commit.called

    @pytest.mark.asyncio
    async def test_get_client_dossier(self, mock_session, mock_memories):
        """Test retrieving and formatting client dossier."""
        from cognitive_orch.services.memory_service import MemoryService

        # Mock database query returning memories
        result = AsyncMock()
        result.scalars.return_value.all.return_value = mock_memories
        mock_session.execute.return_value = result

        # Test
        service = MemoryService(session=mock_session)
        dossier = await service.get_client_dossier("client-123")

        # Assertions
        assert dossier is not None
        assert "ago" in dossier
        assert "Memory 0" in dossier
        assert len(dossier.split("\n")) == 3

    @pytest.mark.asyncio
    async def test_get_dossier_no_memories(self, mock_session):
        """Test dossier returns None when no memories exist."""
        from cognitive_orch.services.memory_service import MemoryService

        # Mock database query returning empty list
        result = AsyncMock()
        result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = result

        # Test
        service = MemoryService(session=mock_session)
        dossier = await service.get_client_dossier("client-123")

        # Assertions
        assert dossier is None

    @pytest.mark.asyncio
    async def test_store_memory(self, mock_session):
        """Test storing a new memory."""
        from cognitive_orch.services.memory_service import MemoryService

        # Test
        service = MemoryService(session=mock_session)
        memory = await service.store_memory(
            client_id="client-123",
            summary_text="Client called about divorce case.",
            embedding=[0.1, 0.2, 0.3],
        )

        # Assertions
        assert mock_session.add.called
        assert mock_session.commit.called

    def test_normalize_phone_number(self):
        """Test phone number normalization."""
        from cognitive_orch.services.memory_service import MemoryService

        # Test various formats
        assert MemoryService._normalize_phone_number("+1 555 123-4567") == "+15551234567"
        assert MemoryService._normalize_phone_number("(555) 123-4567") == "5551234567"
        assert MemoryService._normalize_phone_number("+1-555-123-4567") == "+15551234567"

    def test_format_time_ago(self):
        """Test relative time formatting."""
        from cognitive_orch.services.memory_service import MemoryService

        now = datetime.utcnow()

        # Test various time deltas
        assert MemoryService._format_time_ago(now, now - timedelta(minutes=30)) == "30 minutes ago"
        assert MemoryService._format_time_ago(now, now - timedelta(hours=2)) == "2 hours ago"
        assert MemoryService._format_time_ago(now, now - timedelta(days=1)) == "1 day ago"
        assert MemoryService._format_time_ago(now, now - timedelta(days=3)) == "3 days ago"
        assert MemoryService._format_time_ago(now, now - timedelta(days=14)) == "2 weeks ago"


class TestPostCallWorker:
    """Tests for PostCallWorker."""

    @pytest.mark.asyncio
    async def test_generate_memory(self):
        """Test memory generation from transcript."""
        from cognitive_orch.services.post_call_worker import PostCallWorker

        # Mock MemoryService
        mock_memory_service = AsyncMock()
        mock_memory_service.store_memory = AsyncMock()

        worker = PostCallWorker(memory_service=mock_memory_service)

        # Mock LLM responses
        with patch("cognitive_orch.services.post_call_worker.acompletion") as mock_completion, \
             patch("cognitive_orch.services.post_call_worker.aembedding") as mock_embedding:

            # Setup mocks
            mock_completion.return_value.choices = [
                MagicMock(message=MagicMock(content="Client called about divorce case."))
            ]
            mock_embedding.return_value.data = [{"embedding": [0.1] * 1536}]

            # Test
            transcript = "User: Hi, I need help with divorce.\nAI: I can help with that."
            summary = await worker.generate_memory(transcript, "client-123")

            # Assertions
            assert summary == "Client called about divorce case."
            assert mock_completion.called
            assert mock_embedding.called
            assert mock_memory_service.store_memory.called

    @pytest.mark.asyncio
    async def test_generate_memory_without_embedding(self):
        """Test memory generation without embeddings."""
        from cognitive_orch.services.post_call_worker import PostCallWorker

        mock_memory_service = AsyncMock()
        worker = PostCallWorker(memory_service=mock_memory_service)

        with patch("cognitive_orch.services.post_call_worker.acompletion") as mock_completion:
            mock_completion.return_value.choices = [
                MagicMock(message=MagicMock(content="Summary text"))
            ]

            # Test with include_embedding=False
            summary = await worker.generate_memory(
                "Transcript", "client-123", include_embedding=False
            )

            assert summary == "Summary text"
            # Embedding should not be generated
            assert mock_memory_service.store_memory.call_args[1]["embedding"] is None


class TestPromptBuilder:
    """Tests for PromptBuilder."""

    def test_build_system_prompt_basic(self):
        """Test building basic system prompt without dossier."""
        from cognitive_orch.services.prompt_builder import build_system_prompt

        firm_persona = "You are a receptionist for Smith & Associates."
        prompt = build_system_prompt(firm_persona)

        assert firm_persona in prompt
        assert "RECOGNIZED CALLER INFO" not in prompt

    def test_build_system_prompt_with_dossier(self):
        """Test building system prompt with client dossier."""
        from cognitive_orch.services.prompt_builder import build_system_prompt

        firm_persona = "You are a receptionist for Smith & Associates."
        dossier = "- [2 days ago]: Called about divorce case."

        prompt = build_system_prompt(firm_persona, client_dossier=dossier)

        assert firm_persona in prompt
        assert "RECOGNIZED CALLER INFO" in prompt
        assert dossier in prompt
        assert "known client" in prompt.lower()

    def test_build_system_prompt_with_tools(self):
        """Test building system prompt with tool instructions."""
        from cognitive_orch.services.prompt_builder import build_system_prompt

        firm_persona = "You are a receptionist."
        prompt = build_system_prompt(firm_persona, include_tool_instructions=True)

        assert firm_persona in prompt
        assert "TOOL USAGE INSTRUCTIONS" in prompt
        assert "Appointment Booking" in prompt

    def test_build_system_prompt_complete(self):
        """Test building complete system prompt with all options."""
        from cognitive_orch.services.prompt_builder import build_system_prompt

        firm_persona = "You are a receptionist."
        dossier = "- [1 day ago]: Previous call."

        prompt = build_system_prompt(
            firm_persona,
            client_dossier=dossier,
            include_tool_instructions=True,
        )

        assert firm_persona in prompt
        assert "RECOGNIZED CALLER INFO" in prompt
        assert dossier in prompt
        assert "TOOL USAGE INSTRUCTIONS" in prompt


@pytest.mark.integration
class TestMemoryIntegration:
    """Integration tests for memory flow."""

    @pytest.mark.asyncio
    async def test_full_memory_flow(self):
        """
        Test full flow: identify -> get dossier -> build prompt -> generate memory.

        This is a placeholder for integration testing.
        Requires actual database connection.
        """
        # TODO: Implement with test database
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

