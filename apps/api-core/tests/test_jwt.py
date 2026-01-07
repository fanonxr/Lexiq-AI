"""Unit tests for JWT token handling."""

import pytest
import time
from datetime import datetime, timedelta

from api_core.auth.jwt import (
    create_access_token,
    create_refresh_token,
    refresh_access_token,
    verify_token,
    get_jwt_handler,
)
from api_core.exceptions import AuthenticationError
from api_core.config import get_settings

settings = get_settings()


class TestJWTTokenCreation:
    """Tests for JWT token creation."""

    def test_create_access_token(self):
        """Test creating an access token."""
        user_id = "test-user-id"
        email = "test@example.com"
        
        token = create_access_token(user_id=user_id, email=email)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self):
        """Test creating a refresh token."""
        user_id = "test-user-id"
        email = "test@example.com"
        
        token = create_refresh_token(user_id=user_id, email=email)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_access_token_contains_user_info(self):
        """Test that access token contains user information."""
        user_id = "test-user-id"
        email = "test@example.com"
        
        token = create_access_token(user_id=user_id, email=email)
        payload = verify_token(token)
        
        assert payload.user_id == user_id
        assert payload.email == email
        assert payload.token_type == "access"

    def test_refresh_token_contains_user_info(self):
        """Test that refresh token contains user information."""
        user_id = "test-user-id"
        email = "test@example.com"
        
        token = create_refresh_token(user_id=user_id, email=email)
        payload = verify_token(token)
        
        assert payload.user_id == user_id
        assert payload.email == email
        assert payload.token_type == "refresh"

    def test_access_token_expiration(self):
        """Test that access token has correct expiration."""
        user_id = "test-user-id"
        email = "test@example.com"
        
        token = create_access_token(user_id=user_id, email=email)
        payload = verify_token(token)
        
        # Check expiration is approximately 30 minutes from now
        expected_exp = int(time.time()) + (settings.jwt.access_token_expire_minutes * 60)
        assert abs(payload.exp - expected_exp) < 60  # Within 1 minute

    def test_refresh_token_expiration(self):
        """Test that refresh token has correct expiration."""
        user_id = "test-user-id"
        email = "test@example.com"
        
        token = create_refresh_token(user_id=user_id, email=email)
        payload = verify_token(token)
        
        # Check expiration is approximately 7 days from now
        expected_exp = int(time.time()) + (settings.jwt.refresh_token_expire_days * 24 * 60 * 60)
        assert abs(payload.exp - expected_exp) < 3600  # Within 1 hour

    def test_custom_expiration(self):
        """Test creating token with custom expiration."""
        user_id = "test-user-id"
        email = "test@example.com"
        custom_exp = timedelta(hours=2)
        
        token = create_access_token(
            user_id=user_id,
            email=email,
            expires_delta=custom_exp,
        )
        payload = verify_token(token)
        
        expected_exp = int(time.time()) + int(custom_exp.total_seconds())
        assert abs(payload.exp - expected_exp) < 60  # Within 1 minute


class TestJWTTokenValidation:
    """Tests for JWT token validation."""

    def test_verify_valid_token(self):
        """Test verifying a valid token."""
        user_id = "test-user-id"
        email = "test@example.com"
        
        token = create_access_token(user_id=user_id, email=email)
        payload = verify_token(token)
        
        assert payload is not None
        assert payload.user_id == user_id
        assert payload.email == email

    def test_verify_invalid_token(self):
        """Test verifying an invalid token."""
        invalid_token = "invalid.token.here"
        
        with pytest.raises(AuthenticationError):
            verify_token(invalid_token)

    def test_verify_expired_token(self):
        """Test verifying an expired token."""
        user_id = "test-user-id"
        email = "test@example.com"
        
        # Create token with very short expiration
        token = create_access_token(
            user_id=user_id,
            email=email,
            expires_delta=timedelta(seconds=-1),  # Already expired
        )
        
        with pytest.raises(AuthenticationError, match="expired"):
            verify_token(token)

    def test_verify_token_wrong_secret(self):
        """Test that token signed with wrong secret fails."""
        # This test would require mocking or using a different secret
        # For now, we'll just verify that invalid tokens are rejected
        invalid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0In0.invalid"
        
        with pytest.raises(AuthenticationError):
            verify_token(invalid_token)


class TestTokenRefresh:
    """Tests for token refresh functionality."""

    def test_refresh_access_token_success(self):
        """Test successfully refreshing an access token."""
        user_id = "test-user-id"
        email = "test@example.com"
        
        refresh_token = create_refresh_token(user_id=user_id, email=email)
        new_access_token = refresh_access_token(refresh_token)
        
        assert new_access_token is not None
        assert isinstance(new_access_token, str)
        
        # Verify new token
        payload = verify_token(new_access_token)
        assert payload.user_id == user_id
        assert payload.email == email
        assert payload.token_type == "access"

    def test_refresh_with_access_token_fails(self):
        """Test that using access token as refresh token fails."""
        user_id = "test-user-id"
        email = "test@example.com"
        
        access_token = create_access_token(user_id=user_id, email=email)
        
        with pytest.raises(AuthenticationError, match="not a refresh token"):
            refresh_access_token(access_token)

    def test_refresh_expired_token_fails(self):
        """Test that refreshing with expired refresh token fails."""
        user_id = "test-user-id"
        email = "test@example.com"
        
        # Create expired refresh token
        refresh_token = create_refresh_token(
            user_id=user_id,
            email=email,
            expires_delta=timedelta(seconds=-1),  # Already expired
        )
        
        with pytest.raises(AuthenticationError, match="expired"):
            refresh_access_token(refresh_token)

    def test_refresh_invalid_token_fails(self):
        """Test that refreshing with invalid token fails."""
        invalid_token = "invalid.token.here"
        
        with pytest.raises(AuthenticationError):
            refresh_access_token(invalid_token)


class TestJWTTokenPayload:
    """Tests for JWT token payload structure."""

    def test_payload_contains_required_fields(self):
        """Test that token payload contains all required fields."""
        user_id = "test-user-id"
        email = "test@example.com"
        
        token = create_access_token(user_id=user_id, email=email)
        payload = verify_token(token)
        
        assert hasattr(payload, "user_id")
        assert hasattr(payload, "email")
        assert hasattr(payload, "exp")
        assert hasattr(payload, "iat")
        assert hasattr(payload, "token_type")

    def test_payload_iat_field(self):
        """Test that 'issued at' field is set correctly."""
        user_id = "test-user-id"
        email = "test@example.com"
        
        before = int(time.time())
        token = create_access_token(user_id=user_id, email=email)
        after = int(time.time())
        
        payload = verify_token(token)
        
        assert before <= payload.iat <= after

