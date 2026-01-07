"""User repository for data access operations."""

import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from api_core.database.models import User
from api_core.exceptions import ConflictError, DatabaseError, NotFoundError
from api_core.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository[User]):
    """Repository for user data access operations."""

    def __init__(self, session: AsyncSession):
        """Initialize user repository."""
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.

        Args:
            email: User email address

        Returns:
            User instance or None if not found
        """
        try:
            result = await self.session.execute(
                select(User).where(User.email == email.lower().strip())
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting user by email {email}: {e}")
            raise DatabaseError("Failed to retrieve user by email") from e

    async def get_by_azure_ad_object_id(self, object_id: str) -> Optional[User]:
        """
        Get user by Azure AD B2C object ID.

        Args:
            object_id: Azure AD B2C object ID

        Returns:
            User instance or None if not found
        """
        try:
            result = await self.session.execute(
                select(User).where(User.azure_ad_object_id == object_id)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting user by Azure AD object ID {object_id}: {e}")
            raise DatabaseError("Failed to retrieve user by Azure AD object ID") from e

    async def get_by_google_id(self, google_id: str) -> Optional[User]:
        """
        Get user by Google ID.

        Args:
            google_id: Google user ID (sub claim)

        Returns:
            User instance or None if not found
        """
        try:
            result = await self.session.execute(
                select(User).where(User.google_id == google_id)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting user by Google ID {google_id}: {e}")
            raise DatabaseError("Failed to retrieve user by Google ID") from e

    async def create_user(
        self,
        email: str,
        name: str,
        hashed_password: Optional[str] = None,
        azure_ad_object_id: Optional[str] = None,
        azure_ad_tenant_id: Optional[str] = None,
        is_verified: bool = False,
        **kwargs,
    ) -> User:
        """
        Create a new user.

        Args:
            email: User email address
            name: User full name
            hashed_password: Hashed password (for email/password users)
            azure_ad_object_id: Azure AD B2C object ID (for OAuth users)
            azure_ad_tenant_id: Azure AD B2C tenant ID
            is_verified: Whether email is verified
            **kwargs: Additional user fields

        Returns:
            Created user instance

        Raises:
            ConflictError: If user with email or Azure AD object ID already exists
            DatabaseError: If database operation fails
        """
        try:
            # Check if user with email already exists
            existing = await self.get_by_email(email)
            if existing:
                raise ConflictError(f"User with email {email} already exists")

            # Check if user with Azure AD object ID already exists
            if azure_ad_object_id:
                existing = await self.get_by_azure_ad_object_id(azure_ad_object_id)
                if existing:
                    raise ConflictError(
                        f"User with Azure AD object ID {azure_ad_object_id} already exists"
                    )

            # Check if user with Google ID already exists
            google_id = kwargs.get("google_id")
            if google_id:
                existing = await self.get_by_google_id(google_id)
                if existing:
                    raise ConflictError(
                        f"User with Google ID {google_id} already exists"
                    )

            # Create user
            user = await self.create(
                email=email.lower().strip(),
                name=name,
                hashed_password=hashed_password,
                azure_ad_object_id=azure_ad_object_id,
                azure_ad_tenant_id=azure_ad_tenant_id,
                is_verified=is_verified,
                **kwargs,
            )

            logger.info(f"Created user: {user.id} ({user.email})")
            return user

        except ConflictError:
            raise
        except IntegrityError as e:
            logger.error(f"Integrity error creating user: {e}")
            await self.session.rollback()
            raise ConflictError("User with this email or Azure AD object ID already exists") from e
        except SQLAlchemyError as e:
            logger.error(f"Error creating user: {e}")
            await self.session.rollback()
            raise DatabaseError("Failed to create user") from e

    async def update_user(self, user_id: str, **kwargs) -> Optional[User]:
        """
        Update user by ID.

        Args:
            user_id: User ID
            **kwargs: Fields to update

        Returns:
            Updated user instance or None if not found
        """
        try:
            # Normalize email if provided
            if "email" in kwargs:
                kwargs["email"] = kwargs["email"].lower().strip()

            user = await self.update(user_id, **kwargs)
            if user:
                logger.debug(f"Updated user: {user_id}")
            return user
        except IntegrityError as e:
            logger.error(f"Integrity error updating user {user_id}: {e}")
            await self.session.rollback()
            raise ConflictError("Update would violate unique constraint") from e
        except SQLAlchemyError as e:
            logger.error(f"Error updating user {user_id}: {e}")
            await self.session.rollback()
            raise DatabaseError("Failed to update user") from e

    async def verify_email(self, user_id: str) -> Optional[User]:
        """
        Mark user email as verified.

        Args:
            user_id: User ID

        Returns:
            Updated user instance or None if not found
        """
        return await self.update_user(
            user_id, is_verified=True, email_verified_at=datetime.utcnow()
        )

    async def set_password_reset_token(
        self, user_id: str, token: str, expires_at: Optional[datetime] = None
    ) -> Optional[User]:
        """
        Set password reset token for user.

        Args:
            user_id: User ID
            token: Reset token
            expires_at: Token expiration time

        Returns:
            Updated user instance or None if not found
        """
        return await self.update_user(
            user_id, password_reset_token=token, password_reset_expires_at=expires_at
        )

    async def clear_password_reset_token(self, user_id: str) -> Optional[User]:
        """
        Clear password reset token for user.

        Args:
            user_id: User ID

        Returns:
            Updated user instance or None if not found
        """
        return await self.update_user(
            user_id, password_reset_token=None, password_reset_expires_at=None
        )

    async def get_by_reset_token(self, token: str) -> Optional[User]:
        """
        Get user by password reset token.

        Args:
            token: Password reset token

        Returns:
            User instance or None if not found
        """
        try:
            result = await self.session.execute(
                select(User).where(User.password_reset_token == token)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting user by reset token: {e}")
            raise DatabaseError("Failed to retrieve user by reset token") from e

    async def update_last_login(self, user_id: str) -> Optional[User]:
        """
        Update user's last login timestamp.

        Args:
            user_id: User ID

        Returns:
            Updated user instance or None if not found
        """
        return await self.update_user(user_id, last_login_at=datetime.utcnow())

    async def get_by_verification_token(self, token: str) -> Optional[User]:
        """
        Get user by email verification token.

        Args:
            token: Email verification token

        Returns:
            User instance or None if not found
        """
        try:
            result = await self.session.execute(
                select(User).where(User.email_verification_token == token)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting user by verification token: {e}")
            raise DatabaseError("Failed to retrieve user by verification token") from e

    async def set_email_verification_token(
        self, user_id: str, token: str
    ) -> Optional[User]:
        """
        Set email verification token for user.

        Args:
            user_id: User ID
            token: Verification token

        Returns:
            Updated user instance or None if not found
        """
        return await self.update_user(user_id, email_verification_token=token)

    async def clear_email_verification_token(self, user_id: str) -> Optional[User]:
        """
        Clear email verification token for user.

        Args:
            user_id: User ID

        Returns:
            Updated user instance or None if not found
        """
        return await self.update_user(user_id, email_verification_token=None)

    async def deactivate_user(self, user_id: str) -> Optional[User]:
        """
        Deactivate a user account.

        Args:
            user_id: User ID

        Returns:
            Updated user instance or None if not found
        """
        return await self.update_user(user_id, is_active=False)

    async def activate_user(self, user_id: str) -> Optional[User]:
        """
        Activate a user account.

        Args:
            user_id: User ID

        Returns:
            Updated user instance or None if not found
        """
        return await self.update_user(user_id, is_active=True)

    async def search_users(
        self,
        query: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_verified: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[User]:
        """
        Search users with filters.

        Args:
            query: Search query (searches name and email)
            is_active: Filter by active status
            is_verified: Filter by verified status
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of user instances
        """
        try:
            stmt = select(User)

            # Apply filters
            if query:
                search_term = f"%{query.lower()}%"
                stmt = stmt.where(
                    (User.email.ilike(search_term)) | (User.name.ilike(search_term))
                )

            if is_active is not None:
                stmt = stmt.where(User.is_active == is_active)

            if is_verified is not None:
                stmt = stmt.where(User.is_verified == is_verified)

            stmt = stmt.offset(skip).limit(limit).order_by(User.created_at.desc())

            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error searching users: {e}")
            raise DatabaseError("Failed to search users") from e
