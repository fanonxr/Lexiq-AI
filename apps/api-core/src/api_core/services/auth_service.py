"""Authentication service for user operations."""

import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
import warnings

from api_core.auth.jwt import create_access_token, create_refresh_token
from api_core.config import get_settings
from api_core.exceptions import AuthenticationError, NotFoundError, ValidationError
from api_core.models.auth import UserProfile
from api_core.repositories.user_repository import UserRepository
from api_core.services.user_service import UserService

logger = logging.getLogger(__name__)
settings = get_settings()

# Password hashing context
# Suppress bcrypt version detection warning (known issue with bcrypt 4.3.0 and passlib)
# The warning occurs because passlib tries to read bcrypt.__about__.__version__
# which doesn't exist in bcrypt 4.3.0, but passlib handles this gracefully and continues
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", message=".*bcrypt.*", category=UserWarning)
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Service for authentication operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize auth service.

        Args:
            session: Database session
        """
        self.repository = UserRepository(session)
        self.user_service = UserService(session)

    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Always pre-hashes with SHA256 to avoid bcrypt's 72-byte limit.
        This ensures we can handle passwords of any length securely.
        """
        import hashlib
        
        # Always pre-hash with SHA256 to avoid bcrypt's 72-byte limit
        # This is a common and secure pattern for handling passwords of any length
        password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        return pwd_context.hash(password_hash)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against a hash.
        
        Always pre-hashes with SHA256 before bcrypt verification to match our hashing strategy.
        """
        import hashlib
        
        # Pre-hash with SHA256 to match our hashing strategy
        password_hash = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
        return pwd_context.verify(password_hash, hashed_password)

    async def authenticate_user(self, email: str, password: str) -> Optional[UserProfile]:
        """
        Authenticate a user with email and password.

        Args:
            email: User email
            password: User password

        Returns:
            UserProfile if authentication succeeds, None otherwise

        Raises:
            AuthenticationError: If authentication fails
        """
        # Get user by email
        user = await self.repository.get_by_email(email)
        if not user:
            raise AuthenticationError("Invalid email or password")

        # Check if user has a password (email/password user)
        if not user.hashed_password:
            raise AuthenticationError("Invalid email or password")

        # Verify password
        if not self.verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")

        # Check if user is active
        if not user.is_active:
            raise AuthenticationError("User account is not active")

        # Update last login
        await self.repository.update_last_login(user.id)

        # Convert to UserProfile
        return self.user_service._user_to_profile(user)

    async def create_user(
        self, name: str, email: str, password: str
    ) -> UserProfile:
        """
        Create a new user account.

        Args:
            name: User full name
            email: User email
            password: User password

        Returns:
            Created UserProfile

        Raises:
            ValidationError: If user already exists or validation fails
        """
        # Use UserService to create user (it handles validation and password hashing)
        return await self.user_service.create_user(
            email=email,
            name=name,
            password=password,
        )

    async def get_user_by_id(self, user_id: str) -> Optional[UserProfile]:
        """
        Get user by ID.

        Args:
            user_id: User ID

        Returns:
            UserProfile or None if not found
        """
        return await self.user_service.get_user_by_id(user_id)

    async def request_password_reset(self, email: str) -> None:
        """
        Request a password reset.

        TODO: This is a placeholder implementation.
        Will be completed in Phase 4 when user repository and email service are available.

        Args:
            email: User email

        Raises:
            NotFoundError: If user not found
        """
        # TODO: Implement password reset flow
        # 1. Find user by email
        # 2. Generate reset token
        # 3. Store reset token with expiration
        # 4. Send email with reset link
        # async with get_session() as session:
        #     user = await user_repository.get_by_email(session, email)
        #     if not user:
        #         raise NotFoundError("User not found")
        #
        #     reset_token = generate_reset_token()
        #     await user_repository.update_reset_token(session, user.id, reset_token)
        #     await email_service.send_password_reset_email(user.email, reset_token)

        # Placeholder: For now, just log
        logger.info(f"Password reset requested for email: {email}")

    async def verify_email_token(self, token: str) -> bool:
        """
        Verify email verification token.

        TODO: This is a placeholder implementation.
        Will be completed in Phase 4 when user repository is available.

        Args:
            token: Email verification token

        Returns:
            True if token is valid and email is verified

        Raises:
            ValidationError: If token is invalid
        """
        # TODO: Implement email verification
        # async with get_session() as session:
        #     user = await user_repository.get_by_verification_token(session, token)
        #     if not user:
        #         raise ValidationError("Invalid verification token")
        #     if user.is_verified:
        #         return True
        #     await user_repository.verify_email(session, user.id)
        #     await session.commit()
        #     return True

        # Placeholder: For now, raise error
        raise ValidationError(
            "Email verification not yet implemented. "
            "User repository will be available in Phase 4."
        )


def get_auth_service(session: AsyncSession) -> AuthService:
    """
    Get an AuthService instance.

    Args:
        session: Database session

    Returns:
        AuthService instance
    """
    return AuthService(session)
