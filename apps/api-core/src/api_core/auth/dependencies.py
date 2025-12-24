"""FastAPI dependencies for authentication and authorization."""

import logging
from typing import List, Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.requests import Request

from api_core.auth.token_validator import TokenValidationResult, get_token_validator
from api_core.database.session import get_session_context
from api_core.exceptions import AuthenticationError, AuthorizationError
from api_core.services.user_service import get_user_service

logger = logging.getLogger(__name__)

# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)


async def get_token_from_header(
    authorization: Optional[str] = Header(None),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[str]:
    """Extract token from Authorization header."""
    # Debug logging
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Token extraction - has_credentials: {credentials is not None}, has_authorization_header: {authorization is not None}")
    
    # Try HTTPBearer first (standard Bearer token)
    if credentials:
        token = credentials.credentials
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Token extracted from HTTPBearer: {token[:20] + '...' if token and len(token) > 20 else token}")
        return token

    # Fallback: try manual header parsing
    if authorization:
        # Handle "Bearer <token>" format
        if authorization.startswith("Bearer "):
            token = authorization[7:].strip()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Token extracted from Bearer header: {token[:20] + '...' if token and len(token) > 20 else token}")
            return token
        # Handle plain token
        token = authorization.strip()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Token extracted from plain header: {token[:20] + '...' if token and len(token) > 20 else token}")
        return token

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("No token found in headers")
    return None


async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(get_token_from_header),
) -> TokenValidationResult:
    """
    FastAPI dependency to get the current authenticated user.

    Validates the token (either Azure AD B2C/Entra ID or internal JWT) and returns
    the user information. For Azure AD users, automatically syncs the user to the
    database if they don't exist yet.

    Raises:
        HTTPException: 401 if token is missing or invalid
    """
    if not token:
        # Log all headers for debugging (but don't log sensitive data)
        headers_dict = dict(request.headers)
        # Remove potentially sensitive headers
        safe_headers = {k: v for k, v in headers_dict.items() if k.lower() not in ['authorization', 'cookie', 'x-api-key']}
        logger.warning(
            f"get_current_user called but no token provided. "
            f"Request: {request.method} {request.url.path}. "
            f"Headers present: {list(safe_headers.keys())}"
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated: No token provided. Please ensure you are logged in and the Authorization header is included in your request.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        logger.debug(f"Validating token (length: {len(token)}, preview: {token[:20]}...)")
        validator = get_token_validator()
        result = await validator.validate_token(token)
        logger.debug(f"Token validated successfully for user: {result.user_id} ({result.email})")
        
        # Auto-sync Azure AD users to database
        if result.token_type == "azure_ad_b2c" and result.user_info:
            try:
                async with get_session_context() as session:
                    user_service = get_user_service(session)
                    
                    # Check if user exists in database by Azure AD object ID
                    azure_ad_object_id = result.user_info.oid
                    if azure_ad_object_id:
                        existing_user = await user_service.repository.get_by_azure_ad_object_id(
                            azure_ad_object_id
                        )
                        
                        if not existing_user:
                            # User doesn't exist in database, sync them
                            logger.info(
                                f"Auto-syncing Azure AD user to database: {result.email} "
                                f"(object_id: {azure_ad_object_id})"
                            )
                            
                            # Extract user info from token
                            email = result.user_info.email or result.email
                            name = result.user_info.display_name or result.user_info.name or email.split("@")[0]
                            tenant_id = result.user_info.tenant_id
                            
                            # Sync user from Azure AD
                            user_profile = await user_service.sync_user_from_azure_ad(
                                azure_ad_object_id=azure_ad_object_id,
                                email=email,
                                name=name,
                                azure_ad_tenant_id=tenant_id,
                            )
                            
                            # Update result to use database user ID instead of Azure AD object ID
                            # This ensures subsequent lookups work correctly
                            result.user_id = user_profile.id
                            logger.info(
                                f"Successfully synced Azure AD user to database: "
                                f"{user_profile.id} (was: {azure_ad_object_id})"
                            )
                        else:
                            # User exists, update result to use database user ID
                            result.user_id = existing_user.id
                            logger.debug(
                                f"Azure AD user already exists in database: {existing_user.id}"
                            )
            except Exception as sync_error:
                # Log the error but don't fail authentication
                # The user is still authenticated, just not synced to DB
                logger.error(
                    f"Failed to auto-sync Azure AD user to database: {sync_error}",
                    exc_info=True,
                )
                logger.error(
                    f"Auto-sync error details - user_id: {result.user_id}, "
                    f"email: {result.email}, azure_ad_object_id: {result.user_info.oid if result.user_info else 'N/A'}"
                )
                # Continue with Azure AD object ID as user_id
                # The user will be synced on next request or can be manually synced
                # The /users/me endpoint has a fallback to handle this case
        
        return result
    except AuthenticationError as e:
        logger.warning(f"Authentication failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Unexpected error during authentication: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: TokenValidationResult = Depends(get_current_user),
) -> TokenValidationResult:
    """
    FastAPI dependency to get the current active user.

    Ensures the user is active (not disabled/suspended).
    This is a placeholder - actual implementation will check user status
    from the database once user models are created.

    Raises:
        HTTPException: 403 if user is not active
    """
    # TODO: Check user status from database
    # For now, we assume all authenticated users are active
    # This will be implemented when user models are created in Phase 4

    # Example future implementation:
    # async with get_session() as session:
    #     user = await get_user_by_id(session, current_user.user_id)
    #     if not user or not user.is_active:
    #         raise HTTPException(
    #             status_code=status.HTTP_403_FORBIDDEN,
    #             detail="User account is not active"
    #         )

    return current_user


def require_permissions(required_permissions: List[str]):
    """
    FastAPI dependency factory for role-based access control.

    Creates a dependency that checks if the current user has the required permissions.

    Args:
        required_permissions: List of permission strings required to access the endpoint

    Returns:
        FastAPI dependency function

    Example:
        @app.get("/admin/users")
        async def get_users(
            user: TokenValidationResult = Depends(require_permissions(["admin:read"]))
        ):
            ...
    """

    async def permission_checker(
        current_user: TokenValidationResult = Depends(get_current_active_user),
    ) -> TokenValidationResult:
        """
        Check if user has required permissions.

        This is a placeholder - actual implementation will check permissions
        from the database once user models and permission system are created.

        Raises:
            HTTPException: 403 if user doesn't have required permissions
        """
        # TODO: Check permissions from database
        # For now, we'll check claims/roles from token
        # This will be implemented when user models are created in Phase 4

        # Example future implementation:
        # async with get_session() as session:
        #     user_permissions = await get_user_permissions(session, current_user.user_id)
        #     has_permission = all(
        #         perm in user_permissions for perm in required_permissions
        #     )
        #     if not has_permission:
        #         raise HTTPException(
        #             status_code=status.HTTP_403_FORBIDDEN,
        #             detail=f"Missing required permissions: {required_permissions}"
        #         )

        # Temporary: Check for permissions in token claims
        user_permissions = current_user.claims.get("permissions", [])
        user_roles = current_user.claims.get("roles", [])

        # Check if user has any of the required permissions
        has_permission = any(
            perm in user_permissions for perm in required_permissions
        ) or any(
            role in required_permissions for role in user_roles
        )

        if not has_permission:
            logger.warning(
                f"User {current_user.user_id} attempted to access resource requiring "
                f"permissions {required_permissions}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permissions: {required_permissions}",
            )

        return current_user

    return permission_checker


def require_roles(required_roles: List[str]):
    """
    FastAPI dependency factory for role-based access control.

    Creates a dependency that checks if the current user has the required roles.

    Args:
        required_roles: List of role strings required to access the endpoint

    Returns:
        FastAPI dependency function

    Example:
        @app.get("/admin/dashboard")
        async def get_admin_dashboard(
            user: TokenValidationResult = Depends(require_roles(["admin"]))
        ):
            ...
    """

    async def role_checker(
        current_user: TokenValidationResult = Depends(get_current_active_user),
    ) -> TokenValidationResult:
        """
        Check if user has required roles.

        This is a placeholder - actual implementation will check roles
        from the database once user models are created.

        Raises:
            HTTPException: 403 if user doesn't have required roles
        """
        # TODO: Check roles from database
        # For now, we'll check roles from token claims
        # This will be implemented when user models are created in Phase 4

        user_roles = current_user.claims.get("roles", [])
        has_role = any(role in user_roles for role in required_roles)

        if not has_role:
            logger.warning(
                f"User {current_user.user_id} attempted to access resource requiring "
                f"roles {required_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required roles: {required_roles}",
            )

        return current_user

    return role_checker


# Optional: Dependency for optional authentication (doesn't raise error if no token)
async def get_optional_user(
    token: Optional[str] = Depends(get_token_from_header),
) -> Optional[TokenValidationResult]:
    """
    FastAPI dependency to optionally get the current user.

    Returns None if no token is provided, instead of raising an error.
    Useful for endpoints that work both with and without authentication.

    Example:
        @app.get("/public/content")
        async def get_content(
            user: Optional[TokenValidationResult] = Depends(get_optional_user)
        ):
            if user:
                # Return personalized content
                ...
            else:
                # Return public content
                ...
    """
    if not token:
        return None

    try:
        validator = get_token_validator()
        result = await validator.validate_token(token)
        return result
    except (AuthenticationError, HTTPException):
        # Return None instead of raising error
        return None
    except Exception as e:
        logger.debug(f"Optional authentication failed: {e}")
        return None


async def get_user_or_internal_auth(
    token: Optional[str] = Depends(get_token_from_header),
    x_internal_api_key: Optional[str] = Header(default=None, alias="X-Internal-API-Key"),
) -> Optional[TokenValidationResult]:
    """
    FastAPI dependency that supports both user authentication and internal API key.
    
    Returns:
        - TokenValidationResult if user is authenticated
        - None if valid internal API key is provided (service-to-service call)
        - Raises HTTPException if neither is valid
    
    This allows endpoints to support both:
    - User authentication (Bearer token)
    - Internal service-to-service calls (X-Internal-API-Key header)
    """
    from api_core.config import get_settings
    
    settings = get_settings()
    
    # Check internal API key first
    is_internal = False
    if settings.internal_api_key_enabled and settings.internal_api_key:
        is_internal = x_internal_api_key == settings.internal_api_key
    
    if is_internal:
        # Internal service call - return None to indicate skip user authorization
        return None
    
    # Otherwise, require user authentication
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Provide either a Bearer token or X-Internal-API-Key header.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        validator = get_token_validator()
        result = await validator.validate_token(token)
        
        # Auto-sync Azure AD users to database (same logic as get_current_user)
        if result.token_type == "azure_ad_b2c" and result.user_info:
            try:
                async with get_session_context() as session:
                    user_service = get_user_service(session)
                    
                    azure_ad_object_id = result.user_info.oid
                    if azure_ad_object_id:
                        existing_user = await user_service.repository.get_by_azure_ad_object_id(
                            azure_ad_object_id
                        )
                        
                        if not existing_user:
                            logger.info(
                                f"Auto-syncing Azure AD user to database: {result.email} "
                                f"(object_id: {azure_ad_object_id})"
                            )
                            
                            email = result.user_info.email or result.email
                            name = result.user_info.display_name or result.user_info.name or email.split("@")[0]
                            tenant_id = result.user_info.tenant_id
                            
                            user_profile = await user_service.sync_user_from_azure_ad(
                                azure_ad_object_id=azure_ad_object_id,
                                email=email,
                                name=name,
                                azure_ad_tenant_id=tenant_id,
                            )
                            
                            result.user_id = user_profile.id
                            logger.info(
                                f"Successfully synced Azure AD user to database: "
                                f"{user_profile.id} (was: {azure_ad_object_id})"
                            )
                        else:
                            result.user_id = existing_user.id
                            logger.debug(
                                f"Azure AD user already exists in database: {existing_user.id}"
                            )
            except Exception as sync_error:
                logger.error(
                    f"Failed to auto-sync Azure AD user to database: {sync_error}",
                    exc_info=True,
                )
        
        return result
    except AuthenticationError as e:
        logger.warning(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Unexpected error during authentication: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )
