"""FastAPI dependencies for authentication and authorization."""

import logging
from typing import List, Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api_core.auth.token_validator import TokenValidationResult, get_token_validator
from api_core.exceptions import AuthenticationError, AuthorizationError

logger = logging.getLogger(__name__)

# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)


async def get_token_from_header(
    authorization: Optional[str] = Header(None),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[str]:
    """Extract token from Authorization header."""
    # Try HTTPBearer first (standard Bearer token)
    if credentials:
        return credentials.credentials

    # Fallback: try manual header parsing
    if authorization:
        # Handle "Bearer <token>" format
        if authorization.startswith("Bearer "):
            return authorization[7:].strip()
        # Handle plain token
        return authorization.strip()

    return None


async def get_current_user(
    token: Optional[str] = Depends(get_token_from_header),
) -> TokenValidationResult:
    """
    FastAPI dependency to get the current authenticated user.

    Validates the token (either Azure AD B2C or internal JWT) and returns
    the user information.

    Raises:
        HTTPException: 401 if token is missing or invalid
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        validator = get_token_validator()
        result = await validator.validate_token(token)
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
