"""Internal service-to-service authentication dependencies."""

from typing import Optional

from fastapi import Depends, Header, HTTPException, status

from cognitive_orch.config import get_settings
from cognitive_orch.utils.logging import get_logger

logger = get_logger("internal_service_auth")
settings = get_settings()


async def require_internal_api_key(
    x_internal_api_key: Optional[str] = Header(default=None, alias="X-Internal-API-Key"),
) -> None:
    """
    Require a valid internal API key for service-to-service calls.

    Behavior:
    - If INTERNAL_API_KEY_ENABLED is false: allow (dev-friendly).
    - If enabled: require X-Internal-API-Key to match INTERNAL_API_KEY.
    """
    if not settings.internal_api_key_enabled:
        return

    if not settings.internal_api_key:
        # Misconfiguration; in prod validate_production_settings will fail fast, but guard anyway.
        logger.error("INTERNAL_API_KEY_ENABLED=true but INTERNAL_API_KEY is not set")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal auth misconfigured",
        )

    if not x_internal_api_key or x_internal_api_key != settings.internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal API key",
            headers={"WWW-Authenticate": "X-Internal-API-Key"},
        )


async def check_internal_api_key(
    x_internal_api_key: Optional[str] = Header(default=None, alias="X-Internal-API-Key"),
) -> bool:
    """
    Check if a valid internal API key is provided (does not raise if missing).
    
    Returns True if a valid internal API key is provided, False otherwise.
    Used for endpoints that support both user auth and internal API key.
    """
    if not settings.internal_api_key_enabled:
        return False
    
    if not settings.internal_api_key:
        return False
    
    return x_internal_api_key == settings.internal_api_key


InternalAuthDep = Depends(require_internal_api_key)

