"""User management service with business logic."""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from api_core.database.models import User
from api_core.exceptions import NotFoundError, ValidationError
from api_core.models.auth import UserProfile
from api_core.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class UserService:
    """Service for user management operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize user service.

        Args:
            session: Database session
        """
        self.repository = UserRepository(session)

    def _user_to_profile(self, user: User) -> UserProfile:
        """
        Convert SQLAlchemy User model to Pydantic UserProfile.

        Args:
            user: User database model

        Returns:
            UserProfile Pydantic model
        """
        return UserProfile(
            id=user.id,
            email=user.email,
            name=user.name,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at.isoformat() if user.created_at else None,
            updated_at=user.updated_at.isoformat() if user.updated_at else None,
        )

    def _user_to_response(self, user: User):
        """
        Convert SQLAlchemy User model to UserResponse.

        Args:
            user: User database model

        Returns:
            UserResponse Pydantic model
        """
        from api_core.models.user import UserResponse

        return UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            given_name=user.given_name,
            family_name=user.family_name,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at.isoformat() if user.created_at else None,
            updated_at=user.updated_at.isoformat() if user.updated_at else None,
            last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
        )

    async def create_user(
        self,
        email: str,
        name: str,
        password: Optional[str] = None,
        hashed_password: Optional[str] = None,
        azure_ad_object_id: Optional[str] = None,
        azure_ad_tenant_id: Optional[str] = None,
        is_verified: bool = False,
        **kwargs,
    ) -> UserProfile:
        """
        Create a new user.

        Args:
            email: User email address
            name: User full name
            password: Plain password (will be hashed)
            hashed_password: Pre-hashed password (if password not provided)
            azure_ad_object_id: Azure AD B2C object ID (for OAuth users)
            azure_ad_tenant_id: Azure AD B2C tenant ID
            is_verified: Whether email is verified
            **kwargs: Additional user fields

        Returns:
            Created user profile

        Raises:
            ValidationError: If validation fails
        """
        # Validate email
        if not email or not email.strip():
            raise ValidationError("Email is required")

        # Validate name
        if not name or not name.strip():
            raise ValidationError("Name is required")

        # Hash password if provided
        final_hashed_password = hashed_password
        if password:
            # Reuse the shared pwd_context from auth_service to avoid creating multiple instances
            # and to benefit from the warning suppression
            # Always pre-hash with SHA256 to avoid bcrypt's 72-byte limit
            # This ensures we can handle passwords of any length
            from api_core.services.auth_service import pwd_context
            import hashlib
            
            # Pre-hash with SHA256 to avoid bcrypt's 72-byte limit
            # This is a common and secure pattern for handling long passwords
            password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
            final_hashed_password = pwd_context.hash(password_hash)

        # For email/password users, password is required
        if not azure_ad_object_id and not final_hashed_password:
            raise ValidationError("Password is required for email/password users")

        # Create user
        try:
            user = await self.repository.create_user(
                email=email,
                name=name,
                hashed_password=final_hashed_password,
                azure_ad_object_id=azure_ad_object_id,
                azure_ad_tenant_id=azure_ad_tenant_id,
                is_verified=is_verified,
                **kwargs,
            )
            logger.info(f"Created user: {user.id} ({user.email})")
            return self._user_to_profile(user)
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise

    async def get_user_by_id(self, user_id: str) -> Optional[UserProfile]:
        """
        Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User profile or None if not found
        """
        user = await self.repository.get_by_id(user_id)
        if not user:
            return None
        return self._user_to_profile(user)

    async def get_user_by_id_or_azure_ad_object_id(
        self, user_id: str, azure_ad_object_id: Optional[str] = None
    ) -> Optional[UserProfile]:
        """
        Get user by ID, with fallback to Azure AD object ID.
        
        This is useful when user_id might be either:
        - Database UUID (after successful auto-sync)
        - Azure AD object ID (if auto-sync failed or hasn't run)

        Args:
            user_id: User ID (could be database UUID or Azure AD object ID)
            azure_ad_object_id: Optional Azure AD object ID for fallback

        Returns:
            User profile or None if not found
        """
        # Try database ID first
        user = await self.repository.get_by_id(user_id)
        if user:
            return self._user_to_profile(user)
        
        # Fallback to Azure AD object ID if provided
        if azure_ad_object_id:
            user = await self.repository.get_by_azure_ad_object_id(azure_ad_object_id)
            if user:
                return self._user_to_profile(user)
        
        return None

    async def get_user_by_email(self, email: str) -> Optional[UserProfile]:
        """
        Get user by email.

        Args:
            email: User email address

        Returns:
            User profile or None if not found
        """
        user = await self.repository.get_by_email(email)
        if not user:
            return None
        return self._user_to_profile(user)

    async def get_user_by_azure_ad_object_id(self, object_id: str) -> Optional[UserProfile]:
        """
        Get user by Azure AD B2C object ID.

        Args:
            object_id: Azure AD B2C object ID

        Returns:
            User profile or None if not found
        """
        user = await self.repository.get_by_azure_ad_object_id(object_id)
        if not user:
            return None
        return self._user_to_profile(user)

    async def update_user_profile(
        self, user_id: str, profile_data: Dict[str, any]
    ) -> UserProfile:
        """
        Update user profile.

        Args:
            user_id: User ID
            profile_data: Dictionary of fields to update

        Returns:
            Updated user profile

        Raises:
            NotFoundError: If user not found
            ValidationError: If validation fails
        """
        # Validate profile data
        allowed_fields = {
            "name",
            "given_name",
            "family_name",
            "email",
        }

        # Filter out disallowed fields
        filtered_data = {k: v for k, v in profile_data.items() if k in allowed_fields}

        # Validate email if provided
        if "email" in filtered_data:
            email = filtered_data["email"]
            if not email or not email.strip():
                raise ValidationError("Email cannot be empty")

            # Check if email is already taken by another user
            existing = await self.repository.get_by_email(email)
            if existing and existing.id != user_id:
                raise ValidationError("Email is already taken")

        # Update user
        user = await self.repository.update_user(user_id, **filtered_data)
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")

        logger.info(f"Updated user profile: {user_id}")
        return self._user_to_profile(user)

    async def deactivate_user(self, user_id: str) -> UserProfile:
        """
        Deactivate a user account.

        Args:
            user_id: User ID

        Returns:
            Deactivated user profile

        Raises:
            NotFoundError: If user not found
        """
        user = await self.repository.deactivate_user(user_id)
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")

        logger.info(f"Deactivated user: {user_id}")
        return self._user_to_profile(user)

    async def activate_user(self, user_id: str) -> UserProfile:
        """
        Activate a user account.

        Args:
            user_id: User ID

        Returns:
            Activated user profile

        Raises:
            NotFoundError: If user not found
        """
        user = await self.repository.activate_user(user_id)
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")

        logger.info(f"Activated user: {user_id}")
        return self._user_to_profile(user)

    async def verify_user_email(self, user_id: str) -> UserProfile:
        """
        Verify user email address.

        Args:
            user_id: User ID

        Returns:
            Updated user profile

        Raises:
            NotFoundError: If user not found
        """
        user = await self.repository.verify_email(user_id)
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")

        logger.info(f"Verified email for user: {user_id}")
        return self._user_to_profile(user)

    async def search_users(
        self,
        query: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_verified: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[UserProfile]:
        """
        Search users with filters.

        Args:
            query: Search query (searches name and email)
            is_active: Filter by active status
            is_verified: Filter by verified status
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of user profiles
        """
        users = await self.repository.search_users(
            query=query,
            is_active=is_active,
            is_verified=is_verified,
            skip=skip,
            limit=limit,
        )
        return [self._user_to_profile(user) for user in users]

    async def sync_user_from_azure_ad(
        self,
        azure_ad_object_id: str,
        email: str,
        name: str,
        azure_ad_tenant_id: Optional[str] = None,
        **kwargs,
    ) -> UserProfile:
        """
        Sync or create user from Azure AD B2C.

        This method is called when a user authenticates with Azure AD B2C.
        It will create the user if they don't exist, or update their information
        if they do exist.

        Args:
            azure_ad_object_id: Azure AD B2C object ID
            email: User email address
            name: User full name
            azure_ad_tenant_id: Azure AD B2C tenant ID
            **kwargs: Additional user fields from Azure AD

        Returns:
            User profile (created or updated)
        """
        # Check if user exists by Azure AD object ID
        existing_user = await self.repository.get_by_azure_ad_object_id(azure_ad_object_id)

        if existing_user:
            # Update existing user
            update_data = {
                "email": email,
                "name": name,
                "azure_ad_tenant_id": azure_ad_tenant_id,
                "is_verified": True,  # Azure AD users are pre-verified
            }
            update_data.update(kwargs)

            user = await self.repository.update_user(existing_user.id, **update_data)
            logger.info(f"Synced existing user from Azure AD: {user.id}")
            return self._user_to_profile(user)
        else:
            # Check if user exists by email (might be email/password user)
            existing_by_email = await self.repository.get_by_email(email)
            if existing_by_email:
                # Link Azure AD to existing user
                user = await self.repository.update_user(
                    existing_by_email.id,
                    azure_ad_object_id=azure_ad_object_id,
                    azure_ad_tenant_id=azure_ad_tenant_id,
                    is_verified=True,
                )
                logger.info(f"Linked Azure AD to existing user: {user.id}")
                return self._user_to_profile(user)
            else:
                # Create new user from Azure AD
                user = await self.repository.create_user(
                    email=email,
                    name=name,
                    azure_ad_object_id=azure_ad_object_id,
                    azure_ad_tenant_id=azure_ad_tenant_id,
                    is_verified=True,  # Azure AD users are pre-verified
                    **kwargs,
                )
                logger.info(f"Created new user from Azure AD: {user.id}")
                return self._user_to_profile(user)

    async def update_last_login(self, user_id: str) -> None:
        """
        Update user's last login timestamp.

        Args:
            user_id: User ID
        """
        await self.repository.update_last_login(user_id)
        logger.debug(f"Updated last login for user: {user_id}")


def get_user_service(session: AsyncSession) -> UserService:
    """
    Get a UserService instance.

    Args:
        session: Database session

    Returns:
        UserService instance
    """
    return UserService(session)
