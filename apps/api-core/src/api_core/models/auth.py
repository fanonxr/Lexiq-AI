"""Authentication request/response models."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    """Login request model."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")


class SignupRequest(BaseModel):
    """Signup request model."""

    name: str = Field(..., min_length=1, max_length=100, description="User full name")
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password (minimum 8 characters)")


class ResetPasswordRequest(BaseModel):
    """Password reset request model."""

    email: EmailStr = Field(..., description="User email address")


class ResetPasswordResponse(BaseModel):
    """Password reset response model."""

    message: str = Field(..., description="Success message")


class VerifyEmailRequest(BaseModel):
    """Email verification request model."""

    token: str = Field(..., description="Email verification token")


class VerifyEmailResponse(BaseModel):
    """Email verification response model."""

    message: str = Field(..., description="Success message")


class RefreshTokenRequest(BaseModel):
    """Token refresh request model."""

    refresh_token: str = Field(..., description="Refresh token")


class LogoutRequest(BaseModel):
    """Logout request model (optional body)."""

    pass  # No fields needed


class LogoutResponse(BaseModel):
    """Logout response model."""

    message: str = Field(default="Logged out successfully", description="Success message")


class UserProfile(BaseModel):
    """User profile response model."""

    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email address")
    name: str = Field(..., description="User full name")
    is_active: bool = Field(default=True, description="Whether the user account is active")
    is_verified: bool = Field(default=False, description="Whether the email is verified")
    created_at: Optional[str] = Field(None, description="Account creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


class LoginResponse(BaseModel):
    """Login response model."""

    model_config = ConfigDict(populate_by_name=True)  # Allow both snake_case and camelCase

    token: str = Field(..., description="Access token")
    refresh_token: Optional[str] = Field(None, description="Refresh token", alias="refreshToken")
    user: UserProfile = Field(..., description="User profile")
    expires_in: Optional[int] = Field(None, description="Token expiration time in seconds", alias="expiresIn")


class SignupResponse(BaseModel):
    """Signup response model."""

    model_config = ConfigDict(populate_by_name=True)  # Allow both snake_case and camelCase

    token: str = Field(..., description="Access token")
    refresh_token: Optional[str] = Field(None, description="Refresh token", alias="refreshToken")
    user: UserProfile = Field(..., description="User profile")
    expires_in: Optional[int] = Field(None, description="Token expiration time in seconds", alias="expiresIn")


class RefreshTokenResponse(BaseModel):
    """Token refresh response model."""

    model_config = ConfigDict(populate_by_name=True)  # Allow both snake_case and camelCase

    token: str = Field(..., description="New access token")
    expires_in: Optional[int] = Field(None, description="Token expiration time in seconds", alias="expiresIn")
