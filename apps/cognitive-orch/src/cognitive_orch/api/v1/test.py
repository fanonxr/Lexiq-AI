"""Test endpoints for LLM service and other components."""

from typing import Optional

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from cognitive_orch.services.llm_service import get_llm_service
from cognitive_orch.services.tool_loop_service import get_tool_loop_service
from cognitive_orch.services.tool_service import get_tool_service
from cognitive_orch.utils.errors import LLMError
from cognitive_orch.utils.logging import get_logger

logger = get_logger("test_endpoints")
router = APIRouter(prefix="/test", tags=["test"])


class TestLLMRequest(BaseModel):
    """Request model for testing LLM service."""

    message: str = Field(..., description="Test message to send to LLM")
    model: Optional[str] = Field(
        None, description="Optional model override (e.g., 'azure/gpt-4o')"
    )
    stream: bool = Field(True, description="Whether to stream the response")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")


class TestLLMResponse(BaseModel):
    """Response model for non-streaming LLM test."""

    model_used: str
    response: str
    success: bool


class TestToolDefinitionsResponse(BaseModel):
    """Response model for tool definitions."""

    tools: list[dict]


class TestToolLoopRequest(BaseModel):
    """Request model for running the tool loop."""

    message: str = Field(..., description="User message")
    conversation_id: Optional[str] = Field(None, description="Optional conversation id (UUID)")
    model: Optional[str] = Field(None, description="Optional model override (LiteLLM format)")
    temperature: float = Field(0.2, ge=0.0, le=2.0, description="Sampling temperature")
    max_iterations: int = Field(5, ge=1, le=10, description="Max tool-loop iterations")


class TestToolLoopResponse(BaseModel):
    """Response model for tool-loop results."""

    conversation_id: str
    response: str
    iterations: int
    tool_results: list[dict]


@router.post("/llm", response_model=TestLLMResponse, status_code=status.HTTP_200_OK)
async def test_llm_sync(request: TestLLMRequest):
    """
    Test LLM service with a synchronous (non-streaming) request.
    
    This endpoint tests the LLM service without streaming, useful for
    quick verification that the service is configured correctly.
    """
    try:
        llm_service = get_llm_service()

        # Prepare messages
        messages = [
            {"role": "user", "content": request.message}
        ]

        # Prepare firm preferences if model override provided
        firm_preferences = None
        if request.model:
            firm_preferences = {"model_override": request.model}

        # Generate response (non-streaming)
        response = await llm_service.generate_response_sync(
            messages=messages,
            firm_preferences=firm_preferences,
            stream=False,
            temperature=request.temperature,
        )

        # Extract response text from LiteLLM response
        # LiteLLM response format: {"choices": [{"message": {"content": "..."}}]}
        response_text = ""
        if "choices" in response and len(response["choices"]) > 0:
            choice = response["choices"][0]
            if "message" in choice and "content" in choice["message"]:
                response_text = choice["message"]["content"]
            elif "delta" in choice and "content" in choice["delta"]:
                response_text = choice["delta"]["content"]

        # Get model used from response
        model_used = response.get("model", request.model or llm_service.default_model)

        logger.info(f"LLM test successful, model: {model_used}")

        return TestLLMResponse(
            model_used=model_used,
            response=response_text,
            success=True,
        )

    except LLMError as e:
        logger.error(f"LLM test failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "LLM service error",
                "message": e.message,
                "model": e.details.get("model", "unknown"),
            },
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error in LLM test: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "message": str(e)},
        ) from e


@router.post("/llm/stream", status_code=status.HTTP_200_OK)
async def test_llm_stream(request: TestLLMRequest):
    """
    Test LLM service with a streaming request.
    
    This endpoint tests the LLM service with streaming enabled, returning
    Server-Sent Events (SSE) format for real-time response streaming.
    """
    try:
        llm_service = get_llm_service()

        # Prepare messages
        messages = [
            {"role": "user", "content": request.message}
        ]

        # Prepare firm preferences if model override provided
        firm_preferences = None
        if request.model:
            firm_preferences = {"model_override": request.model}

        async def generate_stream():
            """Generator function for streaming responses."""
            try:
                async for chunk in llm_service.generate_response(
                    messages=messages,
                    firm_preferences=firm_preferences,
                    stream=True,
                    temperature=request.temperature,
                ):
                    # LiteLLM streaming chunks format:
                    # {"choices": [{"delta": {"content": "..."}}]}
                    content = ""
                    if "choices" in chunk and len(chunk["choices"]) > 0:
                        choice = chunk["choices"][0]
                        if "delta" in choice and "content" in choice["delta"]:
                            content = choice["delta"]["content"]
                        elif "message" in choice and "content" in choice["message"]:
                            content = choice["message"]["content"]

                    if content:
                        # Format as Server-Sent Events
                        yield f"data: {content}\n\n"

                # Send completion marker
                yield "data: [DONE]\n\n"

            except Exception as e:
                logger.error(f"Error in streaming: {e}", exc_info=True)
                yield f"data: [ERROR] {str(e)}\n\n"

        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    except Exception as e:
        logger.error(f"Unexpected error in LLM stream test: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "message": str(e)},
        ) from e


@router.get("/tools/definitions", response_model=TestToolDefinitionsResponse, status_code=status.HTTP_200_OK)
async def get_tool_definitions():
    """Return the tool definitions (JSON schema) exposed to the LLM."""
    tool_service = get_tool_service()
    return TestToolDefinitionsResponse(tools=tool_service.get_tool_definitions())


@router.post("/llm/tools", response_model=TestToolLoopResponse, status_code=status.HTTP_200_OK)
async def test_llm_tool_loop(request: TestToolLoopRequest):
    """Run the non-streaming LLM tool-calling loop (MVP)."""
    try:
        tool_loop = get_tool_loop_service()

        firm_preferences = None
        if request.model:
            firm_preferences = {"model_override": request.model}

        result = await tool_loop.run(
            user_message=request.message,
            conversation_id=request.conversation_id,
            firm_preferences=firm_preferences,
            temperature=request.temperature,
            max_iterations=request.max_iterations,
        )

        return TestToolLoopResponse(
            conversation_id=result.conversation_id,
            response=result.final_text,
            iterations=result.iterations,
            tool_results=[r.model_dump(exclude_none=True) for r in result.tool_results],
        )
    except LLMError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "LLM service error", "message": e.message},
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error in tool loop test: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "message": str(e)},
        ) from e
