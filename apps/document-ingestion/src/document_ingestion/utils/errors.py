"""Custom exception classes for the Document Ingestion service."""

from typing import Any, Dict, Optional


class IngestionException(Exception):
    """Base exception for all Document Ingestion errors."""

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


class ParsingError(IngestionException):
    """Exception raised for document parsing errors."""

    def __init__(
        self,
        message: str = "Document parsing failed",
        file_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if file_type:
            error_details["file_type"] = file_type
        super().__init__(
            message=message,
            status_code=422,
            code="PARSING_ERROR",
            details=error_details,
        )


class ChunkingError(IngestionException):
    """Exception raised for text chunking errors."""

    def __init__(
        self,
        message: str = "Text chunking failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=500,
            code="CHUNKING_ERROR",
            details=details,
        )


class EmbeddingError(IngestionException):
    """Exception raised for embedding generation errors."""

    def __init__(
        self,
        message: str = "Embedding generation failed",
        model: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if model:
            error_details["model"] = model
        super().__init__(
            message=message,
            status_code=502,
            code="EMBEDDING_ERROR",
            details=error_details,
        )


class QdrantError(IngestionException):
    """Exception raised for Qdrant operation errors."""

    def __init__(
        self,
        message: str = "Qdrant operation failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=502,
            code="QDRANT_ERROR",
            details=details,
        )


class StorageError(IngestionException):
    """Exception raised for storage operation errors."""

    def __init__(
        self,
        message: str = "Storage operation failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=502,
            code="STORAGE_ERROR",
            details=details,
        )


class QueueError(IngestionException):
    """Exception raised for message queue errors."""

    def __init__(
        self,
        message: str = "Message queue operation failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=502,
            code="QUEUE_ERROR",
            details=details,
        )


class ValidationError(IngestionException):
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


class NotFoundError(IngestionException):
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


class ExternalServiceError(IngestionException):
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

