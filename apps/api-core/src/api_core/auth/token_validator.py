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
        """Get Azure AD B2C / Entra ID client (lazy initialization)."""
        if self.azure_client is None:
            try:
                from api_core.config import get_settings
                settings = get_settings()
                
                # Check if Azure AD is configured before trying to initialize
                if not settings.azure_ad_b2c.is_configured:
                    logger.debug(
                        f"Azure AD / Entra ID is not configured. "
                        f"tenant_id={'set' if settings.azure_ad_b2c.tenant_id else 'missing'}, "
                        f"client_id={'set' if settings.azure_ad_b2c.client_id else 'missing'}"
                    )
                    return None
                
                self.azure_client = get_azure_ad_client()
                auth_type = "Azure AD B2C" if settings.azure_ad_b2c.is_b2c else "Microsoft Entra ID"
                logger.debug(f"{auth_type} client initialized")
            except Exception as e:
                logger.debug(f"Azure AD B2C / Entra ID client not available: {e}")
                return None
        return self.azure_client

    def _is_azure_ad_b2c_token(self, token: str) -> bool:
        """Heuristic to determine if token is from Azure AD B2C or Entra ID."""
        try:
            # Try to decode header without verification
            from jose import jwt as jose_jwt

            header = jose_jwt.get_unverified_header(token)
            alg = header.get("alg", "")
            
            # Azure AD B2C/Entra ID tokens use RS256 (asymmetric)
            # Internal JWT tokens use HS256 (symmetric)
            # If it's RS256, it's definitely an Azure AD token
            if alg == "RS256":
                # Also decode payload to check issuer for confirmation
                try:
                    payload = jose_jwt.get_unverified_claims(token)
                    issuer = payload.get("iss", "")
                    # Check if issuer looks like Azure AD/Entra ID
                    if "login.microsoftonline.com" in issuer or "b2clogin.com" in issuer or "sts.windows.net" in issuer:
                        logger.debug(f"Token identified as Azure AD/Entra ID token (issuer: {issuer})")
                        return True
                    # Even if issuer check fails, RS256 means it's Azure AD
                    logger.debug(f"Token identified as Azure AD/Entra ID token (RS256 algorithm)")
                    return True
                except:
                    # If we can't decode payload, but it's RS256, assume Azure AD
                    logger.debug(f"Token identified as Azure AD/Entra ID token (RS256 algorithm, couldn't decode payload)")
                    return True
            
            # If it's HS256, it's likely an internal JWT token
            if alg == "HS256":
                logger.debug("Token identified as internal JWT token (HS256 algorithm)")
                return False
                
        except Exception as e:
            logger.debug(f"Error checking if token is Azure AD B2C/Entra ID: {e}")
        return False

    async def validate_token(self, token: str) -> TokenValidationResult:
        """Validate a token (either Azure AD B2C/Entra ID or internal JWT)."""
        # Check if Azure AD client is configured
        if not self.azure_ad_client:
            logger.debug("Azure AD B2C / Entra ID client not configured, trying internal JWT only")
        else:
            logger.debug("Azure AD B2C / Entra ID client is configured")
        
        # Check if token looks like Azure AD B2C/Entra ID token
        is_azure_token = self._is_azure_ad_b2c_token(token)
        logger.debug(f"Token appears to be Azure AD B2C/Entra ID token: {is_azure_token}")
        
        # Try Azure AD B2C / Entra ID first if configured and token looks like Azure token
        if self.azure_ad_client and is_azure_token:
            try:
                logger.info("Attempting to validate token as Azure AD B2C / Entra ID token")
                user_info = await self.azure_ad_client.get_user_info(token)
                logger.info(f"Azure AD B2C / Entra ID token validated successfully for user: {user_info.oid}")
                return TokenValidationResult(
                    user_id=user_info.oid or "",
                    email=user_info.email or "",
                    token_type="azure_ad_b2c",
                    user_info=user_info,
                    claims=user_info.claims,
                )
            except AuthenticationError as e:
                # If Azure AD B2C validation fails and it's a configuration error, don't try internal JWT
                error_msg = str(e).lower()
                if "not configured" in error_msg:
                    logger.error(
                        f"Azure AD B2C / Entra ID is not configured. "
                        f"Check environment variables: AZURE_AD_B2C_TENANT_ID, AZURE_AD_B2C_CLIENT_ID. "
                        f"Error: {e}"
                    )
                    raise AuthenticationError(
                        "Azure AD / Entra ID is not configured. Please check backend configuration."
                    ) from e
                # For other authentication errors, try internal JWT
                logger.warning(f"Azure AD B2C / Entra ID validation failed: {e}, trying internal JWT", exc_info=True)
            except Exception as e:
                error_msg = str(e).lower()
                if "not configured" in error_msg:
                    logger.error(
                        f"Azure AD B2C / Entra ID is not configured. "
                        f"Check environment variables: AZURE_AD_B2C_TENANT_ID, AZURE_AD_B2C_CLIENT_ID. "
                        f"Error: {e}"
                    )
                    raise AuthenticationError(
                        "Azure AD / Entra ID is not configured. Please check backend configuration."
                    ) from e
                logger.warning(f"Error validating Azure AD B2C / Entra ID token: {e}, trying internal JWT", exc_info=True)

        # Try internal JWT token (only if it's not an Azure AD token)
        # Don't try internal JWT if we already identified it as Azure AD token
        if not is_azure_token:
            try:
                logger.debug("Attempting to validate token as internal JWT token")
                payload = self.jwt_handler.decode_token(token)
                logger.debug(f"Internal JWT token validated successfully for user: {payload.user_id}")
                return TokenValidationResult(
                    user_id=payload.user_id,
                    email=payload.email,
                    token_type="internal_jwt",
                    payload=payload,
                    claims=payload.to_dict(),
                )
            except AuthenticationError as e:
                logger.warning(f"Internal JWT validation failed: {e}")
                raise AuthenticationError("Invalid token: Could not validate as Azure AD B2C or internal JWT token")
            except Exception as e:
                logger.error(f"Error validating internal JWT token: {e}", exc_info=True)
                raise AuthenticationError("Token validation failed")
        else:
            # If we identified it as Azure AD token but validation failed, don't try internal JWT
            # This prevents the "alg value is not allowed" error
            logger.error(
                "Token was identified as Azure AD/Entra ID token but validation failed. "
                "Check Azure AD configuration and token audience/issuer."
            )
            raise AuthenticationError(
                "Invalid token: Azure AD/Entra ID token validation failed. "
                "Check backend Azure AD configuration (tenant_id, client_id, instance)."
            )

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
