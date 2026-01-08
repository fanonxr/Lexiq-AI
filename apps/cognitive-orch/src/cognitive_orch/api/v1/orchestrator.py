"""Orchestrator chat endpoints (real entrypoint for tool loop + state)."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request, status

from cognitive_orch.auth.internal_service import InternalAuthDep
from cognitive_orch.models.chat import ChatRequest, ChatResponse
from cognitive_orch.models.conversation import ConversationState
from cognitive_orch.models.conversation_api import (
    ClearConversationResponse,
    ConversationStateResponse,
)
from cognitive_orch.services.state_service import get_state_service
from cognitive_orch.services.prompt_service import get_prompt_service
from cognitive_orch.services.tool_loop_service import get_tool_loop_service
from cognitive_orch.utils.errors import NotFoundError, StateError
from cognitive_orch.utils.logging import get_logger

logger = get_logger("orchestrator_api")

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])


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


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Chat with the Cognitive Orchestrator (Internal)",
    description=(
        "Primary chat entrypoint for orchestrator tool execution + state. "
        "Intended for internal service calls (e.g., API Core)."
    ),
    dependencies=[InternalAuthDep],
    include_in_schema=False,
)
async def chat(request: Request, payload: ChatRequest) -> ChatResponse:
    """
    Primary chat entrypoint (HTTP) for orchestrator tool execution + state.

    - Loads/creates conversation state in Redis
    - Runs LLM tool-calling loop (optional)
    - Persists new assistant/tool messages to Redis

    **Authentication**: Internal API key only (via InternalAuthDep)
    **Used by**: API Core service
    **Note**: This endpoint is not accessible to users. It requires the X-Internal-API-Key header.
    """
    try:
        # Use app-initialized redis pool if present (created at startup)
        redis_pool = getattr(request.app.state, "redis_pool", None)
        state_service = get_state_service(redis_pool=redis_pool)

        conversation_id = payload.conversation_id or str(uuid.uuid4())

        state = await state_service.get_conversation_state(conversation_id)
        if state is None:
            state = await state_service.create_conversation(
                conversation_id=conversation_id,
                user_id=payload.user_id,
                firm_id=payload.firm_id,
            )
        else:
            # Ensure firm_id is captured if first message did not include it
            if payload.firm_id and not state.metadata.firm_id:
                state.metadata.firm_id = payload.firm_id

        # Append user message to in-memory state (we persist at end)
        state.add_message(role="user", content=payload.message)

        firm_preferences = None
        if payload.model:
            firm_preferences = {"model_override": payload.model}

        # Build messages for LLM (system prompt + persisted history)
        prompt_service = get_prompt_service(redis_pool=redis_pool)
        system_prompt = await prompt_service.build_system_prompt(
            firm_id=payload.firm_id or state.metadata.firm_id,
            tools_enabled=payload.tools_enabled,
        )
        messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        messages.extend(_state_to_llm_messages(state))

        tool_loop = get_tool_loop_service()

        if payload.tools_enabled:
            result = await tool_loop.run_with_messages(
                messages=messages,
                conversation_id=conversation_id,
                firm_preferences=firm_preferences,
                temperature=payload.temperature,
            )
        else:
            # No tools: single non-streaming LLM call using history
            llm = tool_loop._llm  # same underlying LLM service
            resp = await llm.generate_response_sync(
                messages=messages,
                firm_preferences=firm_preferences,
                tools=None,
                stream=False,
                temperature=payload.temperature,
            )
            assistant_msg = tool_loop._extract_assistant_message(resp)
            content, _tool_calls = tool_loop._extract_content_and_tool_calls(assistant_msg)
            result = type("Tmp", (), {})()
            result.conversation_id = conversation_id
            result.final_text = content
            result.tool_results = []
            result.iterations = 1
            result.messages = messages + [{"role": "assistant", "content": content}]

        # Persist new messages produced during this run (assistant/tool messages after the user turn)
        # We skip the first system message; everything else can be stored.
        # State already has the user message; so we append only the new assistant/tool messages
        llm_messages_no_system = [m for m in result.messages if m.get("role") != "system"]

        # Find the last user message index we just added, then persist subsequent messages
        # (This avoids duplicating the entire history.)
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

        # Persist updated state to Redis
        await state_service.save_conversation_state(state)

        return ChatResponse(
            conversation_id=conversation_id,
            response=result.final_text,
            tool_results=[r.model_dump(exclude_none=True) for r in result.tool_results],
            iterations=result.iterations,
        )
    except Exception as e:
        logger.error(f"Chat failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "message": str(e)},
        ) from e


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationStateResponse,
    status_code=status.HTTP_200_OK,
    summary="Get conversation state",
    description="Retrieve conversation state including all messages and metadata.",
)
async def get_conversation_state(
    request: Request, conversation_id: str
) -> ConversationStateResponse:
    """Get conversation state by ID.
    
    Returns the complete conversation state including:
    - All messages (user, assistant, system, tool)
    - Conversation metadata (user_id, firm_id, tokens, etc.)
    - Timestamps
    """
    try:
        redis_pool = getattr(request.app.state, "redis_pool", None)
        state_service = get_state_service(redis_pool=redis_pool)

        state = await state_service.get_conversation_state(conversation_id)
        if state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "Conversation not found", "conversation_id": conversation_id},
            )

        # Convert messages to dict format
        messages = []
        for msg in state.messages:
            msg_dict: Dict[str, Any] = {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
            }
            if msg.tool_calls:
                msg_dict["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                msg_dict["tool_call_id"] = msg.tool_call_id
            if msg.model:
                msg_dict["model"] = msg.model
            if msg.tokens:
                msg_dict["tokens"] = msg.tokens
            messages.append(msg_dict)

        return ConversationStateResponse(
            conversation_id=state.conversation_id,
            user_id=state.metadata.user_id,
            firm_id=state.metadata.firm_id,
            call_id=state.metadata.call_id,
            messages=messages,
            total_tokens=state.metadata.total_tokens,
            model_used=state.metadata.model_used,
            started_at=state.metadata.started_at,
            updated_at=state.metadata.updated_at,
        )
    except HTTPException:
        raise
    except StateError as e:
        logger.error(f"State error getting conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "State service error", "message": str(e)},
        ) from e
    except Exception as e:
        logger.error(f"Error getting conversation state: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "message": str(e)},
        ) from e


@router.delete(
    "/conversations/{conversation_id}",
    response_model=ClearConversationResponse,
    status_code=status.HTTP_200_OK,
    summary="Clear conversation",
    description="Clear/delete a conversation state from Redis.",
)
async def clear_conversation(
    request: Request, conversation_id: str
) -> ClearConversationResponse:
    """Clear conversation state.
    
    Deletes the conversation state from Redis. This is useful for:
    - Starting a fresh conversation
    - Cleaning up old conversations
    - Testing purposes
    """
    try:
        redis_pool = getattr(request.app.state, "redis_pool", None)
        state_service = get_state_service(redis_pool=redis_pool)

        # Check if conversation exists
        state = await state_service.get_conversation_state(conversation_id)
        if state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "Conversation not found", "conversation_id": conversation_id},
            )

        # Clear conversation
        await state_service.clear_conversation(conversation_id)

        logger.info(f"Cleared conversation: {conversation_id}")

        return ClearConversationResponse(
            success=True,
            message=f"Conversation {conversation_id} cleared successfully",
            conversation_id=conversation_id,
        )
    except HTTPException:
        raise
    except StateError as e:
        logger.error(f"State error clearing conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "State service error", "message": str(e)},
        ) from e
    except Exception as e:
        logger.error(f"Error clearing conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "message": str(e)},
        ) from e


