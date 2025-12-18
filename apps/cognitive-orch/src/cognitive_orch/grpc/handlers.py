"""gRPC request handlers for Cognitive Orchestrator service.

This module contains the gRPC servicer implementation that handles incoming
requests from the Voice Gateway. Handlers reuse the same core chat logic
used by the HTTP REST API endpoints.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional

import grpc
from grpc import aio
from redis.asyncio import ConnectionPool

from cognitive_orch.grpc.proto import cognitive_orch_pb2, cognitive_orch_pb2_grpc
from cognitive_orch.models.conversation import ConversationState
from cognitive_orch.services.prompt_service import get_prompt_service
from cognitive_orch.services.state_service import get_state_service
from cognitive_orch.services.tool_loop_service import get_tool_loop_service
from cognitive_orch.utils.errors import (
    ExternalServiceError,
    LLMError,
    NotFoundError,
    OrchestratorException,
    RAGError,
    StateError,
    ToolExecutionError,
    ValidationError,
)
from cognitive_orch.utils.logging import get_logger

logger = get_logger("grpc.handlers")


def _check_cancellation(context: aio.ServicerContext, correlation_id: str) -> None:
    """Check if the request has been cancelled and raise if so.
    
    Args:
        context: gRPC servicer context
        correlation_id: Correlation ID for logging
        
    Raises:
        asyncio.CancelledError: If the request has been cancelled
    """
    if not context.is_active():
        logger.info(f"Request cancelled: {correlation_id}")
        raise asyncio.CancelledError(f"Request cancelled: {correlation_id}")


def _state_to_llm_messages(state: ConversationState) -> List[Dict[str, Any]]:
    """Convert stored conversation messages into LLM-compatible message dicts.

    We preserve tool metadata when present (tool_calls, tool_call_id) so multi-turn tool flows
    remain consistent.
    """
    llm_msgs: List[Dict[str, Any]] = []
    for m in state.messages:
        msg: Dict[str, Any] = {"role": m.role, "content": m.content}
        if m.role == "assistant" and m.tool_calls:
            msg["tool_calls"] = m.tool_calls
        if m.role == "tool" and m.tool_call_id:
            msg["tool_call_id"] = m.tool_call_id
        llm_msgs.append(msg)
    return llm_msgs


def _map_exception_to_grpc_status(exception: Exception) -> tuple[grpc.StatusCode, str, str]:
    """Map Python exceptions to gRPC status codes.
    
    Args:
        exception: The exception to map
        
    Returns:
        Tuple of (StatusCode, error_message, error_code)
    """
    # Handle custom Orchestrator exceptions
    if isinstance(exception, ValidationError):
        return grpc.StatusCode.INVALID_ARGUMENT, exception.message, exception.code
    elif isinstance(exception, NotFoundError):
        return grpc.StatusCode.NOT_FOUND, exception.message, exception.code
    elif isinstance(exception, StateError):
        # Check if it's a "not found" type error
        if "not found" in str(exception).lower() or "not found" in exception.message.lower():
            return grpc.StatusCode.NOT_FOUND, exception.message, exception.code
        return grpc.StatusCode.INVALID_ARGUMENT, exception.message, exception.code
    elif isinstance(exception, ToolExecutionError):
        # Tool execution errors are internal errors (tool failed, not user error)
        return grpc.StatusCode.INTERNAL, exception.message, exception.code
    elif isinstance(exception, LLMError):
        # LLM errors are typically service unavailable or bad gateway
        return grpc.StatusCode.UNAVAILABLE, exception.message, exception.code
    elif isinstance(exception, RAGError):
        # RAG errors are typically service unavailable
        return grpc.StatusCode.UNAVAILABLE, exception.message, exception.code
    elif isinstance(exception, ExternalServiceError):
        # External service errors are typically unavailable or bad gateway
        if exception.status_code == 503:
            return grpc.StatusCode.UNAVAILABLE, exception.message, exception.code
        elif exception.status_code == 502:
            return grpc.StatusCode.UNAVAILABLE, exception.message, exception.code
        else:
            return grpc.StatusCode.INTERNAL, exception.message, exception.code
    elif isinstance(exception, OrchestratorException):
        # Generic orchestrator exception - use status code to determine gRPC code
        if exception.status_code == 404:
            return grpc.StatusCode.NOT_FOUND, exception.message, exception.code
        elif exception.status_code == 422:
            return grpc.StatusCode.INVALID_ARGUMENT, exception.message, exception.code
        elif exception.status_code == 503:
            return grpc.StatusCode.UNAVAILABLE, exception.message, exception.code
        else:
            return grpc.StatusCode.INTERNAL, exception.message, exception.code
    # Handle standard Python exceptions
    elif isinstance(exception, ValueError):
        return grpc.StatusCode.INVALID_ARGUMENT, str(exception), "VALUE_ERROR"
    elif isinstance(exception, TimeoutError):
        return grpc.StatusCode.DEADLINE_EXCEEDED, str(exception), "TIMEOUT_ERROR"
    elif isinstance(exception, KeyError):
        return grpc.StatusCode.NOT_FOUND, f"Resource not found: {str(exception)}", "KEY_ERROR"
    else:
        # Unknown exception - log and return internal error
        logger.error(f"Unhandled exception in gRPC handler: {type(exception).__name__}: {exception}", exc_info=True)
        return grpc.StatusCode.INTERNAL, "Internal server error", "INTERNAL_ERROR"


class CognitiveOrchestratorServicer(cognitive_orch_pb2_grpc.CognitiveOrchestratorServicer):
    """gRPC servicer for Cognitive Orchestrator service.
    
    Handles all RPC methods defined in the proto service definition.
    """

    def __init__(self, redis_pool: Optional[ConnectionPool] = None):
        """Initialize the servicer.
        
        Args:
            redis_pool: Optional Redis connection pool for state management.
        """
        self.redis_pool = redis_pool

    async def ProcessText(
        self,
        request: cognitive_orch_pb2.TextRequest,
        context: aio.ServicerContext,
    ) -> AsyncIterator[cognitive_orch_pb2.TextResponse]:
        """Process text input and stream response.
        
        This is the primary method for voice conversations. It:
        1. Loads or creates conversation state
        2. Builds system prompt with firm persona
        3. Runs tool loop service (if tools_enabled)
        4. Streams responses back to the client
        
        Args:
            request: TextRequest containing user input and metadata
            context: gRPC servicer context for request metadata and cancellation
            
        Yields:
            TextResponse chunks containing text, tool calls, or errors
        """
        conversation_id = request.conversation_id or str(uuid.uuid4())
        correlation_id = f"{conversation_id}-{uuid.uuid4().hex[:8]}"
        
        try:
            # Check if context is already cancelled
            if context.is_active() is False:
                logger.warning(f"Request cancelled before processing: {correlation_id}")
                return
            # Get services with Redis pool
            state_service = get_state_service(redis_pool=self.redis_pool)
            
            # Load or create conversation state
            state = await state_service.get_conversation_state(conversation_id)
            if state is None:
                if not request.user_id:
                    context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                    context.set_details("user_id is required for new conversations")
                    yield cognitive_orch_pb2.TextResponse(
                        conversation_id=conversation_id,
                        is_done=True,
                        error=cognitive_orch_pb2.Error(
                            code="INVALID_ARGUMENT",
                            message="user_id is required for new conversations",
                        ),
                    )
                    return
                
                state = await state_service.create_conversation(
                    conversation_id=conversation_id,
                    user_id=request.user_id,
                    firm_id=request.firm_id if request.firm_id else None,
                )
            else:
                # Ensure firm_id is captured if first message did not include it
                if request.firm_id and not state.metadata.firm_id:
                    state.metadata.firm_id = request.firm_id

            # Append user message to in-memory state (we persist at end)
            state.add_message(role="user", content=request.text)

            # Build firm preferences
            firm_preferences = None
            if request.model:
                firm_preferences = {"model_override": request.model}

            # Build messages for LLM (system prompt + persisted history)
            prompt_service = get_prompt_service(redis_pool=self.redis_pool)
            system_prompt = await prompt_service.build_system_prompt(
                firm_id=request.firm_id or state.metadata.firm_id,
                tools_enabled=request.tools_enabled,
            )
            messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
            messages.extend(_state_to_llm_messages(state))

            tool_loop = get_tool_loop_service()

            # Check for cancellation before long-running operations
            _check_cancellation(context, correlation_id)
            
            # Run tool loop or simple LLM call
            if request.tools_enabled:
                result = await tool_loop.run_with_messages(
                    messages=messages,
                    conversation_id=conversation_id,
                    firm_preferences=firm_preferences,
                    temperature=0.2,  # Default temperature
                )
            else:
                # No tools: single non-streaming LLM call using history
                llm = tool_loop._llm
                resp = await llm.generate_response_sync(
                    messages=messages,
                    firm_preferences=firm_preferences,
                    tools=None,
                    stream=False,
                    temperature=0.2,
                )
                assistant_msg = tool_loop._extract_assistant_message(resp)
                content, _tool_calls = tool_loop._extract_content_and_tool_calls(assistant_msg)
                
                # Create a result object similar to ToolLoopRunResult
                class SimpleResult:
                    def __init__(self):
                        self.conversation_id = conversation_id
                        self.final_text = content
                        self.tool_results = []
                        self.iterations = 1
                        self.messages = messages + [{"role": "assistant", "content": content}]
                
                result = SimpleResult()
            
            # Check for cancellation after processing
            _check_cancellation(context, correlation_id)

            # Stream tool calls and results for observability (optional)
            for tool_result in result.tool_results:
                # Check for cancellation before each yield
                if not context.is_active():
                    logger.info(f"Request cancelled during tool result streaming: {correlation_id}")
                    return
                
                # Send tool result in stream
                yield cognitive_orch_pb2.TextResponse(
                    conversation_id=conversation_id,
                    tool_result=cognitive_orch_pb2.ToolResult(
                        call_id=tool_result.tool_call_id or "",
                        result_json=json.dumps(tool_result.data),
                        success=tool_result.success,
                        error_message=tool_result.error.message if tool_result.error else "",
                    ),
                    is_done=False,
                )

            # Stream final text in chunks (simulate streaming by chunking)
            # In a future enhancement, we could stream during tool execution
            final_text = result.final_text
            chunk_size = 50  # Characters per chunk
            for i in range(0, len(final_text), chunk_size):
                # Check for cancellation before each yield
                if not context.is_active():
                    logger.info(f"Request cancelled during text streaming: {correlation_id}")
                    return
                
                chunk = final_text[i : i + chunk_size]
                yield cognitive_orch_pb2.TextResponse(
                    conversation_id=conversation_id,
                    text_chunk=chunk,
                    is_done=False,
                )

            # Persist new messages produced during this run
            llm_messages_no_system = [m for m in result.messages if m.get("role") != "system"]

            # Find the last user message index we just added, then persist subsequent messages
            last_user_idx = -1
            for idx in range(len(llm_messages_no_system) - 1, -1, -1):
                if llm_messages_no_system[idx].get("role") == "user":
                    last_user_idx = idx
                    break

            for m in llm_messages_no_system[last_user_idx + 1 :]:
                role = m.get("role", "assistant")
                content = m.get("content", "") or ""
                tool_calls = m.get("tool_calls")
                tool_call_id = m.get("tool_call_id")
                state.add_message(
                    role=role,
                    content=content,
                    tool_calls=tool_calls if isinstance(tool_calls, list) else None,
                    tool_call_id=tool_call_id if isinstance(tool_call_id, str) else None,
                )

            # Check for cancellation before persisting state
            _check_cancellation(context, correlation_id)
            
            # Persist updated state to Redis
            await state_service.save_conversation_state(state)

            # Check for cancellation one more time before final message
            if context.is_active():
                # Send final done message
                yield cognitive_orch_pb2.TextResponse(
                    conversation_id=conversation_id,
                    is_done=True,
                    total_tokens=state.metadata.total_tokens,
                )
            else:
                logger.info(f"Request cancelled before sending final message: {correlation_id}")

        except asyncio.CancelledError:
            # Handle cancellation gracefully
            logger.info(f"Request cancelled: {correlation_id}")
            context.set_code(grpc.StatusCode.CANCELLED)
            context.set_details("Request was cancelled by client")
            # Don't yield - stream is already cancelled
            return
        except Exception as e:
            # Map exception to gRPC status
            status_code, error_message, error_code = _map_exception_to_grpc_status(e)
            
            # Log error with correlation ID
            logger.error(
                f"ProcessText failed: {correlation_id}",
                extra={
                    "correlation_id": correlation_id,
                    "conversation_id": conversation_id,
                    "error_type": type(e).__name__,
                    "error_code": error_code,
                    "grpc_status": status_code.name,
                },
                exc_info=True,
            )
            
            # Set gRPC context status
            context.set_code(status_code)
            context.set_details(error_message)
            
            # Build error details
            error_details = {
                "correlation_id": correlation_id,
                "conversation_id": conversation_id,
                "exception_type": type(e).__name__,
            }
            
            # Add exception details if available
            if isinstance(e, OrchestratorException):
                error_details.update(e.details)
            
            # Yield error response in stream
            yield cognitive_orch_pb2.TextResponse(
                conversation_id=conversation_id,
                is_done=True,
                error=cognitive_orch_pb2.Error(
                    code=error_code,
                    message=error_message,
                    details_json=json.dumps(error_details),
                ),
            )

    async def GetConversationState(
        self,
        request: cognitive_orch_pb2.StateRequest,
        context: aio.ServicerContext,
    ) -> cognitive_orch_pb2.StateResponse:
        """Get current conversation state.
        
        Args:
            request: StateRequest containing conversation_id
            context: gRPC servicer context
            
        Returns:
            StateResponse with conversation history and metadata
        """
        try:
            state_service = get_state_service(redis_pool=self.redis_pool)
            
            state = await state_service.get_conversation_state(request.conversation_id)
            if state is None:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Conversation {request.conversation_id} not found")
                return cognitive_orch_pb2.StateResponse(
                    conversation_id=request.conversation_id,
                    messages=[],
                    total_tokens=0,
                )

            # Convert messages to proto format
            proto_messages = []
            for msg in state.messages:
                proto_msg = cognitive_orch_pb2.Message(
                    role=msg.role,
                    content=msg.content,
                    timestamp=int(msg.timestamp.timestamp()),
                )
                if msg.tool_call_id:
                    proto_msg.tool_call_id = msg.tool_call_id
                if msg.role == "tool" and hasattr(msg, "tool_name"):
                    # Extract tool name from tool_calls if available
                    proto_msg.tool_name = ""  # Could be enhanced to extract from tool_calls
                proto_messages.append(proto_msg)

            return cognitive_orch_pb2.StateResponse(
                conversation_id=state.conversation_id,
                messages=proto_messages,
                total_tokens=state.metadata.total_tokens,
                user_id=state.metadata.user_id,
                firm_id=state.metadata.firm_id or "",
                created_at=int(state.metadata.started_at.timestamp()),
                updated_at=int(state.metadata.updated_at.timestamp()),
            )

        except Exception as e:
            # Map exception to gRPC status
            status_code, error_message, error_code = _map_exception_to_grpc_status(e)
            
            # Log error with correlation ID
            correlation_id = f"{request.conversation_id}-{uuid.uuid4().hex[:8]}"
            logger.error(
                f"GetConversationState failed: {correlation_id}",
                extra={
                    "correlation_id": correlation_id,
                    "conversation_id": request.conversation_id,
                    "error_type": type(e).__name__,
                    "error_code": error_code,
                    "grpc_status": status_code.name,
                },
                exc_info=True,
            )
            
            context.set_code(status_code)
            context.set_details(error_message)
            raise

    async def ClearConversation(
        self,
        request: cognitive_orch_pb2.ClearRequest,
        context: aio.ServicerContext,
    ) -> cognitive_orch_pb2.ClearResponse:
        """Clear conversation state.
        
        Args:
            request: ClearRequest containing conversation_id
            context: gRPC servicer context
            
        Returns:
            ClearResponse indicating success or failure
        """
        try:
            state_service = get_state_service(redis_pool=self.redis_pool)
            
            # Check if conversation exists before clearing
            state = await state_service.get_conversation_state(request.conversation_id)
            if state is None:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Conversation {request.conversation_id} not found")
                return cognitive_orch_pb2.ClearResponse(
                    success=False,
                    message=f"Conversation {request.conversation_id} not found",
                )
            
            # Clear conversation state
            await state_service.clear_conversation(request.conversation_id)
            
            return cognitive_orch_pb2.ClearResponse(
                success=True,
                message=f"Conversation {request.conversation_id} cleared successfully",
            )

        except Exception as e:
            # Map exception to gRPC status
            status_code, error_message, error_code = _map_exception_to_grpc_status(e)
            
            # Log error with correlation ID
            correlation_id = f"{request.conversation_id}-{uuid.uuid4().hex[:8]}"
            logger.error(
                f"ClearConversation failed: {correlation_id}",
                extra={
                    "correlation_id": correlation_id,
                    "conversation_id": request.conversation_id,
                    "error_type": type(e).__name__,
                    "error_code": error_code,
                    "grpc_status": status_code.name,
                },
                exc_info=True,
            )
            
            context.set_code(status_code)
            context.set_details(error_message)
            raise

    async def HealthCheck(
        self,
        request: cognitive_orch_pb2.HealthRequest,
        context: aio.ServicerContext,
    ) -> cognitive_orch_pb2.HealthResponse:
        """Health check endpoint for gRPC service.
        
        Args:
            request: HealthRequest (empty)
            context: gRPC servicer context
            
        Returns:
            HealthResponse with service health status
        """
        # Simple health check - can be enhanced later to check Redis/Qdrant
        return cognitive_orch_pb2.HealthResponse(
            healthy=True,
            status="healthy",
            version="0.1.0",
        )
