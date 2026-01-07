"""Google OAuth integration for token validation and user management."""

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


class GoogleUserInfo:
    """User information extracted from Google ID token."""

    def __init__(self, claims: Dict[str, Any]):
        """Initialize from JWT claims."""
        self.sub = claims.get("sub")  # Subject (Google user ID - unique identifier)
        self.email = claims.get("email")
        self.email_verified = claims.get("email_verified", False)
        self.name = claims.get("name", "")
        self.given_name = claims.get("given_name", "")
        self.family_name = claims.get("family_name", "")
        self.picture = claims.get("picture")
        self.issuer = claims.get("iss")  # Token issuer (should be https://accounts.google.com)
        self.audience = claims.get("aud")  # Token audience (should be our client ID)
        self.exp = claims.get("exp")  # Expiration time
        self.iat = claims.get("iat")  # Issued at time
        self.claims = claims  # All claims

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.sub,
            "email": self.email,
            "name": self.name,
            "given_name": self.given_name,
            "family_name": self.family_name,
            "picture": self.picture,
        }


class GoogleOAuthClient:
    """Client for Google OAuth token validation and user management."""

    def __init__(self):
        """Initialize Google OAuth client."""
        self.config = settings.google
        self.jwks_cache: Optional[Dict] = None
        self.jwks_cache_expiry: Optional[float] = None
        self.jwks_url = "https://www.googleapis.com/oauth2/v3/certs"

    @property
    def is_configured(self) -> bool:
        """Check if Google OAuth is configured."""
        return self.config.is_configured

    async def get_jwks(self) -> Dict:
        """Get JSON Web Key Set from Google."""
        if not self.is_configured:
            raise AuthenticationError("Google OAuth is not configured")

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
            logger.error(f"Failed to fetch JWKS from Google: {e}")
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

    async def validate_token(self, token: str, access_token: Optional[str] = None) -> Dict[str, Any]:
        """Validate a Google ID token and return claims.
        
        Args:
            token: The ID token to validate
            access_token: Optional access token to validate at_hash claim
        """
        if not self.is_configured:
            raise AuthenticationError("Google OAuth is not configured")

        try:
            # Get JWKS
            jwks = await self.get_jwks()

            # Get signing key
            public_key = self.get_signing_key(token, jwks)
            if not public_key:
                raise AuthenticationError("Unable to find signing key for token")

            # Expected issuer and audience
            expected_issuer = "https://accounts.google.com"
            expected_audience = self.config.client_id

            # Verify and decode token
            algorithms = ["RS256"]  # Google uses RS256

            options = {
                "verify_signature": True,
                "verify_aud": True,
                "verify_exp": True,
                "verify_iss": True,
            }

            # Decode token with access_token if provided (enables at_hash validation)
            try:
                if access_token:
                    # Pass access_token to enable at_hash validation
                    claims = jwt.decode(
                        token,
                        public_key,
                        algorithms=algorithms,
                        audience=expected_audience,
                        issuer=expected_issuer,
                        options=options,
                        access_token=access_token,
                    )
                else:
                    # No access_token provided, decode without at_hash validation
                    claims = jwt.decode(
                        token,
                        public_key,
                        algorithms=algorithms,
                        audience=expected_audience,
                        issuer=expected_issuer,
                        options=options,
                    )
            except JWTError as e:
                # If at_hash validation fails and we have access_token, that's an error
                # If we don't have access_token, fall back to manual validation
                error_msg = str(e).lower()
                if "at_hash" in error_msg:
                    if access_token:
                        # We have access_token but validation failed - this is an error
                        logger.warning(f"at_hash validation failed even with access_token: {e}")
                        raise AuthenticationError(f"Token validation failed: at_hash mismatch") from e
                    else:
                        # No access_token provided, decode without at_hash validation
                        logger.debug(
                            "Token contains at_hash claim but no access token provided. "
                            "Decoding without at_hash validation."
                        )
                        # Decode token with signature verification but skip at_hash
                        # We'll verify signature, then manually verify audience/issuer/expiration
                        from jose import jwt as jose_jwt
                        import time
                        
                        # Get unverified claims first
                        unverified_claims = jose_jwt.get_unverified_claims(token)
                        
                        # Verify signature (this is the most important check)
                        jose_jwt.decode(
                            token,
                            public_key,
                            algorithms=algorithms,
                            options={
                                "verify_signature": True,
                                "verify_aud": False,  # Verify manually below
                                "verify_exp": False,  # Verify manually below
                                "verify_iss": False,  # Verify manually below
                            },
                        )
                        
                        # Manually verify audience
                        if unverified_claims.get("aud") != expected_audience:
                            raise AuthenticationError(
                                f"Invalid audience: expected {expected_audience}, got {unverified_claims.get('aud')}"
                            )
                        
                        # Manually verify issuer
                        if unverified_claims.get("iss") != expected_issuer:
                            raise AuthenticationError(
                                f"Invalid issuer: expected {expected_issuer}, got {unverified_claims.get('iss')}"
                            )
                        
                        # Manually verify expiration
                        exp = unverified_claims.get("exp")
                        if exp:
                            current_time = time.time()
                            if exp < current_time:
                                raise AuthenticationError(f"Token has expired (exp: {exp}, now: {current_time})")
                        
                        # Use the claims (signature is verified, audience/issuer/exp are verified)
                        claims = unverified_claims
                else:
                    raise

            logger.debug(f"Token validated successfully for user: {claims.get('sub')}")
            return claims

        except JWTError as e:
            logger.warning(f"Token validation failed (JWTError): {e}", exc_info=True)
            # Log more details about the error
            try:
                from jose import jwt as jose_jwt
                unverified_claims = jose_jwt.get_unverified_claims(token)
                logger.warning(
                    f"Token claims (unverified): aud={unverified_claims.get('aud')}, "
                    f"iss={unverified_claims.get('iss')}, exp={unverified_claims.get('exp')}"
                )
            except:
                pass
            raise AuthenticationError(f"Invalid token: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during token validation: {e}", exc_info=True)
            raise AuthenticationError(f"Token validation failed: {str(e)}")

    async def get_user_info(self, token: str, access_token: Optional[str] = None) -> GoogleUserInfo:
        """Get user information from a validated token.
        
        Args:
            token: The ID token to validate
            access_token: Optional access token to validate at_hash claim
        """
        claims = await self.validate_token(token, access_token=access_token)
        return GoogleUserInfo(claims)

    async def validate_and_get_user(self, token: str) -> GoogleUserInfo:
        """Validate token and return user info (convenience method)."""
        return await self.get_user_info(token)


# Global client instance
_client: Optional[GoogleOAuthClient] = None


def get_google_oauth_client() -> GoogleOAuthClient:
    """Get the global Google OAuth client instance."""
    global _client
    if _client is None:
        _client = GoogleOAuthClient()
    return _client


async def validate_google_token(token: str) -> Dict[str, Any]:
    """Validate a Google ID token and return claims."""
    client = get_google_oauth_client()
    return await client.validate_token(token)


async def get_google_user_info(token: str) -> GoogleUserInfo:
    """Get user information from a Google ID token."""
    client = get_google_oauth_client()
    return await client.get_user_info(token)

