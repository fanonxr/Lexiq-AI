"""Google OAuth authentication endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api_core.auth.dependencies import get_current_user, get_optional_user
from api_core.auth.google_oauth import get_google_oauth_client
from api_core.auth.jwt import create_access_token, create_refresh_token
from api_core.auth.token_validator import TokenValidationResult
from api_core.config import get_settings
from api_core.database.session import get_session_context
from api_core.exceptions import AuthenticationError, ValidationError
from api_core.models.auth import LoginResponse, UserProfile
from api_core.services.user_service import get_user_service

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/auth/google", tags=["authentication", "google"])


# Google OAuth scopes for user authentication
GOOGLE_AUTH_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]


class InitiateGoogleAuthRequest(BaseModel):
    """Request to initiate Google OAuth flow."""

    redirect_uri: str = Field(..., description="OAuth redirect URI")


class InitiateGoogleAuthResponse(BaseModel):
    """Response with Google OAuth authorization URL."""

    model_config = {"populate_by_name": True}

    authUrl: str = Field(..., description="Google OAuth authorization URL", alias="authUrl")


class GoogleCallbackRequest(BaseModel):
    """Google OAuth callback request."""

    code: str = Field(..., description="Authorization code from Google")
    state: Optional[str] = Field(None, description="State parameter (optional, for CSRF protection)")
    redirect_uri: str = Field(..., description="OAuth redirect URI")


@router.post(
    "/initiate",
    response_model=InitiateGoogleAuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Initiate Google OAuth flow",
    description="Generate Google OAuth authorization URL for user sign-in/sign-up",
)
async def initiate_google_auth(request: InitiateGoogleAuthRequest):
    """
    Initiate Google OAuth flow for user authentication.
    
    This endpoint generates an authorization URL that the frontend should redirect to.
    After the user authenticates with Google, they will be redirected back to the
    callback endpoint with an authorization code.
    """
    try:
        if not settings.google.is_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google OAuth is not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
            )

        from google_auth_oauthlib.flow import Flow

        # Normalize redirect_uri (remove trailing slash, ensure consistent format)
        normalized_redirect_uri = request.redirect_uri.rstrip("/")

        # Create OAuth flow
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.google.client_id,
                    "client_secret": settings.google.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [normalized_redirect_uri],
                }
            },
            scopes=GOOGLE_AUTH_SCOPES,
        )
        flow.redirect_uri = normalized_redirect_uri

        # Generate authorization URL
        # Note: For user authentication, we don't need to pass user_id in state
        # The state can be used for CSRF protection if needed
        auth_url, _ = flow.authorization_url(
            access_type="online",  # For user auth, we don't need refresh tokens
            include_granted_scopes="false",  # Only request our specific scopes, don't include previously granted ones
            prompt="select_account",  # Let user choose account
        )

        if not auth_url or not isinstance(auth_url, str) or not auth_url.startswith("http"):
            raise ValidationError(f"Invalid authorization URL format: {auth_url}")

        logger.info(f"Generated Google authorization URL, redirect_uri={normalized_redirect_uri}")
        return InitiateGoogleAuthResponse(authUrl=auth_url)

    except ValidationError as e:
        logger.error(f"Validation error initiating Google OAuth: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error initiating Google OAuth: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate Google OAuth flow",
        ) from e


@router.post(
    "/callback",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Handle Google OAuth callback",
    description="Exchange authorization code for tokens and authenticate user",
    response_model_by_alias=True,
)
async def handle_google_callback(
    request: GoogleCallbackRequest,
    current_user: Optional[TokenValidationResult] = Depends(get_optional_user),
):
    """
    Handle Google OAuth callback.
    
    This endpoint:
    1. Exchanges the authorization code for an ID token
    2. Validates the ID token
    3. Syncs/creates the user in the database
    4. Returns JWT tokens for the user
    
    Note: If the user is already authenticated (has a valid token), we skip
    code exchange to handle duplicate requests from React StrictMode.
    """
    try:
        if not settings.google.is_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google OAuth is not configured.",
            )

        # Normalize redirect_uri (must match exactly what was used in initiation)
        # Remove trailing slash and ensure consistent format
        normalized_redirect_uri = request.redirect_uri.rstrip("/")
        
        # Log detailed information for debugging
        logger.info(f"Handling Google OAuth callback", {
            "redirect_uri": normalized_redirect_uri,
            "original_redirect_uri": request.redirect_uri,
            "code_length": len(request.code) if request.code else 0,
            "has_state": bool(request.state),
            "user_already_authenticated": current_user is not None,
            "client_id": settings.google.client_id[:10] + "..." if settings.google.client_id else None,
        })

        # Exchange authorization code for tokens using manual HTTP exchange
        # This bypasses the google_auth_oauthlib library's strict scope validation
        # which can fail when users have previously authorized additional scopes (e.g., calendar)
        logger.debug("Exchanging authorization code for tokens using manual HTTP exchange")
        
        import httpx
        try:
            # Log token exchange request details (without secrets)
            logger.debug("Token exchange request details", {
                "redirect_uri": normalized_redirect_uri,
                "code_length": len(request.code) if request.code else 0,
                "client_id": settings.google.client_id[:10] + "..." if settings.google.client_id else None,
                "has_client_secret": bool(settings.google.client_secret),
            })
            
            async with httpx.AsyncClient() as client:
                token_response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "code": request.code,
                        "client_id": settings.google.client_id,
                        "client_secret": settings.google.client_secret,
                        "redirect_uri": normalized_redirect_uri,
                        "grant_type": "authorization_code",
                    },
                )
                
                # Check response status and log error details
                if token_response.status_code != 200:
                    error_body = token_response.text
                    try:
                        error_json = token_response.json()
                        error_message = error_json.get("error", "unknown_error")
                        error_description = error_json.get("error_description", error_body)
                    except:
                        error_message = "unknown_error"
                        error_description = error_body
                    
                    logger.error(
                        f"Token exchange failed with status {token_response.status_code}: {error_message} - {error_description}",
                        extra={
                            "status_code": token_response.status_code,
                            "error": error_message,
                            "error_description": error_description,
                            "response_body": error_body,
                            "redirect_uri": normalized_redirect_uri,
                            "code_length": len(request.code) if request.code else 0,
                            "client_id": settings.google.client_id[:10] + "..." if settings.google.client_id else None,
                        }
                    )
                    token_response.raise_for_status()
                
                token_data = token_response.json()
                id_token = token_data.get("id_token")
                access_token = token_data.get("access_token")
                
                if not id_token:
                    raise ValidationError("No ID token received from Google token exchange")
                
                logger.info("Successfully exchanged authorization code for tokens")
                
        except httpx.HTTPStatusError as http_error:
            # HTTP error from Google - log the response body
            error_body = ""
            error_message = "unknown_error"
            error_description = ""
            
            if http_error.response:
                try:
                    error_body = http_error.response.text
                    error_json = http_error.response.json()
                    error_message = error_json.get("error", "unknown_error")
                    error_description = error_json.get("error_description", error_body)
                except:
                    error_body = http_error.response.text if http_error.response else ""
                    error_description = error_body
            
            logger.error(
                f"Token exchange failed with HTTP {http_error.response.status_code if http_error.response else 'unknown'}: {error_message} - {error_description}",
                exc_info=True,
                extra={
                    "status_code": http_error.response.status_code if http_error.response else None,
                    "error": error_message,
                    "error_description": error_description,
                    "response_body": error_body,
                    "redirect_uri": normalized_redirect_uri,
                    "code_length": len(request.code) if request.code else 0,
                    "client_id": settings.google.client_id[:10] + "..." if settings.google.client_id else None,
                }
            )
            
            # Provide helpful error messages based on the error
            if "invalid_grant" in error_message.lower() or "invalid_grant" in error_description.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Authorization code is invalid or has expired. "
                        "This usually happens if: "
                        "(1) The code was already used, "
                        "(2) The redirect URI doesn't match exactly, or "
                        "(3) Too much time passed between authorization and callback. "
                        "Please try signing in again."
                    ),
                ) from http_error
            elif "redirect_uri_mismatch" in error_message.lower() or "redirect_uri_mismatch" in error_description.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Redirect URI mismatch. "
                        f"Expected redirect URI in Google Console must match exactly: {normalized_redirect_uri}. "
                        f"Please check your Google OAuth configuration."
                    ),
                ) from http_error
            elif "invalid_client" in error_message.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Invalid Google OAuth client credentials. "
                        "Please check that GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are correctly configured."
                    ),
                ) from http_error
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Failed to exchange authorization code with Google. "
                        f"Error: {error_message} - {error_description or str(http_error)}. "
                        f"Please try signing in again."
                    ),
                ) from http_error
        except Exception as e:
            logger.error(
                f"Unexpected error during token exchange: {e}",
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to exchange authorization code: {str(e)}",
            ) from e

        # Validate the ID token and get user info
        # Pass access_token to enable at_hash validation
        google_client = get_google_oauth_client()
        user_info = await google_client.get_user_info(id_token, access_token=access_token)

        # Sync user to database
        # Use a transaction to ensure atomicity and prevent race conditions
        async with get_session_context() as session:
            user_service = get_user_service(session)

            # Check if user already exists before syncing (helps with duplicate requests)
            existing_user = await user_service.repository.get_by_google_id(user_info.sub)
            if existing_user:
                logger.info(
                    f"User already exists for Google ID {user_info.sub}, skipping sync. "
                    f"User ID: {existing_user.id}"
                )
                user_profile = user_service._user_to_profile(existing_user)
            else:
                # Sync user from Google (this handles creation or updates)
                user_profile = await user_service.sync_user_from_google(
                    google_id=user_info.sub,
                    email=user_info.email or "",
                    name=user_info.name or user_info.given_name or "Google User",
                    google_email=user_info.email,
                    picture=user_info.picture,
                    given_name=user_info.given_name,
                    family_name=user_info.family_name,
                )

            # Update last login
            await user_service.update_last_login(user_profile.id)

        # Generate internal JWT tokens for the user
        # Note: We use internal JWT tokens even for OAuth users for consistency
        access_token = create_access_token(
            user_id=user_profile.id,
            email=user_profile.email,
        )
        refresh_token = create_refresh_token(
            user_id=user_profile.id,
            email=user_profile.email,
        )

        # Calculate expiration
        expires_in = settings.jwt.access_token_expire_minutes * 60

        logger.info(f"Google OAuth authentication successful for user: {user_profile.id} ({user_profile.email})")

        return LoginResponse(
            token=access_token,
            refresh_token=refresh_token,
            user=user_profile,
            expires_in=expires_in,
        )

    except ValidationError as e:
        logger.error(f"Validation error in Google OAuth callback: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except AuthenticationError as e:
        logger.error(f"Authentication error in Google OAuth callback: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error handling Google OAuth callback: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to handle Google OAuth callback",
        ) from e

