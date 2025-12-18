"""Unit tests for LLM Service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from cognitive_orch.services.llm_service import LLMService, get_llm_service
from cognitive_orch.utils.errors import LLMError


@pytest.fixture
def llm_service():
    """Create LLM service instance for testing."""
    return LLMService()


@pytest.fixture
def mock_messages():
    """Sample messages for testing."""
    return [
        {"role": "user", "content": "Hello, how are you?"}
    ]


class TestModelSelection:
    """Test model selection logic."""

    def test_select_default_model(self, llm_service):
        """Test that default model is selected when no firm preferences."""
        model = llm_service._select_model()
        assert model == llm_service.default_model

    def test_select_firm_override_model(self, llm_service):
        """Test that firm override model is selected when provided."""
        firm_prefs = {"model_override": "anthropic/claude-3-5-sonnet"}
        model = llm_service._select_model(firm_preferences=firm_prefs)
        assert model == "anthropic/claude-3-5-sonnet"

    def test_select_model_with_none_firm_prefs(self, llm_service):
        """Test that default model is used when firm_preferences is None."""
        model = llm_service._select_model(firm_preferences=None)
        assert model == llm_service.default_model


class TestModelValidation:
    """Test model configuration validation."""

    def test_validate_azure_model_with_config(self, llm_service):
        """Test validation passes when Azure OpenAI is configured."""
        # Mock settings to have Azure OpenAI configured
        with patch.object(llm_service.settings.llm, "has_azure_openai", True):
            # Should not raise
            llm_service._validate_model_configuration("azure/gpt-4o")

    def test_validate_azure_model_without_config(self, llm_service):
        """Test validation fails when Azure OpenAI is not configured."""
        # Mock settings to not have Azure OpenAI configured
        with patch.object(llm_service.settings.llm, "has_azure_openai", False):
            with pytest.raises(LLMError) as exc_info:
                llm_service._validate_model_configuration("azure/gpt-4o")
            assert "Azure OpenAI" in exc_info.value.message

    def test_validate_anthropic_model_without_config(self, llm_service):
        """Test validation fails when Anthropic is not configured."""
        with patch.object(llm_service.settings.llm, "has_anthropic", False):
            with pytest.raises(LLMError) as exc_info:
                llm_service._validate_model_configuration("anthropic/claude-3-haiku")
            assert "Anthropic" in exc_info.value.message


class TestLLMCalls:
    """Test LLM API calls."""

    @pytest.mark.asyncio
    async def test_call_llm_success(self, llm_service, mock_messages):
        """Test successful LLM call."""
        mock_response = {
            "choices": [{"message": {"content": "Hello! I'm doing well, thank you."}}],
            "model": "azure/gpt-4o",
        }

        with patch("cognitive_orch.services.llm_service.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_response

            with patch.object(llm_service, "_validate_model_configuration"):
                response = await llm_service._call_llm(
                    model="azure/gpt-4o",
                    messages=mock_messages,
                    stream=False,
                )

                assert response == mock_response
                mock_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_llm_failure(self, llm_service, mock_messages):
        """Test LLM call failure raises LLMError."""
        with patch("cognitive_orch.services.llm_service.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.side_effect = Exception("API Error")

            with patch.object(llm_service, "_validate_model_configuration"):
                with pytest.raises(LLMError) as exc_info:
                    await llm_service._call_llm(
                        model="azure/gpt-4o",
                        messages=mock_messages,
                        stream=False,
                    )

                assert "LLM call failed" in exc_info.value.message


class TestFallbackLogic:
    """Test fallback logic."""

    @pytest.mark.asyncio
    async def test_fallback_on_primary_failure(self, llm_service, mock_messages):
        """Test that fallback model is used when primary fails."""
        # Mock primary model to fail
        primary_error = LLMError(
            message="Primary model failed",
            model="azure/gpt-4o",
        )

        # Mock fallback model to succeed
        fallback_response = {
            "choices": [{"message": {"content": "Fallback response"}}],
            "model": "anthropic/claude-3-haiku",
        }

        with patch.object(llm_service, "_call_llm") as mock_call:
            # First call (primary) fails, second call (fallback) succeeds
            mock_call.side_effect = [
                primary_error,  # Primary fails
                fallback_response,  # Fallback succeeds
            ]

            # Enable fallbacks
            llm_service.enable_fallbacks = True

            # Collect response chunks
            responses = []
            async for chunk in llm_service.generate_response(
                messages=mock_messages,
                stream=False,
            ):
                responses.append(chunk)

            # Should have tried primary, then fallback
            assert mock_call.call_count == 2
            assert responses[0] == fallback_response

    @pytest.mark.asyncio
    async def test_no_fallback_when_disabled(self, llm_service, mock_messages):
        """Test that fallback is not used when disabled."""
        primary_error = LLMError(
            message="Primary model failed",
            model="azure/gpt-4o",
        )

        with patch.object(llm_service, "_call_llm") as mock_call:
            mock_call.side_effect = primary_error

            # Disable fallbacks
            llm_service.enable_fallbacks = False

            # Should raise error without trying fallback
            with pytest.raises(LLMError):
                async for _ in llm_service.generate_response(
                    messages=mock_messages,
                    stream=False,
                ):
                    pass

            # Should only try primary model
            assert mock_call.call_count == 1


class TestServiceSingleton:
    """Test service singleton pattern."""

    def test_get_llm_service_returns_singleton(self):
        """Test that get_llm_service returns the same instance."""
        service1 = get_llm_service()
        service2 = get_llm_service()
        assert service1 is service2

