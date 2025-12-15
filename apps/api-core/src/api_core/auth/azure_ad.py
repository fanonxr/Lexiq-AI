"""Azure AD B2C integration for token validation and user management."""

import base64
import json
import logging
import time
from typing import Any, Dict, Optional

import httpx
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import JWTError, jwt

from api_core.config import get_settings
from api_core.exceptions import AuthenticationError

logger = logging.getLogger(__name__)
settings = get_settings()


class UserInfo:
    """User information extracted from Azure AD B2C token."""

    def __init__(self, claims: Dict[str, any]):
        """Initialize from JWT claims."""
        self.oid = claims.get("oid")  # Object ID (unique user identifier)
        self.email = claims.get("email") or claims.get("emails", [None])[0]
        self.name = claims.get("name") or claims.get("given_name", "")
        self.family_name = claims.get("family_name", "")
        self.display_name = claims.get("name") or f"{self.name} {self.family_name}".strip()
        self.tenant_id = claims.get("tid")  # Tenant ID
        self.issuer = claims.get("iss")  # Token issuer
        self.audience = claims.get("aud")  # Token audience
        self.exp = claims.get("exp")  # Expiration time
        self.iat = claims.get("iat")  # Issued at time
        self.claims = claims  # All claims

    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary."""
        return {
            "id": self.oid,
            "email": self.email,
            "name": self.display_name,
            "given_name": self.name,
            "family_name": self.family_name,
        }


class AzureADB2CClient:
    """Client for Azure AD B2C token validation and user management."""

    def __init__(self):
        """Initialize Azure AD B2C client."""
        self.config = settings.azure_ad_b2c
        self.jwks_cache: Optional[Dict] = None
        self.jwks_cache_expiry: Optional[float] = None

    @property
    def jwks_url(self) -> Optional[str]:
        """Get the JWKS (JSON Web Key Set) URL for token validation."""
        if not self.config.is_configured:
            return None

        # Azure AD B2C JWKS URL format:
        # https://{tenant}.b2clogin.com/{tenant}/{policy}/discovery/v2.0/keys
        tenant = self.config.tenant_id
        policy = self.config.policy_signup_signin
        instance = self.config.instance.format(tenant=tenant)

        return f"{instance}/{tenant}/{policy}/discovery/v2.0/keys"

    async def get_jwks(self) -> Dict:
        """Get JSON Web Key Set from Azure AD B2C."""
        if not self.jwks_url:
            raise AuthenticationError("Azure AD B2C is not configured")

        # Use cached JWKS if available and not expired
        if (
            self.jwks_cache is not None
            and self.jwks_cache_expiry is not None
            and time.time() < self.jwks_cache_expiry
        ):
            return self.jwks_cache

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.jwks_url, timeout=10.0)
                response.raise_for_status()
                jwks = response.json()

                # Cache JWKS for 1 hour
                self.jwks_cache = jwks
                self.jwks_cache_expiry = time.time() + 3600

                logger.debug(f"Fetched JWKS from {self.jwks_url}")
                return jwks
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch JWKS from Azure AD B2C: {e}")
            raise AuthenticationError("Failed to validate token: Unable to fetch signing keys")

    def get_signing_key(self, token: str, jwks: Dict) -> Optional[rsa.RSAPublicKey]:
        """Get the signing key for a token from JWKS."""
        try:
            # Decode token header without verification
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")

            if not kid:
                logger.warning("Token missing 'kid' in header")
                return None

            # Find the key in JWKS
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    try:
                        # Convert JWK to RSA public key
                        # JWK format: n and e are base64url-encoded strings
                        n_str = key["n"]
                        e_str = key["e"]

                        # Decode base64url-encoded values
                        # base64url uses - and _ instead of + and /
                        def base64url_decode_str(s: str) -> bytes:
                            # Add padding if needed
                            padding = 4 - len(s) % 4
                            if padding != 4:
                                s += "=" * padding
                            # Replace URL-safe characters
                            s = s.replace("-", "+").replace("_", "/")
                            return base64.b64decode(s)

                        n_bytes = base64url_decode_str(n_str)
                        e_bytes = base64url_decode_str(e_str)

                        # Convert bytes to integers (big-endian)
                        n_int = int.from_bytes(n_bytes, byteorder="big")
                        e_int = int.from_bytes(e_bytes, byteorder="big")

                        # Create RSA public key from numbers
                        public_numbers = rsa.RSAPublicNumbers(e_int, n_int)
                        public_key = public_numbers.public_key()

                        return public_key
                    except Exception as key_error:
                        logger.error(f"Error converting JWK to RSA key: {key_error}")
                        continue

            logger.warning(f"Signing key with kid '{kid}' not found in JWKS")
            return None
        except Exception as e:
            logger.error(f"Error extracting signing key: {e}")
            return None

    async def validate_token(self, token: str) -> Dict[str, any]:
        """Validate an Azure AD B2C JWT token and return claims."""
        if not self.config.is_configured:
            raise AuthenticationError("Azure AD B2C is not configured")

        try:
            # Get JWKS
            jwks = await self.get_jwks()

            # Get signing key
            public_key = self.get_signing_key(token, jwks)
            if not public_key:
                raise AuthenticationError("Unable to find signing key for token")

            # Get expected audience and issuer
            expected_audience = self.config.client_id
            expected_issuer = self.config.authority

            # Verify and decode token
            algorithms = ["RS256"]  # Azure AD B2C uses RS256
            options = {
                "verify_signature": True,
                "verify_aud": True,
                "verify_exp": True,
                "verify_iss": True,
            }

            claims = jwt.decode(
                token,
                public_key,
                algorithms=algorithms,
                audience=expected_audience,
                issuer=expected_issuer,
                options=options,
            )

            logger.debug(f"Token validated successfully for user: {claims.get('oid')}")
            return claims

        except JWTError as e:
            logger.warning(f"Token validation failed: {e}")
            raise AuthenticationError(f"Invalid token: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during token validation: {e}")
            raise AuthenticationError(f"Token validation failed: {str(e)}")

    async def get_user_info(self, token: str) -> UserInfo:
        """Get user information from a validated token."""
        claims = await self.validate_token(token)
        return UserInfo(claims)

    async def validate_and_get_user(self, token: str) -> UserInfo:
        """Validate token and return user info (convenience method)."""
        return await self.get_user_info(token)


# Global client instance
_client: Optional[AzureADB2CClient] = None


def get_azure_ad_client() -> AzureADB2CClient:
    """Get the global Azure AD B2C client instance."""
    global _client
    if _client is None:
        _client = AzureADB2CClient()
    return _client


async def validate_azure_token(token: str) -> Dict[str, any]:
    """Validate an Azure AD B2C token and return claims."""
    client = get_azure_ad_client()
    return await client.validate_token(token)


async def get_user_info(token: str) -> UserInfo:
    """Get user information from an Azure AD B2C token."""
    client = get_azure_ad_client()
    return await client.get_user_info(token)
