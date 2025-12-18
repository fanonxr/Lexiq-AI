"""Custom exception classes for the Cognitive Orchestrator service."""

from typing import Any, Dict, Optional


class OrchestratorException(Exception):
    """Base exception for all Orchestrator errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.code = code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON response."""
        return {
            "error": {
                "message": self.message,
                "code": self.code,
                "status_code": self.status_code,
                "details": self.details,
            }
        }


class LLMError(OrchestratorException):
    """Exception raised for LLM-related errors."""

    def __init__(
        self,
        message: str = "LLM operation failed",
        model: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if model:
            error_details["model"] = model
        super().__init__(
            message=message,
            status_code=502,
            code="LLM_ERROR",
            details=error_details,
        )


class RAGError(OrchestratorException):
    """Exception raised for RAG-related errors."""

    def __init__(
        self,
        message: str = "RAG operation failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=502,
            code="RAG_ERROR",
            details=details,
        )


class StateError(OrchestratorException):
    """Exception raised for conversation state errors."""

    def __init__(
        self,
        message: str = "Conversation state operation failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=500,
            code="STATE_ERROR",
            details=details,
        )


class ToolExecutionError(OrchestratorException):
    """Exception raised for tool execution errors."""

    def __init__(
        self,
        tool_name: str,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_message = message or f"Tool '{tool_name}' execution failed"
        error_details = details or {}
        error_details["tool_name"] = tool_name
        super().__init__(
            message=error_message,
            status_code=500,
            code="TOOL_EXECUTION_ERROR",
            details=error_details,
        )


class ValidationError(OrchestratorException):
    """Exception raised for validation errors."""

    def __init__(
        self,
        message: str = "Validation failed",
        errors: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if errors:
            error_details["validation_errors"] = errors
        super().__init__(
            message=message,
            status_code=422,
            code="VALIDATION_ERROR",
            details=error_details,
        )


class NotFoundError(OrchestratorException):
    """Exception raised when a resource is not found."""

    def __init__(
        self,
        resource: str = "Resource",
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        message = f"{resource} not found"
        if resource_id:
            message += f" with id: {resource_id}"
        error_details = details or {}
        error_details["resource"] = resource
        if resource_id:
            error_details["resource_id"] = resource_id
        super().__init__(
            message=message,
            status_code=404,
            code="NOT_FOUND",
            details=error_details,
        )


class ExternalServiceError(OrchestratorException):
    """Exception raised when external service calls fail."""

    def __init__(
        self,
        service: str,
        message: Optional[str] = None,
        status_code: int = 502,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_message = message or f"External service '{service}' unavailable"
        error_details = details or {}
        error_details["service"] = service
        super().__init__(
            message=error_message,
            status_code=status_code,
            code="EXTERNAL_SERVICE_ERROR",
            details=error_details,
        )

