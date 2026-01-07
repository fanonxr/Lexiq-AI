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
# Suppress bcrypt version detection warning/error (known issue with bcrypt 4.3.0 and passlib)
# The error occurs because passlib tries to read bcrypt.__about__.__version__
# which doesn't exist in bcrypt 4.3.0, but passlib handles this gracefully and continues
# We suppress both warnings and the passlib logger to prevent the error from appearing in logs
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", message=".*bcrypt.*", category=UserWarning)
    # Suppress passlib's bcrypt handler logger to prevent "(trapped) error reading bcrypt version"
    passlib_logger = logging.getLogger("passlib.handlers.bcrypt")
    passlib_logger.setLevel(logging.CRITICAL)  # Only show critical errors, suppress AttributeError
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

    def validate_password_strength(self, password: str) -> None:
        """
        Validate password strength requirements.
        
        Requirements:
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)
        
        Args:
            password: Password to validate
            
        Raises:
            ValidationError: If password doesn't meet requirements
        """
        if not password:
            raise ValidationError("Password is required")
        
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long")
        
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        errors = []
        if not has_upper:
            errors.append("one uppercase letter")
        if not has_lower:
            errors.append("one lowercase letter")
        if not has_digit:
            errors.append("one digit")
        if not has_special:
            errors.append("one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)")
        
        if errors:
            raise ValidationError(
                f"Password must contain at least {', '.join(errors)}"
            )

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
        from datetime import datetime, timedelta
        
        # Get user by email
        user = await self.repository.get_by_email(email)
        if not user:
            raise AuthenticationError("Invalid email or password")

        # Check if user has a password (email/password user)
        if not user.hashed_password:
            raise AuthenticationError("Invalid email or password")

        # Check if account is locked
        if user.locked_until and user.locked_until > datetime.utcnow():
            remaining_minutes = int((user.locked_until - datetime.utcnow()).total_seconds() / 60)
            raise AuthenticationError(
                f"Account is locked due to too many failed login attempts. "
                f"Please try again in {remaining_minutes} minute(s)."
            )

        # Verify password
        password_valid = self.verify_password(password, user.hashed_password)
        
        if not password_valid:
            # Increment failed login attempts
            failed_attempts = (user.failed_login_attempts or 0) + 1
            max_attempts = 5  # Lock after 5 failed attempts
            lockout_minutes = 30  # Lock for 30 minutes
            
            if failed_attempts >= max_attempts:
                # Lock the account
                locked_until = datetime.utcnow() + timedelta(minutes=lockout_minutes)
                await self.repository.update_user(
                    user.id,
                    failed_login_attempts=failed_attempts,
                    locked_until=locked_until,
                )
                raise AuthenticationError(
                    f"Account has been locked due to too many failed login attempts. "
                    f"Please try again in {lockout_minutes} minutes."
                )
            else:
                # Update failed attempts count
                await self.repository.update_user(
                    user.id,
                    failed_login_attempts=failed_attempts,
                )
            
            raise AuthenticationError("Invalid email or password")

        # Successful login - reset failed attempts and unlock if locked
        if user.failed_login_attempts > 0 or user.locked_until:
            await self.repository.update_user(
                user.id,
                failed_login_attempts=0,
                locked_until=None,
            )

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
        # Validate password strength
        self.validate_password_strength(password)
        
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

    async def request_password_reset(self, email: str, frontend_url: str) -> None:
        """
        Request a password reset.

        Generates a secure reset token, stores it with expiration, and sends a reset email.

        Args:
            email: User email
            frontend_url: Frontend base URL for reset link

        Raises:
            NotFoundError: If user not found
        """
        import secrets
        from datetime import datetime, timedelta
        from api_core.services.notifications_service import get_notifications_service
        from api_core.models.notifications import NotificationCreateRequest
        
        # Find user by email
        user = await self.repository.get_by_email(email)
        if not user:
            # Don't reveal if user exists (security best practice)
            logger.info(f"Password reset requested for email: {email} (user not found)")
            return
        
        # Check if user has a password (email/password users only)
        if not user.hashed_password:
            # User doesn't have a password (OAuth-only user)
            logger.info(f"Password reset requested for OAuth-only user: {email}")
            return
        
        # Generate secure reset token
        reset_token = secrets.token_urlsafe(32)
        
        # Set expiration (24 hours)
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        # Store token in database
        await self.repository.set_password_reset_token(user.id, reset_token, expires_at)
        
        # Create reset link
        reset_link = f"{frontend_url}/auth/reset-password/confirm?token={reset_token}"
        
        # Create email content
        subject = "Reset your password"
        message = f"""
Hello,

You requested to reset your password. Click the link below to reset it:

{reset_link}

This link will expire in 24 hours.

If you didn't request a password reset, please ignore this email. Your password will remain unchanged.

Best regards,
LexiqAI Team
        """.strip()
        
        # Send email via notifications service
        if user.firm_id:
            notifications_service = get_notifications_service(self.repository.session)
            await notifications_service.create_notification(
                NotificationCreateRequest(
                    firm_id=user.firm_id,
                    channel="email",
                    to=user.email,
                    subject=subject,
                    message=message,
                    idempotency_key=f"password_reset_{user.id}_{reset_token[:16]}",
                )
            )
            logger.info(f"Password reset email sent to {email} for user {user.id}")
        else:
            logger.warning(f"User {user.id} has no firm_id, cannot send password reset email")

    async def confirm_password_reset(self, token: str, new_password: str) -> None:
        """
        Confirm password reset with token and new password.

        Args:
            token: Password reset token
            new_password: New password

        Raises:
            ValidationError: If token is invalid or expired
            NotFoundError: If user not found
        """
        from datetime import datetime
        
        # Find user by reset token
        user = await self.repository.get_by_reset_token(token)
        if not user:
            raise ValidationError("Invalid or expired password reset token")
        
        # Check if token is expired
        if user.password_reset_expires_at and user.password_reset_expires_at < datetime.utcnow():
            # Clear expired token
            await self.repository.clear_password_reset_token(user.id)
            raise ValidationError("Password reset token has expired. Please request a new one.")
        
        # Validate password strength
        self.validate_password_strength(new_password)
        
        # Hash new password
        hashed_password = self.hash_password(new_password)
        
        # Update password and clear reset token
        await self.repository.update_user(
            user.id,
            hashed_password=hashed_password,
            password_reset_token=None,
            password_reset_expires_at=None,
        )
        
        logger.info(f"Password reset confirmed for user {user.id} ({user.email})")

    async def send_verification_email(self, user_id: str, email: str, firm_id: str, frontend_url: str) -> None:
        """
        Send email verification email to user.

        Args:
            user_id: User ID
            email: User email address
            firm_id: Firm ID for the notification
            frontend_url: Frontend base URL for verification link

        Raises:
            NotFoundError: If user not found
        """
        import secrets
        from api_core.services.notifications_service import get_notifications_service
        from api_core.models.notifications import NotificationCreateRequest
        
        # Generate secure verification token
        verification_token = secrets.token_urlsafe(32)
        
        # Store token in database
        await self.repository.set_email_verification_token(user_id, verification_token)
        
        # Create verification link
        verification_link = f"{frontend_url}/auth/verify-email?token={verification_token}"
        
        # Create email content
        subject = "Verify your email address"
        message = f"""
Hello,

Thank you for signing up! Please verify your email address by clicking the link below:

{verification_link}

This link will expire in 24 hours.

If you didn't create an account, please ignore this email.

Best regards,
LexiqAI Team
        """.strip()
        
        # Send email via notifications service
        notifications_service = get_notifications_service(self.repository.session)
        await notifications_service.create_notification(
            NotificationCreateRequest(
                firm_id=firm_id,
                channel="email",
                to=email,
                subject=subject,
                message=message,
                idempotency_key=f"email_verification_{user_id}_{verification_token[:16]}",
            )
        )
        
        logger.info(f"Verification email sent to {email} for user {user_id}")

    async def verify_email_token(self, token: str) -> bool:
        """
        Verify email verification token.

        Args:
            token: Email verification token

        Returns:
            True if token is valid and email is verified

        Raises:
            ValidationError: If token is invalid
            NotFoundError: If user not found
        """
        # Get user by verification token
        user = await self.repository.get_by_verification_token(token)
        if not user:
            raise ValidationError("Invalid or expired verification token")
        
        # Check if already verified
        if user.is_verified:
            # Clear the token since it's already been used
            await self.repository.clear_email_verification_token(user.id)
            return True
        
        # Verify email
        await self.repository.verify_email(user.id)
        
        # Clear the verification token
        await self.repository.clear_email_verification_token(user.id)
        
        logger.info(f"Email verified for user {user.id} ({user.email})")
        return True


def get_auth_service(session: AsyncSession) -> AuthService:
    """
    Get an AuthService instance.

    Args:
        session: Database session

    Returns:
        AuthService instance
    """
    return AuthService(session)
