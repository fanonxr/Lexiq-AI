"""Authentication endpoints."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status

from api_core.auth.dependencies import get_current_user
from api_core.auth.jwt import create_access_token, create_refresh_token, refresh_access_token
from api_core.auth.token_validator import TokenValidationResult
from api_core.config import get_settings
from api_core.exceptions import AuthenticationError, RateLimitError, ValidationError
from api_core.services.rate_limit_service import get_rate_limit_service
from api_core.models.auth import (
    ConfirmPasswordResetRequest,
    ConfirmPasswordResetResponse,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    LogoutResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    ResendVerificationRequest,
    ResendVerificationResponse,
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
async def login(request: LoginRequest, http_request: Request):
    """
    Login with email and password.

    Authenticates a user with email and password, returning an access token
    and refresh token if successful.

    Rate limited to 5 attempts per 15 minutes per email address.
    """
    # Rate limiting: 5 attempts per 15 minutes per email
    rate_limit_service = get_rate_limit_service()
    rate_limit_key = f"login:{request.email.lower().strip()}"
    max_attempts = 5
    window_seconds = 15 * 60  # 15 minutes
    
    is_allowed, retry_after = await rate_limit_service.check_rate_limit(
        rate_limit_key, max_attempts, window_seconds
    )
    
    if not is_allowed:
        raise RateLimitError(
            message=f"Too many login attempts. Please try again in {retry_after} seconds.",
            retry_after=retry_after,
        )
    
    try:
        async with get_session_context() as session:
            auth_service = get_auth_service(session)
            user = await auth_service.authenticate_user(request.email, request.password)
            
            # Reset rate limit on successful login
            await rate_limit_service.reset_rate_limit(rate_limit_key)

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
        # Increment rate limit counter on failed login
        await rate_limit_service.increment_attempt(rate_limit_key, window_seconds)
        logger.warning(f"Login failed for email {request.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except RateLimitError as e:
        logger.warning(f"Rate limit exceeded for email {request.email}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
            headers={"Retry-After": str(e.retry_after) if e.retry_after else "900"},
        ) from e
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
    and refresh token if successful. Sends a verification email to the user.
    """
    try:
        async with get_session_context() as session:
            auth_service = get_auth_service(session)
            user = await auth_service.create_user(
                name=request.name,
                email=request.email,
                password=request.password,
            )
            
            # Get user from database to access firm_id
            db_user = await auth_service.repository.get_by_id(user.id)
            if db_user and db_user.firm_id:
                # Get frontend URL from environment or use default
                import os
                frontend_url = os.getenv("FRONTEND_URL", os.getenv("NEXT_PUBLIC_APP_URL", "http://localhost:3000"))
                
                # Send verification email
                try:
                    await auth_service.send_verification_email(
                        user_id=user.id,
                        email=user.email,
                        firm_id=db_user.firm_id,
                        frontend_url=frontend_url,
                    )
                except Exception as email_error:
                    # Log error but don't fail signup if email sending fails
                    logger.error(f"Failed to send verification email: {email_error}", exc_info=True)

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
    Always returns success to avoid email enumeration.
    """
    try:
        async with get_session_context() as session:
            auth_service = get_auth_service(session)
            
            # Get frontend URL from environment or use default
            import os
            frontend_url = os.getenv("FRONTEND_URL", os.getenv("NEXT_PUBLIC_APP_URL", "http://localhost:3000"))
            
            await auth_service.request_password_reset(request.email, frontend_url)

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
    "/reset-password/confirm",
    response_model=ConfirmPasswordResetResponse,
    status_code=status.HTTP_200_OK,
)
async def confirm_password_reset(request: ConfirmPasswordResetRequest):
    """
    Confirm password reset with token and new password.

    Validates the reset token and updates the user's password.
    """
    try:
        async with get_session_context() as session:
            auth_service = get_auth_service(session)
            await auth_service.confirm_password_reset(request.token, request.new_password)

        return ConfirmPasswordResetResponse(
            message="Password has been reset successfully. You can now sign in with your new password."
        )
    except ValidationError as e:
        logger.warning(f"Password reset confirmation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error confirming password reset: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during password reset",
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
    """
    try:
        async with get_session_context() as session:
            auth_service = get_auth_service(session)
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


@router.post(
    "/resend-verification",
    response_model=ResendVerificationResponse,
    status_code=status.HTTP_200_OK,
)
async def resend_verification(request: ResendVerificationRequest):
    """
    Resend email verification email.

    Sends a new verification email to the user if the email exists and is not verified.
    Always returns success to avoid email enumeration.
    """
    try:
        async with get_session_context() as session:
            auth_service = get_auth_service(session)
            user = await auth_service.repository.get_by_email(request.email)
            
            if user and not user.is_verified and user.firm_id:
                # Get frontend URL from environment or use default
                import os
                frontend_url = os.getenv("FRONTEND_URL", os.getenv("NEXT_PUBLIC_APP_URL", "http://localhost:3000"))
                
                # Send verification email
                await auth_service.send_verification_email(
                    user_id=user.id,
                    email=user.email,
                    firm_id=user.firm_id,
                    frontend_url=frontend_url,
                )
                logger.info(f"Verification email resent to {request.email}")
            else:
                # Log but don't reveal if email exists
                logger.debug(f"Resend verification requested for {request.email} (user not found or already verified)")
        
        # Always return success to avoid email enumeration
        return ResendVerificationResponse(
            message="If an account with that email exists and is not verified, a verification email has been sent."
        )
    except Exception as e:
        logger.error(f"Error resending verification email: {e}", exc_info=True)
        # Still return success to avoid email enumeration
        return ResendVerificationResponse(
            message="If an account with that email exists and is not verified, a verification email has been sent."
        )


@router.get("/me", response_model=UserProfile, status_code=status.HTTP_200_OK)
async def get_current_user_profile(
    current_user: TokenValidationResult = Depends(get_current_user),
):
    """
    Get current user profile.

    Returns the profile of the currently authenticated user.
    Works with all authentication types:
    - Microsoft (Azure AD B2C/Entra ID) tokens
    - Google OAuth tokens
    - Email/Password (internal JWT) tokens

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
        # This handles OAuth users (Azure AD B2C/Entra ID, Google) who haven't been synced yet
        # OAuth users are pre-verified (email verified by provider)
        is_verified = current_user.token_type in ("azure_ad_b2c", "google_oauth")
        
        return UserProfile(
            id=current_user.user_id,
            email=current_user.email,
            name=current_user.claims.get("name", current_user.email.split("@")[0]),
            is_active=True,
            is_verified=is_verified,  # OAuth users are pre-verified
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
