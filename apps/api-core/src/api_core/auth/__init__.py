"""Authentication utilities."""

from api_core.auth.azure_ad import (
    AzureADB2CClient,
    UserInfo,
    get_azure_ad_client,
    get_user_info,
    validate_azure_token,
)
from api_core.auth.jwt import (
    TokenPayload,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_jwt_handler,
    refresh_access_token,
    verify_token,
)
from api_core.auth.dependencies import (
    get_current_active_user,
    get_current_user,
    get_optional_user,
    get_token_from_header,
    require_permissions,
    require_roles,
)
from api_core.auth.token_validator import (
    TokenValidationResult,
    UnifiedTokenValidator,
    get_email_from_token,
    get_token_validator,
    get_user_id_from_token,
    validate_token,
)

__all__ = [
    # Azure AD B2C
    "AzureADB2CClient",
    "UserInfo",
    "get_azure_ad_client",
    "validate_azure_token",
    "get_user_info",
    # JWT
    "TokenPayload",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "get_jwt_handler",
    "refresh_access_token",
    "verify_token",
    # Unified Token Validator
    "TokenValidationResult",
    "UnifiedTokenValidator",
    "get_token_validator",
    "validate_token",
    "get_user_id_from_token",
    "get_email_from_token",
    # FastAPI Dependencies
    "get_token_from_header",
    "get_current_user",
    "get_current_active_user",
    "get_optional_user",
    "require_permissions",
    "require_roles",
]
