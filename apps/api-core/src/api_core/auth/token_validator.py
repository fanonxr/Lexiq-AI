"""Unified token validator for both Azure AD B2C and internal JWT tokens."""

import logging
from typing import Dict, Optional, Tuple

from api_core.auth.azure_ad import AzureADB2CClient, UserInfo, get_azure_ad_client
from api_core.auth.jwt import TokenPayload, get_jwt_handler
from api_core.config import get_settings
from api_core.exceptions import AuthenticationError

logger = logging.getLogger(__name__)
settings = get_settings()


class TokenValidationResult:
    """Result of token validation."""

    def __init__(
        self,
        user_id: str,
        email: str,
        token_type: str,  # "azure_ad_b2c" or "internal_jwt"
        payload: Optional[TokenPayload] = None,
        user_info: Optional[UserInfo] = None,
        claims: Optional[Dict] = None,
    ):
        """Initialize validation result."""
        self.user_id = user_id
        self.email = email
        self.token_type = token_type
        self.payload = payload  # For internal JWT tokens
        self.user_info = user_info  # For Azure AD B2C tokens
        self.claims = claims or (payload.to_dict() if payload else user_info.claims if user_info else {})

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "email": self.email,
            "token_type": self.token_type,
        }


class UnifiedTokenValidator:
    """Unified validator that handles both Azure AD B2C and internal JWT tokens."""

    def __init__(self):
        """Initialize unified token validator."""
        self.azure_client: Optional[AzureADB2CClient] = None
        self.jwt_handler = get_jwt_handler()

    @property
    def azure_ad_client(self) -> Optional[AzureADB2CClient]:
        """Get Azure AD B2C client (lazy initialization)."""
        if self.azure_client is None:
            try:
                self.azure_client = get_azure_ad_client()
            except Exception as e:
                logger.debug(f"Azure AD B2C client not available: {e}")
                return None
        return self.azure_client

    def _is_azure_ad_b2c_token(self, token: str) -> bool:
        """Heuristic to determine if token is from Azure AD B2C."""
        try:
            # Try to decode header without verification
            from jose import jwt as jose_jwt

            header = jose_jwt.get_unverified_header(token)
            # Azure AD B2C tokens typically have "kid" in header and use RS256
            if "kid" in header and header.get("alg") == "RS256":
                return True
        except Exception:
            pass
        return False

    async def validate_token(self, token: str) -> TokenValidationResult:
        """Validate a token (either Azure AD B2C or internal JWT)."""
        # Try Azure AD B2C first if configured
        if self.azure_ad_client and self._is_azure_ad_b2c_token(token):
            try:
                user_info = await self.azure_ad_client.get_user_info(token)
                return TokenValidationResult(
                    user_id=user_info.oid or "",
                    email=user_info.email or "",
                    token_type="azure_ad_b2c",
                    user_info=user_info,
                    claims=user_info.claims,
                )
            except AuthenticationError:
                # If Azure AD B2C validation fails, try internal JWT
                logger.debug("Azure AD B2C validation failed, trying internal JWT")
            except Exception as e:
                logger.debug(f"Error validating Azure AD B2C token: {e}, trying internal JWT")

        # Try internal JWT token
        try:
            payload = self.jwt_handler.decode_token(token)
            return TokenValidationResult(
                user_id=payload.user_id,
                email=payload.email,
                token_type="internal_jwt",
                payload=payload,
                claims=payload.to_dict(),
            )
        except AuthenticationError:
            raise AuthenticationError("Invalid token: Could not validate as Azure AD B2C or internal JWT token")
        except Exception as e:
            logger.error(f"Error validating internal JWT token: {e}")
            raise AuthenticationError("Token validation failed")

    async def get_user_id_from_token(self, token: str) -> str:
        """Extract user ID from token (convenience method)."""
        result = await self.validate_token(token)
        return result.user_id

    async def get_email_from_token(self, token: str) -> str:
        """Extract email from token (convenience method)."""
        result = await self.validate_token(token)
        return result.email


# Global validator instance
_validator: Optional[UnifiedTokenValidator] = None


def get_token_validator() -> UnifiedTokenValidator:
    """Get the global unified token validator instance."""
    global _validator
    if _validator is None:
        _validator = UnifiedTokenValidator()
    return _validator


async def validate_token(token: str) -> TokenValidationResult:
    """Validate a token (either Azure AD B2C or internal JWT) - convenience function."""
    validator = get_token_validator()
    return await validator.validate_token(token)


async def get_user_id_from_token(token: str) -> str:
    """Extract user ID from token - convenience function."""
    validator = get_token_validator()
    return await validator.get_user_id_from_token(token)


async def get_email_from_token(token: str) -> str:
    """Extract email from token - convenience function."""
    validator = get_token_validator()
    return await validator.get_email_from_token(token)
