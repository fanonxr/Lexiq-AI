"""Custom exception classes for the API Core service."""

from typing import Any, Dict, Optional


class APIException(Exception):
    """Base exception for all API errors."""

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


class AuthenticationError(APIException):
    """Exception raised for authentication failures."""

    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=401,
            code="AUTHENTICATION_ERROR",
            details=details,
        )


class AuthorizationError(APIException):
    """Exception raised for authorization failures."""

    def __init__(
        self,
        message: str = "Insufficient permissions",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=403,
            code="AUTHORIZATION_ERROR",
            details=details,
        )


class ValidationError(APIException):
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


class NotFoundError(APIException):
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


class ConflictError(APIException):
    """Exception raised when a resource conflict occurs."""

    def __init__(
        self,
        message: str = "Resource conflict",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=409,
            code="CONFLICT",
            details=details,
        )


class DatabaseError(APIException):
    """Exception raised for database-related errors."""

    def __init__(
        self,
        message: str = "Database operation failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=500,
            code="DATABASE_ERROR",
            details=details,
        )


class ExternalServiceError(APIException):
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


class RateLimitError(APIException):
    """Exception raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if retry_after:
            error_details["retry_after"] = retry_after
        super().__init__(
            message=message,
            status_code=429,
            code="RATE_LIMIT_EXCEEDED",
            details=error_details,
        )
