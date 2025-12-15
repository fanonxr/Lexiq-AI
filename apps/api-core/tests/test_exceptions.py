"""Tests for exception handling."""

import pytest
from fastapi.testclient import TestClient

from api_core.exceptions import (
    APIException,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    DatabaseError,
    ExternalServiceError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)


def test_api_exception():
    """Test base APIException."""
    exc = APIException("Test error", status_code=400, code="TEST_ERROR")
    assert exc.message == "Test error"
    assert exc.status_code == 400
    assert exc.code == "TEST_ERROR"
    assert exc.to_dict()["error"]["message"] == "Test error"


def test_authentication_error():
    """Test AuthenticationError."""
    exc = AuthenticationError("Invalid credentials")
    assert exc.status_code == 401
    assert exc.code == "AUTHENTICATION_ERROR"
    assert exc.message == "Invalid credentials"


def test_authorization_error():
    """Test AuthorizationError."""
    exc = AuthorizationError("Access denied")
    assert exc.status_code == 403
    assert exc.code == "AUTHORIZATION_ERROR"


def test_validation_error():
    """Test ValidationError."""
    errors = {"email": ["Invalid email format"]}
    exc = ValidationError("Validation failed", errors=errors)
    assert exc.status_code == 422
    assert exc.code == "VALIDATION_ERROR"
    assert "validation_errors" in exc.details


def test_not_found_error():
    """Test NotFoundError."""
    exc = NotFoundError("User", resource_id="123")
    assert exc.status_code == 404
    assert exc.code == "NOT_FOUND"
    assert "User not found with id: 123" in exc.message


def test_conflict_error():
    """Test ConflictError."""
    exc = ConflictError("Resource already exists")
    assert exc.status_code == 409
    assert exc.code == "CONFLICT"


def test_database_error():
    """Test DatabaseError."""
    exc = DatabaseError("Connection failed")
    assert exc.status_code == 500
    assert exc.code == "DATABASE_ERROR"


def test_external_service_error():
    """Test ExternalServiceError."""
    exc = ExternalServiceError("payment_service", "Service unavailable")
    assert exc.status_code == 502
    assert exc.code == "EXTERNAL_SERVICE_ERROR"
    assert exc.details["service"] == "payment_service"


def test_rate_limit_error():
    """Test RateLimitError."""
    exc = RateLimitError("Too many requests", retry_after=60)
    assert exc.status_code == 429
    assert exc.code == "RATE_LIMIT_EXCEEDED"
    assert exc.details["retry_after"] == 60
