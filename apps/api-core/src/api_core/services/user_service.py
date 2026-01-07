"""User management service with business logic."""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from api_core.database.models import User
from api_core.exceptions import ConflictError, NotFoundError, ValidationError
from sqlalchemy.exc import IntegrityError
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
        self.session = session
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
            firm_id=user.firm_id,
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
            # If firm_id is not provided, create a firm for the user
            firm_id = kwargs.get("firm_id")
            if not firm_id:
                from api_core.repositories.firms_repository import FirmsRepository
                firms_repo = FirmsRepository(self.session)
                
                # Create a firm for the user (using user's name as firm name)
                firm = await firms_repo.create(
                    name=f"{name}'s Firm",  # Default firm name
                )
                firm_id = firm.id
                logger.info(f"Created firm {firm_id} for new user {email}")
            
            # Create user with firm_id
            user = await self.repository.create_user(
                email=email,
                name=name,
                hashed_password=final_hashed_password,
                azure_ad_object_id=azure_ad_object_id,
                azure_ad_tenant_id=azure_ad_tenant_id,
                is_verified=is_verified,
                firm_id=firm_id,  # Always set firm_id
                **{k: v for k, v in kwargs.items() if k != "firm_id"},  # Exclude firm_id from kwargs
            )
            logger.info(f"Created user: {user.id} ({user.email}) with firm_id: {firm_id}")
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

    async def get_user_by_google_id(self, google_id: str) -> Optional[UserProfile]:
        """
        Get user by Google ID.

        Args:
            google_id: Google user ID (sub claim)

        Returns:
            User profile or None if not found
        """
        user = await self.repository.get_by_google_id(google_id)
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
            # Update given_name and family_name if provided
            if "given_name" in kwargs:
                update_data["given_name"] = kwargs["given_name"]
            if "family_name" in kwargs:
                update_data["family_name"] = kwargs["family_name"]
            # Add other kwargs (excluding already handled fields)
            for key, value in kwargs.items():
                if key not in ["given_name", "family_name", "firm_id"]:
                    update_data[key] = value

            user = await self.repository.update_user(existing_user.id, **update_data)
            logger.info(f"Synced existing user from Azure AD: {user.id}")
            return self._user_to_profile(user)
        else:
            # Check if user exists by email (might be email/password user, Google user, etc.)
            existing_by_email = await self.repository.get_by_email(email)
            if existing_by_email:
                # Link Azure AD to existing user
                # Preserve existing provider IDs (don't overwrite Google ID if present)
                update_data = {
                    "azure_ad_object_id": azure_ad_object_id,
                    "azure_ad_tenant_id": azure_ad_tenant_id,
                    "is_verified": True,  # Azure AD users are pre-verified
                }
                # Update name if provided and different
                if name and name != existing_by_email.name:
                    update_data["name"] = name
                
                user = await self.repository.update_user(
                    existing_by_email.id,
                    **update_data,
                )
                logger.info(
                    f"Linked Azure AD to existing user: {user.id} "
                    f"(email: {email}, had_google: {bool(user.google_id)}, had_password: {bool(user.hashed_password)})"
                )
                return self._user_to_profile(user)
            else:
                # Create new user from Azure AD
                # Create a firm for the user if they don't have one
                firm_id = kwargs.get("firm_id")
                if not firm_id:
                    from api_core.repositories.firms_repository import FirmsRepository
                    firms_repo = FirmsRepository(self.session)
                    
                    # Create a firm for the user
                    firm = await firms_repo.create(
                        name=f"{name}'s Firm",  # Default firm name
                    )
                    firm_id = firm.id
                    logger.info(f"Created firm {firm_id} for new Azure AD user {email}")
                
                # Prepare user creation data
                create_data = {
                    "email": email,
                    "name": name,
                    "azure_ad_object_id": azure_ad_object_id,
                    "azure_ad_tenant_id": azure_ad_tenant_id,
                    "is_verified": True,  # Azure AD users are pre-verified
                    "firm_id": firm_id,
                }
                # Add given_name and family_name if provided
                if "given_name" in kwargs:
                    create_data["given_name"] = kwargs["given_name"]
                if "family_name" in kwargs:
                    create_data["family_name"] = kwargs["family_name"]
                # Add other kwargs (excluding firm_id)
                for key, value in kwargs.items():
                    if key not in ["given_name", "family_name", "firm_id"]:
                        create_data[key] = value
                
                user = await self.repository.create_user(**create_data)
                logger.info(f"Created new user from Azure AD: {user.id} with firm_id: {firm_id}")
                return self._user_to_profile(user)

    async def sync_user_from_google(
        self,
        google_id: str,
        email: str,
        name: str,
        google_email: Optional[str] = None,
        picture: Optional[str] = None,
        **kwargs,
    ) -> UserProfile:
        """
        Sync or create user from Google OAuth.

        This method is called when a user authenticates with Google.
        It will create the user if they don't exist, or update their information
        if they do exist.

        Args:
            google_id: Google user ID (sub claim)
            email: User email address (primary email)
            name: User full name
            google_email: Google-specific email (may differ from primary email)
            picture: User profile picture URL
            **kwargs: Additional user fields from Google

        Returns:
            User profile (created or updated)
        """
        # Check if user exists by Google ID
        existing_user = await self.repository.get_by_google_id(google_id)

        if existing_user:
            # Update existing user
            update_data = {
                "email": email,
                "name": name,
                "google_email": google_email or email,
                "is_verified": True,  # Google users are pre-verified
            }
            # Update given_name and family_name if provided
            if "given_name" in kwargs:
                update_data["given_name"] = kwargs["given_name"]
            if "family_name" in kwargs:
                update_data["family_name"] = kwargs["family_name"]
            # Store picture in metadata_json if we have that field
            # For now, we'll just update the basic fields
            if picture:
                # TODO: Store picture URL in metadata_json or add picture field to User model
                pass
            # Add other kwargs (excluding already handled fields)
            for key, value in kwargs.items():
                if key not in ["given_name", "family_name", "picture", "firm_id"]:
                    update_data[key] = value

            user = await self.repository.update_user(existing_user.id, **update_data)
            logger.info(f"Synced existing user from Google: {user.id}")
            return self._user_to_profile(user)
        else:
            # Check if user exists by email (might be email/password user, Azure AD user, etc.)
            existing_by_email = await self.repository.get_by_email(email)
            if existing_by_email:
                # Link Google to existing user
                # Preserve existing provider IDs (don't overwrite Azure AD ID if present)
                update_data = {
                    "google_id": google_id,
                    "google_email": google_email or email,
                    "is_verified": True,  # Google users are pre-verified
                }
                # Update name if provided and different
                if name and name != existing_by_email.name:
                    update_data["name"] = name
                
                user = await self.repository.update_user(
                    existing_by_email.id,
                    **update_data,
                )
                logger.info(
                    f"Linked Google to existing user: {user.id} "
                    f"(email: {email}, had_azure_ad: {bool(user.azure_ad_object_id)}, had_password: {bool(user.hashed_password)})"
                )
                return self._user_to_profile(user)
            else:
                # Create new user from Google
                # Create a firm for the user if they don't have one
                firm_id = kwargs.get("firm_id")
                if not firm_id:
                    from api_core.repositories.firms_repository import FirmsRepository
                    firms_repo = FirmsRepository(self.session)
                    
                    # Create a firm for the user
                    firm = await firms_repo.create(
                        name=f"{name}'s Firm",  # Default firm name
                    )
                    firm_id = firm.id
                    logger.info(f"Created firm {firm_id} for new Google user {email}")
                
                # Prepare user creation data
                create_data = {
                    "email": email,
                    "name": name,
                    "google_id": google_id,
                    "google_email": google_email or email,
                    "is_verified": True,  # Google users are pre-verified
                    "firm_id": firm_id,
                }
                # Add given_name and family_name if provided
                if "given_name" in kwargs:
                    create_data["given_name"] = kwargs["given_name"]
                if "family_name" in kwargs:
                    create_data["family_name"] = kwargs["family_name"]
                # Add other kwargs (excluding firm_id)
                for key, value in kwargs.items():
                    if key not in ["given_name", "family_name", "picture", "firm_id"]:
                        create_data[key] = value
                
                try:
                    user = await self.repository.create_user(**create_data)
                    logger.info(f"Created new user from Google: {user.id} with firm_id: {firm_id}")
                    return self._user_to_profile(user)
                except (ConflictError, IntegrityError) as e:
                    # User was created between our check and create attempt (race condition)
                    # Or email normalization issue - try to find and link the existing user
                    logger.warning(
                        f"User creation failed due to conflict/integrity error, attempting to find existing user. "
                        f"Error: {type(e).__name__}: {str(e)}"
                    )
                    
                    # Re-check for existing user by email (case-insensitive, normalized)
                    existing_by_email = await self.repository.get_by_email(email)
                    if existing_by_email:
                        # Link Google to existing user
                        update_data = {
                            "google_id": google_id,
                            "google_email": google_email or email,
                            "is_verified": True,
                        }
                        # Update name if provided and different
                        if name and name != existing_by_email.name:
                            update_data["name"] = name
                        
                        user = await self.repository.update_user(
                            existing_by_email.id,
                            **update_data,
                        )
                        logger.info(
                            f"Linked Google to existing user after conflict: {user.id} "
                            f"(email: {email})"
                        )
                        return self._user_to_profile(user)
                    
                    # Re-check by Google ID in case it was created
                    existing_by_google = await self.repository.get_by_google_id(google_id)
                    if existing_by_google:
                        logger.info(
                            f"Found existing user by Google ID after conflict: {existing_by_google.id}"
                        )
                        return self._user_to_profile(existing_by_google)
                    
                    # If still not found, log the error and re-raise
                    logger.error(
                        f"Could not find existing user after conflict error. "
                        f"Email: {email}, Google ID: {google_id}, Error: {e}",
                        exc_info=True
                    )
                    raise ConflictError(
                        f"User with email {email} or Google ID {google_id} already exists, "
                        f"but could not be found. This may indicate a database consistency issue."
                    ) from e

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
