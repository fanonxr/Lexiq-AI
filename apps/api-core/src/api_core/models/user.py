"""User request/response models."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserProfileUpdate(BaseModel):
    """User profile update request model."""

    name: Optional[str] = Field(None, min_length=1, max_length=255, description="User full name")
    given_name: Optional[str] = Field(None, max_length=100, description="User given name")
    family_name: Optional[str] = Field(None, max_length=100, description="User family name")
    email: Optional[EmailStr] = Field(None, description="User email address")


class UserResponse(BaseModel):
    """User response model."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email address")
    name: str = Field(..., description="User full name")
    given_name: Optional[str] = Field(None, description="User given name")
    family_name: Optional[str] = Field(None, description="User family name")
    is_active: bool = Field(..., description="Whether the user account is active")
    is_verified: bool = Field(..., description="Whether the email is verified")
    created_at: Optional[str] = Field(None, description="Account creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")
    last_login_at: Optional[str] = Field(None, description="Last login timestamp")


class UserListResponse(BaseModel):
    """User list response model with pagination."""

    model_config = ConfigDict(populate_by_name=True)

    users: List[UserResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    skip: int = Field(..., description="Number of records skipped")
    limit: int = Field(..., description="Maximum number of records returned")
