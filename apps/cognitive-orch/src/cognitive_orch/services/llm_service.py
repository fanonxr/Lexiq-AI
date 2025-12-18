"""LLM Service for model-agnostic LLM routing using LiteLLM.

This service provides a unified interface for interacting with multiple LLM providers
(Azure OpenAI, Anthropic, AWS Bedrock, Groq) through LiteLLM.
"""

import os
from typing import AsyncIterator, Dict, List, Optional, Union

from litellm import acompletion
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from cognitive_orch.config import get_settings
from cognitive_orch.utils.errors import LLMError
from cognitive_orch.utils.logging import get_logger

logger = get_logger("llm_service")
settings = get_settings()


class LLMService:
    """Service for LLM model routing and response generation.

    This service uses LiteLLM to provide a model-agnostic interface for
    interacting with various LLM providers. It handles:
    - Model selection (default or firm-specific override)
    - Automatic fallback on failure
    - Streaming responses
    - Tool/function calling
    - Retry logic with exponential backoff
    """

    def __init__(self):
        """Initialize LLM service with configuration."""
        self.settings = get_settings()
        self.default_model = self.settings.llm.default_model_name
        self.fallback_model = self.settings.llm.fallback_model_name
        self.enable_fallbacks = self.settings.llm.enable_fallbacks

        # Set up LiteLLM environment variables from config
        self._configure_litellm_environment()

    def _configure_litellm_environment(self) -> None:
        """Configure LiteLLM environment variables from settings.

        LiteLLM reads API keys and configuration from environment variables.
        This method sets them up based on our configuration.
        """
        # Azure OpenAI
        if self.settings.llm.azure_api_key:
            os.environ["AZURE_API_KEY"] = self.settings.llm.azure_api_key
        if self.settings.llm.azure_api_base:
            os.environ["AZURE_API_BASE"] = self.settings.llm.azure_api_base
        if self.settings.llm.azure_api_version:
            os.environ["AZURE_API_VERSION"] = self.settings.llm.azure_api_version

        # Anthropic
        if self.settings.llm.anthropic_api_key:
            os.environ["ANTHROPIC_API_KEY"] = self.settings.llm.anthropic_api_key

        # AWS Bedrock
        if self.settings.llm.aws_access_key_id:
            os.environ["AWS_ACCESS_KEY_ID"] = self.settings.llm.aws_access_key_id
        if self.settings.llm.aws_secret_access_key:
            os.environ["AWS_SECRET_ACCESS_KEY"] = self.settings.llm.aws_secret_access_key
        if self.settings.llm.aws_region:
            os.environ["AWS_REGION"] = self.settings.llm.aws_region

        # Groq
        if self.settings.llm.groq_api_key:
            os.environ["GROQ_API_KEY"] = self.settings.llm.groq_api_key

        logger.debug("LiteLLM environment variables configured")

    def _select_model(
        self, firm_preferences: Optional[Dict] = None
    ) -> str:
        """Select the appropriate model for the request.

        Args:
            firm_preferences: Optional firm-specific preferences containing model override.

        Returns:
            Model name in LiteLLM format (e.g., "azure/gpt-4o").
        """
        # Check for firm-specific model override
        if firm_preferences and firm_preferences.get("model_override"):
            model = firm_preferences["model_override"]
            logger.debug(f"Using firm-specific model override: {model}")
            return model

        # Use default model
        logger.debug(f"Using default model: {self.default_model}")
        return self.default_model

    def _validate_model_configuration(self, model: str) -> None:
        """Validate that the required API keys are configured for the model.

        Args:
            model: Model name in LiteLLM format.

        Raises:
            LLMError: If required API keys are not configured.
        """
        if model.startswith("azure/"):
            if not self.settings.llm.has_azure_openai:
                raise LLMError(
                    message=f"Azure OpenAI API key or base URL not configured for model {model}",
                    model=model,
                    details={"required": ["AZURE_API_KEY", "AZURE_API_BASE"]},
                )
        elif model.startswith("anthropic/"):
            if not self.settings.llm.has_anthropic:
                raise LLMError(
                    message=f"Anthropic API key not configured for model {model}",
                    model=model,
                    details={"required": ["ANTHROPIC_API_KEY"]},
                )
        elif model.startswith("bedrock/"):
            if not self.settings.llm.has_aws_bedrock:
                raise LLMError(
                    message=f"AWS Bedrock credentials not configured for model {model}",
                    model=model,
                    details={"required": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION"]},
                )
        elif model.startswith("groq/"):
            if not self.settings.llm.has_groq:
                raise LLMError(
                    message=f"Groq API key not configured for model {model}",
                    model=model,
                    details={"required": ["GROQ_API_KEY"]},
                )

    @retry(
        retry=retry_if_exception_type((LLMError, Exception)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _call_llm(
        self,
        model: str,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        stream: bool = True,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> Union[AsyncIterator, Dict]:
        """Call LLM via LiteLLM with retry logic.

        Args:
            model: Model name in LiteLLM format.
            messages: List of message dictionaries with 'role' and 'content'.
            tools: Optional list of tool definitions in JSON Schema format.
            stream: Whether to stream the response.
            temperature: Sampling temperature (0.0 to 2.0).
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional parameters to pass to LiteLLM.

        Returns:
            AsyncIterator for streaming responses or Dict for non-streaming.

        Raises:
            LLMError: If the LLM call fails after retries.
        """
        # Validate model configuration
        self._validate_model_configuration(model)

        # Prepare LiteLLM parameters
        litellm_params = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "temperature": temperature,
        }

        if max_tokens:
            litellm_params["max_tokens"] = max_tokens

        if tools:
            litellm_params["tools"] = tools

        # Add any additional kwargs
        litellm_params.update(kwargs)

        try:
            logger.debug(f"Calling LLM model: {model}, stream={stream}, tools={bool(tools)}")
            
            # LiteLLM's acompletion returns an async iterator when stream=True
            # or a single response dict when stream=False
            response = await acompletion(**litellm_params)
            return response

        except Exception as e:
            logger.error(
                f"LLM call failed for model {model}: {e}",
                extra={
                    "model": model,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            raise LLMError(
                message=f"LLM call failed: {str(e)}",
                model=model,
                details={"error_type": type(e).__name__, "error_message": str(e)},
            ) from e

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        firm_preferences: Optional[Dict] = None,
        tools: Optional[List[Dict]] = None,
        stream: bool = True,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncIterator[Dict]:
        """Generate LLM response with automatic fallback.

        This method handles:
        - Model selection (firm override or default)
        - Automatic fallback to secondary model on failure
        - Streaming responses
        - Tool/function calling

        Args:
            messages: List of message dictionaries with 'role' and 'content'.
            firm_preferences: Optional firm-specific preferences (e.g., model override).
            tools: Optional list of tool definitions in JSON Schema format.
            stream: Whether to stream the response (default: True).
            temperature: Sampling temperature (default: 0.7).
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional parameters to pass to LiteLLM.

        Yields:
            Dictionary chunks from the LLM response stream.

        Raises:
            LLMError: If all models fail (primary and fallback).
        """
        # Select primary model
        primary_model = self._select_model(firm_preferences)

        try:
            # Try primary model
            logger.info(f"Attempting LLM call with primary model: {primary_model}")
            response = await self._call_llm(
                model=primary_model,
                messages=messages,
                tools=tools,
                stream=stream,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

            # Handle streaming vs non-streaming responses
            if stream:
                # response is an async iterator when stream=True
                async for chunk in response:
                    yield chunk
            else:
                # response is a single dict when stream=False
                yield response

            logger.info(f"Successfully generated response using model: {primary_model}")

        except LLMError as e:
            # If fallbacks are enabled and we haven't already tried the fallback
            if (
                self.enable_fallbacks
                and primary_model != self.fallback_model
                and self.fallback_model
            ):
                logger.warning(
                    f"Primary model {primary_model} failed, attempting fallback: {self.fallback_model}",
                    extra={
                        "primary_model": primary_model,
                        "fallback_model": self.fallback_model,
                        "error": str(e),
                    },
                )

                try:
                    # Try fallback model
                    response = await self._call_llm(
                        model=self.fallback_model,
                        messages=messages,
                        tools=tools,
                        stream=stream,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        **kwargs,
                    )

                    # Handle streaming vs non-streaming responses
                    if stream:
                        # response is an async iterator when stream=True
                        async for chunk in response:
                            yield chunk
                    else:
                        # response is a single dict when stream=False
                        yield response

                    logger.info(
                        f"Successfully generated response using fallback model: {self.fallback_model}"
                    )

                except LLMError as fallback_error:
                    logger.error(
                        f"Both primary ({primary_model}) and fallback ({self.fallback_model}) models failed",
                        extra={
                            "primary_error": str(e),
                            "fallback_error": str(fallback_error),
                        },
                    )
                    raise LLMError(
                        message=f"All models failed. Primary: {str(e)}, Fallback: {str(fallback_error)}",
                        model=primary_model,
                        details={
                            "primary_model": primary_model,
                            "fallback_model": self.fallback_model,
                            "primary_error": str(e),
                            "fallback_error": str(fallback_error),
                        },
                    ) from fallback_error
            else:
                # No fallback or already using fallback - re-raise the error
                logger.error(f"LLM call failed and no fallback available: {e}")
                raise

    async def generate_response_sync(
        self,
        messages: List[Dict[str, str]],
        firm_preferences: Optional[Dict] = None,
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> Dict:
        """Generate LLM response synchronously (non-streaming).

        Convenience method for non-streaming responses. Returns the complete
        response dictionary.

        Args:
            messages: List of message dictionaries with 'role' and 'content'.
            firm_preferences: Optional firm-specific preferences.
            tools: Optional list of tool definitions.
            temperature: Sampling temperature (default: 0.7).
            max_tokens: Maximum tokens to generate.
            **kwargs: Additional parameters to pass to LiteLLM.

        Returns:
            Complete response dictionary from LiteLLM.
        """
        # Collect the single response from non-streaming call
        response_dict = None
        async for chunk in self.generate_response(
            messages=messages,
            firm_preferences=firm_preferences,
            tools=tools,
            stream=False,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        ):
            # For non-streaming, there should be only one chunk
            response_dict = chunk
            break

        if response_dict is None:
            raise LLMError(
                message="No response received from LLM",
                model=self._select_model(firm_preferences),
            )

        return response_dict


# Global service instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get the global LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service

