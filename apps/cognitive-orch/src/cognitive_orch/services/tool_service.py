"""Tool execution service for Cognitive Orchestrator.

Phase 5 MVP starts with LexiqAI-native scheduling tools (no external CRMs yet).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional, Type

import httpx
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from cognitive_orch.config import get_settings
from cognitive_orch.models.tools import (
    CheckAvailabilityArgs,
    CheckAvailabilityResult,
    BookAppointmentArgs,
    BookAppointmentResult,
    CreateLeadArgs,
    CreateLeadResult,
    SendNotificationArgs,
    SendNotificationResult,
    ToolError,
    ToolResult,
)
from cognitive_orch.utils.errors import ExternalServiceError, ToolExecutionError, ValidationError
from cognitive_orch.utils.logging import get_logger

logger = get_logger("tool_service")
settings = get_settings()

ToolHandler = Callable[[Any], Awaitable[BaseModel]]


@dataclass(frozen=True)
class ToolSpec:
    """Tool registry entry.

    This is the source of truth for:
    - the tool JSON schema (args_model)
    - how to execute it (handler)
    - safety policy (side-effect + confirmation gate)
    - runtime limits (timeout_seconds)
    """

    name: str
    args_model: Type[BaseModel]
    handler: ToolHandler
    description: str
    is_side_effect: bool
    requires_confirmation: bool
    timeout_seconds: float


class ToolService:
    """Service responsible for tool definitions and safe execution."""

    def __init__(self) -> None:
        self._core_api_url = settings.integration.core_api_url.rstrip("/")
        self._core_api_timeout = settings.integration.core_api_timeout
        self._core_api_api_key = settings.integration.core_api_api_key

        # Allowlist / registry: tool_name -> ToolSpec
        self._tools: Dict[str, ToolSpec] = {
            "check_availability": ToolSpec(
                name="check_availability",
                args_model=CheckAvailabilityArgs,
                handler=self._handle_check_availability,
                description="Return available appointment slots within a time window.",
                is_side_effect=False,
                requires_confirmation=False,
                timeout_seconds=float(self._core_api_timeout),
            ),
            "book_appointment": ToolSpec(
                name="book_appointment",
                args_model=BookAppointmentArgs,
                handler=self._handle_book_appointment,
                description="Book an appointment in LexiqAI scheduling (requires user confirmation).",
                is_side_effect=True,
                requires_confirmation=True,
                timeout_seconds=float(self._core_api_timeout),
            ),
            "create_lead": ToolSpec(
                name="create_lead",
                args_model=CreateLeadArgs,
                handler=self._handle_create_lead,
                description="Create a LexiqAI lead/intake record (requires user confirmation).",
                is_side_effect=True,
                requires_confirmation=True,
                timeout_seconds=float(self._core_api_timeout),
            ),
            "send_notification": ToolSpec(
                name="send_notification",
                args_model=SendNotificationArgs,
                handler=self._handle_send_notification,
                description="Send an email/SMS notification (requires user confirmation).",
                is_side_effect=True,
                requires_confirmation=True,
                timeout_seconds=float(self._core_api_timeout),
            ),
        }

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Return tool definitions in OpenAI-style JSON schema (LiteLLM compatible)."""
        definitions: List[Dict[str, Any]] = []
        for tool_name, spec in self._tools.items():
            schema = spec.args_model.model_json_schema()
            # Ensure we provide a clean parameters object
            parameters = {
                k: v for k, v in schema.items() if k in {"type", "properties", "required", "additionalProperties"}
            }
            if "type" not in parameters:
                parameters["type"] = "object"

            definitions.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "description": spec.description,
                        "parameters": parameters,
                    },
                }
            )
        return definitions

    def _timeout_for(self, tool_name: str) -> float:
        """Get the timeout for a tool (seconds)."""
        spec = self._tools.get(tool_name)
        if not spec:
            return float(self._core_api_timeout)
        return float(spec.timeout_seconds)

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        tool_call_id: Optional[str] = None,
    ) -> ToolResult:
        """Validate and execute a tool by name."""
        spec = self._tools.get(tool_name)
        if spec is None:
            raise ToolExecutionError(
                tool_name=tool_name,
                message="Tool is not allowlisted",
                details={"tool_name": tool_name},
            )

        try:
            parsed_args = spec.args_model.model_validate(arguments)
        except PydanticValidationError as e:
            raise ValidationError(
                message=f"Invalid arguments for tool '{tool_name}'",
                errors={"pydantic": e.errors()},
                details={"tool_name": tool_name},
            ) from e

        # Centralized safety enforcement (per ToolSpec)
        if spec.requires_confirmation:
            confirmed = getattr(parsed_args, "confirmed", None)
            if confirmed is not True:
                raise ValidationError(
                    message=f"User confirmation required for tool '{tool_name}'",
                    errors={"confirmed": "must be true"},
                    details={"tool_name": tool_name},
                )

        try:
            result_payload = await spec.handler(parsed_args)
            return ToolResult(
                tool_name=tool_name,
                tool_call_id=tool_call_id,
                success=True,
                data=result_payload.model_dump(),
            )
        except (ExternalServiceError, ValidationError, ToolExecutionError):
            raise
        except Exception as e:
            logger.error(f"Unhandled tool execution error: {tool_name}: {e}", exc_info=True)
            raise ToolExecutionError(tool_name=tool_name, details={"error": str(e)}) from e

    async def _handle_check_availability(self, args: CheckAvailabilityArgs) -> CheckAvailabilityResult:
        """Tool handler for check_availability -> Core API appointments availability."""
        url = f"{self._core_api_url}/api/v1/appointments/availability"
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self._core_api_api_key:
            headers["X-Internal-API-Key"] = self._core_api_api_key

        payload = args.model_dump(mode="json", exclude_none=True)
        timeout = self._timeout_for("check_availability")

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, json=payload, headers=headers)

            if resp.status_code == 200:
                return CheckAvailabilityResult.model_validate(resp.json())

            # Provide a meaningful message, but avoid leaking details
            raise ExternalServiceError(
                service="api-core",
                message="Core API availability lookup failed",
                status_code=resp.status_code,
                details={"endpoint": "/api/v1/appointments/availability"},
            )
        except httpx.TimeoutException as e:
            raise ExternalServiceError(
                service="api-core",
                message="Core API availability lookup timed out",
                status_code=504,
                details={"endpoint": "/api/v1/appointments/availability"},
            ) from e
        except httpx.RequestError as e:
            raise ExternalServiceError(
                service="api-core",
                message="Core API availability lookup network error",
                status_code=502,
                details={"endpoint": "/api/v1/appointments/availability"},
            ) from e
        except ValueError as e:
            # JSON parse errors
            raise ExternalServiceError(
                service="api-core",
                message="Core API returned invalid JSON",
                status_code=502,
                details={"endpoint": "/api/v1/appointments/availability"},
            ) from e

    async def _handle_book_appointment(self, args: BookAppointmentArgs) -> BookAppointmentResult:
        """Tool handler for book_appointment -> Core API appointments booking."""
        url = f"{self._core_api_url}/api/v1/appointments"
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self._core_api_api_key:
            headers["X-Internal-API-Key"] = self._core_api_api_key

        payload = args.model_dump(mode="json", exclude_none=True)
        timeout = self._timeout_for("book_appointment")

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, json=payload, headers=headers)

            if resp.status_code in (200, 201):
                return BookAppointmentResult.model_validate(resp.json())

            raise ExternalServiceError(
                service="api-core",
                message="Core API appointment booking failed",
                status_code=resp.status_code,
                details={"endpoint": "/api/v1/appointments"},
            )
        except httpx.TimeoutException as e:
            raise ExternalServiceError(
                service="api-core",
                message="Core API appointment booking timed out",
                status_code=504,
                details={"endpoint": "/api/v1/appointments"},
            ) from e
        except httpx.RequestError as e:
            raise ExternalServiceError(
                service="api-core",
                message="Core API appointment booking network error",
                status_code=502,
                details={"endpoint": "/api/v1/appointments"},
            ) from e
        except ValueError as e:
            raise ExternalServiceError(
                service="api-core",
                message="Core API returned invalid JSON",
                status_code=502,
                details={"endpoint": "/api/v1/appointments"},
            ) from e

    async def _handle_create_lead(self, args: CreateLeadArgs) -> CreateLeadResult:
        """Tool handler for create_lead -> Core API leads endpoint."""
        url = f"{self._core_api_url}/api/v1/leads"
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self._core_api_api_key:
            headers["X-Internal-API-Key"] = self._core_api_api_key

        payload = args.model_dump(mode="json", exclude_none=True)
        timeout = self._timeout_for("create_lead")

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, json=payload, headers=headers)

            if resp.status_code in (200, 201):
                return CreateLeadResult.model_validate(resp.json())

            raise ExternalServiceError(
                service="api-core",
                message="Core API lead creation failed",
                status_code=resp.status_code,
                details={"endpoint": "/api/v1/leads"},
            )
        except httpx.TimeoutException as e:
            raise ExternalServiceError(
                service="api-core",
                message="Core API lead creation timed out",
                status_code=504,
                details={"endpoint": "/api/v1/leads"},
            ) from e
        except httpx.RequestError as e:
            raise ExternalServiceError(
                service="api-core",
                message="Core API lead creation network error",
                status_code=502,
                details={"endpoint": "/api/v1/leads"},
            ) from e
        except ValueError as e:
            raise ExternalServiceError(
                service="api-core",
                message="Core API returned invalid JSON",
                status_code=502,
                details={"endpoint": "/api/v1/leads"},
            ) from e

    async def _handle_send_notification(self, args: SendNotificationArgs) -> SendNotificationResult:
        """Tool handler for send_notification -> Core API notifications outbox."""
        url = f"{self._core_api_url}/api/v1/notifications"
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self._core_api_api_key:
            headers["X-Internal-API-Key"] = self._core_api_api_key

        payload = args.model_dump(mode="json", exclude_none=True)
        timeout = self._timeout_for("send_notification")

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, json=payload, headers=headers)

            if resp.status_code in (200, 201):
                return SendNotificationResult.model_validate(resp.json())

            raise ExternalServiceError(
                service="api-core",
                message="Core API notification creation failed",
                status_code=resp.status_code,
                details={"endpoint": "/api/v1/notifications"},
            )
        except httpx.TimeoutException as e:
            raise ExternalServiceError(
                service="api-core",
                message="Core API notification creation timed out",
                status_code=504,
                details={"endpoint": "/api/v1/notifications"},
            ) from e
        except httpx.RequestError as e:
            raise ExternalServiceError(
                service="api-core",
                message="Core API notification creation network error",
                status_code=502,
                details={"endpoint": "/api/v1/notifications"},
            ) from e
        except ValueError as e:
            raise ExternalServiceError(
                service="api-core",
                message="Core API returned invalid JSON",
                status_code=502,
                details={"endpoint": "/api/v1/notifications"},
            ) from e


_tool_service: Optional[ToolService] = None


def get_tool_service() -> ToolService:
    """Get the global tool service instance."""
    global _tool_service
    if _tool_service is None:
        _tool_service = ToolService()
    return _tool_service


