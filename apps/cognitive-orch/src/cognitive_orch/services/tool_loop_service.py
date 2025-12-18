"""LLM tool-calling loop (tool execution orchestration).

This implements the core "LLM -> tool_calls -> tool_results -> final response" loop for Phase 5.

Notes:
- Non-streaming only (MVP). Streaming tool-calls require incremental parsing.
- We do not trust the LLM to generate idempotency keys; we override them in the loop.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from cognitive_orch.services.llm_service import get_llm_service
from cognitive_orch.services.prompt_service import BASE_PERSONA_PROMPT, TOOL_POLICY_PROMPT
from cognitive_orch.services.tool_service import get_tool_service
from cognitive_orch.models.tools import ToolError, ToolResult
from cognitive_orch.utils.logging import get_logger

logger = get_logger("tool_loop_service")


# Backwards-compatible default for tests; Phase 6 uses PromptService for firm-aware prompts.
TOOL_SYSTEM_PROMPT = BASE_PERSONA_PROMPT + "\n\n" + TOOL_POLICY_PROMPT


@dataclass(frozen=True)
class ToolLoopRunResult:
    """Result of one tool-loop run."""

    conversation_id: str
    final_text: str
    tool_results: List[ToolResult]
    iterations: int
    messages: List[Dict[str, Any]]


class ToolLoopService:
    """Service that runs the LLM tool-calling loop."""

    def __init__(self) -> None:
        self._llm = get_llm_service()
        self._tools = get_tool_service()

    def _compute_idempotency_key(
        self, conversation_id: str, tool_name: str, args: Dict[str, Any]
    ) -> str:
        """Compute a stable idempotency key for a tool call.

        We exclude fields that shouldn't affect idempotency.
        """
        canonical = dict(args)
        canonical.pop("idempotency_key", None)
        # "confirmed" should not change the identity of the action (it is a gate)
        canonical.pop("confirmed", None)

        payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str)
        raw = f"{conversation_id}:{tool_name}:{payload}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def _maybe_override_idempotency_key(
        self, conversation_id: str, tool_name: str, args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Override idempotency_key if the tool args support it."""
        if "idempotency_key" not in args:
            return args
        new_args = dict(args)
        new_args["idempotency_key"] = self._compute_idempotency_key(conversation_id, tool_name, args)
        return new_args

    def _extract_assistant_message(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract assistant message object from a non-streaming LiteLLM response."""
        if "choices" not in response or not response["choices"]:
            return {}
        choice0 = response["choices"][0] or {}
        msg = choice0.get("message") or {}
        return msg or {}

    def _extract_content_and_tool_calls(
        self, assistant_msg: Dict[str, Any]
    ) -> Tuple[str, List[Dict[str, Any]]]:
        content = assistant_msg.get("content") or ""
        tool_calls = assistant_msg.get("tool_calls") or []
        if not isinstance(tool_calls, list):
            tool_calls = []
        return content, tool_calls

    def _parse_tool_call(self, tool_call: Dict[str, Any]) -> Tuple[str, str, Dict[str, Any]]:
        """Parse a tool call into (tool_call_id, tool_name, arguments_dict)."""
        tool_call_id = tool_call.get("id") or ""
        fn = tool_call.get("function") or {}
        tool_name = fn.get("name") or ""
        raw_args = fn.get("arguments") or "{}"
        if isinstance(raw_args, dict):
            args = raw_args
        else:
            try:
                args = json.loads(raw_args)
            except Exception:
                args = {}
        if not isinstance(args, dict):
            args = {}
        return tool_call_id, tool_name, args

    def _tool_result_to_tool_message(self, tool_call_id: str, result: ToolResult) -> Dict[str, Any]:
        """Format a tool result as an OpenAI-style tool message."""
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": result.model_dump_json(exclude_none=True),
        }

    async def run(
        self,
        user_message: str,
        conversation_id: Optional[str] = None,
        firm_preferences: Optional[Dict[str, Any]] = None,
        temperature: float = 0.2,
        max_iterations: int = 5,
    ) -> ToolLoopRunResult:
        """Run the tool loop (non-streaming) with a single user message.

        This is primarily used for simple testing. For real chat integration with history,
        use `run_with_messages(...)`.
        """
        conv_id = conversation_id or str(uuid.uuid4())
        tools_def = self._tools.get_tool_definitions()

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": TOOL_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        return await self.run_with_messages(
            messages=messages,
            conversation_id=conv_id,
            firm_preferences=firm_preferences,
            temperature=temperature,
            max_iterations=max_iterations,
            tools_definitions=tools_def,
        )

    async def run_with_messages(
        self,
        messages: List[Dict[str, Any]],
        conversation_id: str,
        firm_preferences: Optional[Dict[str, Any]] = None,
        temperature: float = 0.2,
        max_iterations: int = 5,
        tools_definitions: Optional[List[Dict[str, Any]]] = None,
    ) -> ToolLoopRunResult:
        """Run the tool loop (non-streaming) starting from a pre-built message list.

        Expectations:
        - `messages` should already include a system prompt message
        - `messages` should include the latest user message and any prior history
        """
        tools_def = tools_definitions or self._tools.get_tool_definitions()
        results: List[ToolResult] = []

        for i in range(max_iterations):
            resp = await self._llm.generate_response_sync(
                messages=messages,
                firm_preferences=firm_preferences,
                tools=tools_def,
                stream=False,
                temperature=temperature,
            )

            assistant_msg = self._extract_assistant_message(resp)
            content, tool_calls = self._extract_content_and_tool_calls(assistant_msg)

            # Always append the assistant message we received (content may be empty when tool_calls exist)
            assistant_entry: Dict[str, Any] = {"role": "assistant", "content": content}
            if tool_calls:
                assistant_entry["tool_calls"] = tool_calls
            messages.append(assistant_entry)

            if not tool_calls:
                return ToolLoopRunResult(
                    conversation_id=conversation_id,
                    final_text=content,
                    tool_results=results,
                    iterations=i + 1,
                    messages=messages,
                )

            # Execute tool calls in order, append tool messages
            for tc in tool_calls:
                tool_call_id, tool_name, args = self._parse_tool_call(tc)
                if not tool_name:
                    err = ToolResult(
                        tool_name="",
                        tool_call_id=tool_call_id or None,
                        success=False,
                        data={},
                        error=ToolError(code="INVALID_TOOL_CALL", message="Missing tool name", details={}),
                    )
                    results.append(err)
                    messages.append(self._tool_result_to_tool_message(tool_call_id, err))
                    continue

                args = self._maybe_override_idempotency_key(conv_id, tool_name, args)

                try:
                    r = await self._tools.execute_tool(
                        tool_name=tool_name,
                        arguments=args,
                        tool_call_id=tool_call_id or None,
                    )
                    results.append(r)
                    messages.append(self._tool_result_to_tool_message(tool_call_id, r))
                except Exception as e:
                    logger.warning(
                        f"Tool execution failed: tool={tool_name}, error={type(e).__name__}: {e}",
                        exc_info=True,
                    )
                    err = ToolResult(
                        tool_name=tool_name,
                        tool_call_id=tool_call_id or None,
                        success=False,
                        data={},
                        error=ToolError(
                            code="TOOL_EXEC_FAILED",
                            message=str(e),
                            details={"tool_name": tool_name, "error_type": type(e).__name__},
                        ),
                    )
                    results.append(err)
                    messages.append(self._tool_result_to_tool_message(tool_call_id, err))

        # Max iterations reached; return best-effort content
        return ToolLoopRunResult(
            conversation_id=conversation_id,
            final_text="I’m unable to complete this request right now due to too many tool steps.",
            tool_results=results,
            iterations=max_iterations,
            messages=messages,
        )


_tool_loop_service: Optional[ToolLoopService] = None


def get_tool_loop_service() -> ToolLoopService:
    """Get the global tool-loop service instance."""
    global _tool_loop_service
    if _tool_loop_service is None:
        _tool_loop_service = ToolLoopService()
    return _tool_loop_service


