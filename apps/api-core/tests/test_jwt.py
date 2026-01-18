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
        from unittest.mock import patch
        from api_core.config import Settings, JWTSettings
        from api_core.auth.jwt import JWTTokenHandler
        import api_core.auth.jwt as jwt_module
        
        user_id = "test-user-id"
        email = "test@example.com"
        
        # Create mock settings with 30 minutes expiration
        mock_jwt_settings = JWTSettings(access_token_expire_minutes=30)
        mock_settings = Settings(jwt=mock_jwt_settings)
        
        # Use expected default of 30 minutes
        expected_minutes = 30
        
        # Reset the global handler and patch settings
        original_handler = jwt_module._handler
        original_settings = jwt_module.settings
        try:
            # Reset handler to force reinitialization
            jwt_module._handler = None
            
            # Patch the module-level settings BEFORE creating handler
            with patch.object(jwt_module, "settings", mock_settings, create=False):
                # Create a new handler instance with patched settings
                handler = JWTTokenHandler()
                # Verify the handler got the right config
                assert handler.config.access_token_expire_minutes == 30, \
                    f"Handler config has {handler.config.access_token_expire_minutes} minutes, expected 30"
                
                # Use handler directly to create token
                token = handler.create_access_token(user_id=user_id, email=email)
                payload = handler.decode_token(token)
                
                # Check expiration is approximately 30 minutes from now
                expected_exp = int(time.time()) + (expected_minutes * 60)
                # Allow up to 2 minutes tolerance for timing differences
                actual_diff = abs(payload.exp - expected_exp)
                assert actual_diff < 120, \
                    f"Expected exp ~{expected_exp}, got {payload.exp}, diff: {actual_diff} seconds " \
                    f"({actual_diff/60:.1f} minutes). Handler config: {handler.config.access_token_expire_minutes} minutes"
        finally:
            # Restore original handler and settings
            jwt_module._handler = original_handler
            jwt_module.settings = original_settings

    def test_refresh_token_expiration(self):
        """Test that refresh token has correct expiration."""
        from unittest.mock import patch
        from api_core.config import Settings, JWTSettings
        from api_core.auth.jwt import JWTTokenHandler
        import api_core.auth.jwt as jwt_module
        
        user_id = "test-user-id"
        email = "test@example.com"
        
        # Create mock settings with 7 days expiration
        mock_jwt_settings = JWTSettings(refresh_token_expire_days=7)
        mock_settings = Settings(jwt=mock_jwt_settings)
        
        # Use expected default of 7 days
        expected_days = 7
        
        # Reset the global handler and patch settings
        original_handler = jwt_module._handler
        original_settings = jwt_module.settings
        try:
            # Reset handler to force reinitialization
            jwt_module._handler = None
            
            # Patch the module-level settings BEFORE creating handler
            with patch.object(jwt_module, "settings", mock_settings, create=False):
                # Create a new handler instance with patched settings
                handler = JWTTokenHandler()
                # Verify the handler got the right config
                assert handler.config.refresh_token_expire_days == 7, \
                    f"Handler config has {handler.config.refresh_token_expire_days} days, expected 7"
                
                # Use handler directly to create token
                token = handler.create_refresh_token(user_id=user_id, email=email)
                payload = handler.decode_token(token)
                
                # Check expiration is approximately 7 days from now
                expected_exp = int(time.time()) + (expected_days * 24 * 60 * 60)
                # Allow up to 2 hours tolerance for timing differences
                actual_diff = abs(payload.exp - expected_exp)
                assert actual_diff < 7200, \
                    f"Expected exp ~{expected_exp}, got {payload.exp}, diff: {actual_diff} seconds " \
                    f"({actual_diff/3600:.1f} hours). Handler config: {handler.config.refresh_token_expire_days} days"
        finally:
            # Restore original handler and settings
            jwt_module._handler = original_handler
            jwt_module.settings = original_settings

    def test_custom_expiration(self):
        """Test creating token with custom expiration."""
        from api_core.auth.jwt import get_jwt_handler
        
        user_id = "test-user-id"
        email = "test@example.com"
        custom_exp = timedelta(hours=2)
        
        # Custom expiration should override settings, so no need to mock
        # Use handler directly to ensure we're using the current handler
        handler = get_jwt_handler()
        token = handler.create_access_token(
            user_id=user_id,
            email=email,
            expires_delta=custom_exp,
        )
        payload = handler.decode_token(token)
        
        expected_exp = int(time.time()) + int(custom_exp.total_seconds())
        # Allow up to 2 minutes tolerance for timing differences
        actual_diff = abs(payload.exp - expected_exp)
        assert actual_diff < 120, f"Expected exp ~{expected_exp}, got {payload.exp}, diff: {actual_diff} seconds"


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
        
        # Create token with expiration far in the past
        token = create_access_token(
            user_id=user_id,
            email=email,
            expires_delta=timedelta(days=-1),  # Expired 1 day ago
        )
        
        # Wait a moment to ensure token is definitely expired
        import time
        time.sleep(0.1)
        
        with pytest.raises(AuthenticationError):
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
        
        # Create expired refresh token (expired 1 day ago)
        refresh_token = create_refresh_token(
            user_id=user_id,
            email=email,
            expires_delta=timedelta(days=-1),  # Expired 1 day ago
        )
        
        # Wait a moment to ensure token is definitely expired
        time.sleep(0.1)
        
        with pytest.raises(AuthenticationError):
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

