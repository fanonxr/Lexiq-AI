"""JWT token handling for internal authentication."""

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from jose import JWTError, jwt

from api_core.config import get_settings
from api_core.exceptions import AuthenticationError

logger = logging.getLogger(__name__)
settings = get_settings()


class TokenPayload:
    """JWT token payload structure."""

    def __init__(
        self,
        user_id: str,
        email: str,
        exp: Optional[int] = None,
        iat: Optional[int] = None,
        token_type: str = "access",
        **kwargs: Any,
    ):
        """Initialize token payload."""
        self.user_id = user_id
        self.email = email
        self.token_type = token_type
        self.exp = exp or int(time.time()) + settings.jwt.access_token_expire_minutes * 60
        self.iat = iat or int(time.time())
        self.extra_claims = kwargs

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JWT encoding."""
        payload = {
            "sub": self.user_id,  # Subject (user ID)
            "email": self.email,
            "exp": self.exp,  # Expiration time
            "iat": self.iat,  # Issued at time
            "type": self.token_type,  # Token type (access, refresh)
        }
        payload.update(self.extra_claims)
        return payload

    @classmethod
    def from_dict(cls, claims: Dict[str, Any]) -> "TokenPayload":
        """Create TokenPayload from decoded JWT claims."""
        return cls(
            user_id=claims.get("sub", ""),
            email=claims.get("email", ""),
            exp=claims.get("exp"),
            iat=claims.get("iat"),
            token_type=claims.get("type", "access"),
            **{k: v for k, v in claims.items() if k not in ["sub", "email", "exp", "iat", "type"]},
        )


class JWTTokenHandler:
    """Handler for JWT token generation and validation."""

    def __init__(self):
        """Initialize JWT token handler."""
        self.config = settings.jwt
        self.secret_key = self.config.secret_key
        self.algorithm = self.config.algorithm

    def encode_token(self, payload: TokenPayload) -> str:
        """Encode a token payload into a JWT token."""
        try:
            token_data = payload.to_dict()
            token = jwt.encode(
                token_data,
                self.secret_key,
                algorithm=self.algorithm,
            )
            logger.debug(f"Generated JWT token for user: {payload.user_id}")
            return token
        except Exception as e:
            logger.error(f"Error encoding JWT token: {e}")
            raise AuthenticationError("Failed to generate token")

    def decode_token(self, token: str, verify_exp: bool = True) -> TokenPayload:
        """Decode and validate a JWT token."""
        try:
            options = {
                "verify_signature": True,
                "verify_exp": verify_exp,
            }

            claims = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options=options,
            )

            # Validate token type
            token_type = claims.get("type", "access")
            if token_type not in ["access", "refresh"]:
                raise AuthenticationError("Invalid token type")

            payload = TokenPayload.from_dict(claims)
            logger.debug(f"Decoded JWT token for user: {payload.user_id}")
            return payload

        except JWTError as e:
            logger.warning(f"JWT token validation failed: {e}")
            raise AuthenticationError(f"Invalid token: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error decoding JWT token: {e}")
            raise AuthenticationError(f"Token validation failed: {str(e)}")

    def create_access_token(
        self,
        user_id: str,
        email: str,
        expires_delta: Optional[timedelta] = None,
        **extra_claims: Any,
    ) -> str:
        """Create an access token for a user."""
        if expires_delta:
            exp = int((datetime.utcnow() + expires_delta).timestamp())
        else:
            exp = int(
                (datetime.utcnow() + timedelta(minutes=self.config.access_token_expire_minutes)).timestamp()
            )

        payload = TokenPayload(
            user_id=user_id,
            email=email,
            exp=exp,
            token_type="access",
            **extra_claims,
        )

        return self.encode_token(payload)

    def create_refresh_token(
        self,
        user_id: str,
        email: str,
        expires_delta: Optional[timedelta] = None,
        **extra_claims: Any,
    ) -> str:
        """Create a refresh token for a user."""
        # Refresh tokens typically have longer expiration
        if expires_delta:
            exp = int((datetime.utcnow() + expires_delta).timestamp())
        else:
            # Use configured refresh token expiration
            exp = int(
                (datetime.utcnow() + timedelta(days=self.config.refresh_token_expire_days)).timestamp()
            )

        payload = TokenPayload(
            user_id=user_id,
            email=email,
            exp=exp,
            token_type="refresh",
            **extra_claims,
        )

        return self.encode_token(payload)

    def verify_token(self, token: str) -> TokenPayload:
        """Verify and decode a token (alias for decode_token)."""
        return self.decode_token(token)

    def refresh_access_token(self, refresh_token: str) -> str:
        """Generate a new access token from a refresh token."""
        try:
            # Decode refresh token (don't verify expiration yet to get user info)
            payload = self.decode_token(refresh_token, verify_exp=False)

            # Verify it's actually a refresh token
            if payload.token_type != "refresh":
                raise AuthenticationError("Token is not a refresh token")

            # Check if refresh token is expired
            if payload.exp and payload.exp < int(time.time()):
                raise AuthenticationError("Refresh token has expired")

            # Generate new access token with same user info
            return self.create_access_token(
                user_id=payload.user_id,
                email=payload.email,
                **payload.extra_claims,
            )

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            raise AuthenticationError("Failed to refresh token")


# Global handler instance
_handler: Optional[JWTTokenHandler] = None


def get_jwt_handler() -> JWTTokenHandler:
    """Get the global JWT token handler instance."""
    global _handler
    if _handler is None:
        _handler = JWTTokenHandler()
    return _handler


def create_access_token(
    user_id: str,
    email: str,
    expires_delta: Optional[timedelta] = None,
    **extra_claims: Any,
) -> str:
    """Create an access token for a user (convenience function)."""
    handler = get_jwt_handler()
    return handler.create_access_token(user_id, email, expires_delta, **extra_claims)


def create_refresh_token(
    user_id: str,
    email: str,
    expires_delta: Optional[timedelta] = None,
    **extra_claims: Any,
) -> str:
    """Create a refresh token for a user (convenience function)."""
    handler = get_jwt_handler()
    return handler.create_refresh_token(user_id, email, expires_delta, **extra_claims)


def decode_token(token: str, verify_exp: bool = True) -> TokenPayload:
    """Decode and validate a JWT token (convenience function)."""
    handler = get_jwt_handler()
    return handler.decode_token(token, verify_exp)


def verify_token(token: str) -> TokenPayload:
    """Verify and decode a token (convenience function)."""
    handler = get_jwt_handler()
    return handler.verify_token(token)


def refresh_access_token(refresh_token: str) -> str:
    """Generate a new access token from a refresh token (convenience function)."""
    handler = get_jwt_handler()
    return handler.refresh_access_token(refresh_token)
