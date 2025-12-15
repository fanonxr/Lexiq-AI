"""Authentication endpoints."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from api_core.auth.dependencies import get_current_user
from api_core.auth.jwt import create_access_token, create_refresh_token, refresh_access_token
from api_core.auth.token_validator import TokenValidationResult
from api_core.config import get_settings
from api_core.exceptions import AuthenticationError, ValidationError
from api_core.models.auth import (
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    LogoutResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    SignupRequest,
    SignupResponse,
    UserProfile,
    VerifyEmailRequest,
    VerifyEmailResponse,
)
from api_core.database.session import get_session_context
from api_core.services.auth_service import get_auth_service

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post(
    "/login",
    response_model=LoginResponse,
    response_model_by_alias=True,  # Use camelCase aliases in JSON response
    status_code=status.HTTP_200_OK,
)
async def login(request: LoginRequest):
    """
    Login with email and password.

    Authenticates a user with email and password, returning an access token
    and refresh token if successful.

    **Note:** This endpoint is currently a placeholder. Full implementation
    will be available in Phase 4 when user repository is created.
    """
    try:
        async with get_session_context() as session:
            auth_service = get_auth_service(session)
            user = await auth_service.authenticate_user(request.email, request.password)

        # Generate tokens
        access_token = create_access_token(
            user_id=user.id,
            email=user.email,
        )
        refresh_token = create_refresh_token(
            user_id=user.id,
            email=user.email,
        )

        # Calculate expiration
        expires_in = settings.jwt.access_token_expire_minutes * 60

        return LoginResponse(
            token=access_token,
            refresh_token=refresh_token,
            user=user,
            expires_in=expires_in,
        )
    except AuthenticationError as e:
        logger.warning(f"Login failed for email {request.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error during login: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login",
        )


@router.post(
    "/signup",
    response_model=SignupResponse,
    response_model_by_alias=True,  # Use camelCase aliases in JSON response
    status_code=status.HTTP_201_CREATED,
)
async def signup(request: SignupRequest):
    """
    Register a new user account.

    Creates a new user account with email and password, returning an access token
    and refresh token if successful.

    **Note:** This endpoint is currently a placeholder. Full implementation
    will be available in Phase 4 when user repository is created.
    """
    try:
        async with get_session_context() as session:
            auth_service = get_auth_service(session)
            user = await auth_service.create_user(
                name=request.name,
                email=request.email,
                password=request.password,
            )

        # Generate tokens
        access_token = create_access_token(
            user_id=user.id,
            email=user.email,
        )
        refresh_token = create_refresh_token(
            user_id=user.id,
            email=user.email,
        )

        # Calculate expiration
        expires_in = settings.jwt.access_token_expire_minutes * 60

        return SignupResponse(
            token=access_token,
            refresh_token=refresh_token,
            user=user,
            expires_in=expires_in,
        )
    except ValidationError as e:
        logger.warning(f"Signup failed for email {request.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error during signup: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during registration",
        )


@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse,
    status_code=status.HTTP_200_OK,
)
async def reset_password(request: ResetPasswordRequest):
    """
    Request a password reset.

    Sends a password reset email to the user if the email exists.

    **Note:** This endpoint is currently a placeholder. Full implementation
    will be available in Phase 4 when user repository and email service are created.
    """
    try:
        auth_service = get_auth_service()
        await auth_service.request_password_reset(request.email)

        # Always return success message (don't reveal if email exists)
        return ResetPasswordResponse(
            message="If an account with that email exists, a password reset link has been sent."
        )
    except Exception as e:
        logger.error(f"Error requesting password reset: {e}", exc_info=True)
        # Still return success to avoid email enumeration
        return ResetPasswordResponse(
            message="If an account with that email exists, a password reset link has been sent."
        )


@router.post(
    "/verify-email",
    response_model=VerifyEmailResponse,
    status_code=status.HTTP_200_OK,
)
async def verify_email(request: VerifyEmailRequest):
    """
    Verify email address.

    Verifies a user's email address using a verification token.

    **Note:** This endpoint is currently a placeholder. Full implementation
    will be available in Phase 4 when user repository is created.
    """
    try:
        auth_service = get_auth_service()
        await auth_service.verify_email_token(request.token)

        return VerifyEmailResponse(message="Email verified successfully")
    except ValidationError as e:
        logger.warning(f"Email verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error verifying email: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during email verification",
        )


@router.get("/me", response_model=UserProfile, status_code=status.HTTP_200_OK)
async def get_current_user_profile(
    current_user: TokenValidationResult = Depends(get_current_user),
):
    """
    Get current user profile.

    Returns the profile of the currently authenticated user.
    Works with both Azure AD B2C tokens and internal JWT tokens.

    **Note:** This endpoint is currently a placeholder. Full implementation
    will be available in Phase 4 when user repository is created.
    """
    try:
        async with get_session_context() as session:
            auth_service = get_auth_service(session)

            # Try to get user from database
            user = await auth_service.get_user_by_id(current_user.user_id)

            if user:
                return user

        # If user not in database, create profile from token
        # This handles Azure AD B2C users who haven't been synced yet
        return UserProfile(
            id=current_user.user_id,
            email=current_user.email,
            name=current_user.claims.get("name", current_user.email.split("@")[0]),
            is_active=True,
            is_verified=True,  # Azure AD B2C users are pre-verified
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.error(f"Error getting user profile: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching user profile",
        )


@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    response_model_by_alias=True,  # Use camelCase aliases in JSON response
    status_code=status.HTTP_200_OK,
)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh access token.

    Generates a new access token from a valid refresh token.
    """
    try:
        new_access_token = refresh_access_token(request.refresh_token)

        # Calculate expiration
        expires_in = settings.jwt.access_token_expire_minutes * 60

        return RefreshTokenResponse(
            token=new_access_token,
            expires_in=expires_in,
        )
    except AuthenticationError as e:
        logger.warning(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error during token refresh: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during token refresh",
        )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
)
async def logout(
    current_user: TokenValidationResult = Depends(get_current_user),
):
    """
    Logout current user.

    Invalidates the current session. In a stateless JWT system, logout is
    typically handled client-side by removing the token. This endpoint
    can be used for logging purposes or future token blacklisting.

    **Note:** Token blacklisting will be implemented in Phase 4 when
    Redis token blacklist is available.
    """
    # TODO: Implement token blacklisting in Redis when available
    # For now, just log the logout event
    logger.info(f"User {current_user.user_id} logged out")

    return LogoutResponse(message="Logged out successfully")
