"""Unit tests for AuthService."""

import pytest
import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from api_core.services.auth_service import AuthService, get_auth_service
from api_core.services.user_service import UserService, get_user_service
from api_core.exceptions import AuthenticationError, ValidationError, NotFoundError
from api_core.database.models import User, Firm


@pytest.fixture
async def auth_service(session: AsyncSession) -> AuthService:
    """Create AuthService instance for testing."""
    return get_auth_service(session)


@pytest.fixture
async def user_service(session: AsyncSession) -> UserService:
    """Create UserService instance for testing."""
    return get_user_service(session)


@pytest.fixture
async def test_firm(session: AsyncSession) -> Firm:
    """Create a test firm."""
    firm = Firm(
        id=str(uuid.uuid4()),
        name="Test Firm",
    )
    session.add(firm)
    await session.commit()
    await session.refresh(firm)
    return firm


@pytest.fixture
async def test_user(session: AsyncSession, auth_service: AuthService, test_firm: Firm) -> User:
    """Create a test user with password."""
    hashed_password = auth_service.hash_password("TestPassword123!")
    user = User(
        id=str(uuid.uuid4()),
        email="test@example.com",
        name="Test User",
        hashed_password=hashed_password,
        firm_id=test_firm.id,
        is_verified=True,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


class TestPasswordStrengthValidation:
    """Tests for password strength validation."""

    def test_valid_password(self, auth_service: AuthService):
        """Test that a valid password passes validation."""
        auth_service.validate_password_strength("ValidPass123!")

    def test_password_too_short(self, auth_service: AuthService):
        """Test that password shorter than 8 characters fails."""
        with pytest.raises(ValidationError, match="at least 8 characters"):
            auth_service.validate_password_strength("Short1!")

    def test_password_missing_uppercase(self, auth_service: AuthService):
        """Test that password without uppercase fails."""
        with pytest.raises(ValidationError, match="uppercase"):
            auth_service.validate_password_strength("lowercase123!")

    def test_password_missing_lowercase(self, auth_service: AuthService):
        """Test that password without lowercase fails."""
        with pytest.raises(ValidationError, match="lowercase"):
            auth_service.validate_password_strength("UPPERCASE123!")

    def test_password_missing_digit(self, auth_service: AuthService):
        """Test that password without digit fails."""
        with pytest.raises(ValidationError, match="digit"):
            auth_service.validate_password_strength("NoDigits!")

    def test_password_missing_special_char(self, auth_service: AuthService):
        """Test that password without special character fails."""
        with pytest.raises(ValidationError, match="special character"):
            auth_service.validate_password_strength("NoSpecial123")

    def test_empty_password(self, auth_service: AuthService):
        """Test that empty password fails."""
        with pytest.raises(ValidationError, match="required"):
            auth_service.validate_password_strength("")

    def test_none_password(self, auth_service: AuthService):
        """Test that None password fails."""
        with pytest.raises(ValidationError):
            auth_service.validate_password_strength(None)


class TestPasswordHashing:
    """Tests for password hashing and verification."""

    def test_hash_password(self, auth_service: AuthService):
        """Test that password hashing produces a hash."""
        password = "TestPassword123!"
        hashed = auth_service.hash_password(password)
        
        assert hashed is not None
        assert hashed != password
        assert len(hashed) > 0

    def test_hash_password_deterministic(self, auth_service: AuthService):
        """Test that same password produces different hashes (bcrypt salt)."""
        password = "TestPassword123!"
        hashed1 = auth_service.hash_password(password)
        hashed2 = auth_service.hash_password(password)
        
        # Bcrypt uses random salt, so hashes should be different
        assert hashed1 != hashed2

    def test_verify_password_correct(self, auth_service: AuthService):
        """Test that correct password verifies successfully."""
        password = "TestPassword123!"
        hashed = auth_service.hash_password(password)
        
        assert auth_service.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self, auth_service: AuthService):
        """Test that incorrect password fails verification."""
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        hashed = auth_service.hash_password(password)
        
        assert auth_service.verify_password(wrong_password, hashed) is False

    def test_verify_password_empty(self, auth_service: AuthService):
        """Test that empty password fails verification."""
        password = "TestPassword123!"
        hashed = auth_service.hash_password(password)
        
        assert auth_service.verify_password("", hashed) is False


class TestUserAuthentication:
    """Tests for user authentication."""

    @pytest.mark.asyncio
    async def test_authenticate_user_success(
        self, auth_service: AuthService, test_user: User
    ):
        """Test successful user authentication."""
        user_profile = await auth_service.authenticate_user(
            "test@example.com", "TestPassword123!"
        )
        
        assert user_profile is not None
        assert user_profile.email == "test@example.com"
        assert user_profile.id == test_user.id

    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(
        self, auth_service: AuthService, test_user: User
    ):
        """Test authentication with wrong password."""
        with pytest.raises(AuthenticationError, match="Invalid email or password"):
            await auth_service.authenticate_user(
                "test@example.com", "WrongPassword123!"
            )

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, auth_service: AuthService):
        """Test authentication with non-existent user."""
        with pytest.raises(AuthenticationError, match="Invalid email or password"):
            await auth_service.authenticate_user(
                "nonexistent@example.com", "TestPassword123!"
            )

    @pytest.mark.asyncio
    async def test_authenticate_user_no_password(
        self, session: AsyncSession, auth_service: AuthService, test_firm: Firm
    ):
        """Test authentication for OAuth-only user (no password)."""
        # Create OAuth-only user
        oauth_user = User(
            id=str(uuid.uuid4()),
            email="oauth@example.com",
            name="OAuth User",
            hashed_password=None,  # No password
            firm_id=test_firm.id,
            is_verified=True,
        )
        session.add(oauth_user)
        await session.commit()
        
        with pytest.raises(AuthenticationError, match="Invalid email or password"):
            await auth_service.authenticate_user(
                "oauth@example.com", "AnyPassword123!"
            )

    @pytest.mark.asyncio
    async def test_authenticate_user_account_locked(
        self, session: AsyncSession, auth_service: AuthService, test_user: User
    ):
        """Test authentication when account is locked."""
        # Lock the account
        test_user.locked_until = datetime.utcnow() + timedelta(minutes=30)
        test_user.failed_login_attempts = 5
        await session.commit()
        
        with pytest.raises(AuthenticationError, match="Account is locked"):
            await auth_service.authenticate_user(
                "test@example.com", "TestPassword123!"
            )

    @pytest.mark.asyncio
    async def test_authenticate_user_increments_failed_attempts(
        self, session: AsyncSession, auth_service: AuthService, test_user: User
    ):
        """Test that failed login increments failed attempts."""
        initial_attempts = test_user.failed_login_attempts
        
        # Try wrong password
        with pytest.raises(AuthenticationError):
            await auth_service.authenticate_user(
                "test@example.com", "WrongPassword123!"
            )
        
        # Check that failed attempts were incremented
        await session.refresh(test_user)
        assert test_user.failed_login_attempts == initial_attempts + 1

    @pytest.mark.asyncio
    async def test_authenticate_user_locks_after_max_attempts(
        self, session: AsyncSession, auth_service: AuthService, test_user: User
    ):
        """Test that account locks after 5 failed attempts."""
        # Set failed attempts to 4
        test_user.failed_login_attempts = 4
        await session.commit()
        
        # Try wrong password (5th attempt)
        with pytest.raises(AuthenticationError):
            await auth_service.authenticate_user(
                "test@example.com", "WrongPassword123!"
            )
        
        # Check that account is locked
        await session.refresh(test_user)
        assert test_user.failed_login_attempts == 5
        assert test_user.locked_until is not None
        assert test_user.locked_until > datetime.utcnow()

    @pytest.mark.asyncio
    async def test_authenticate_user_resets_attempts_on_success(
        self, session: AsyncSession, auth_service: AuthService, test_user: User
    ):
        """Test that successful login resets failed attempts."""
        # Set failed attempts
        test_user.failed_login_attempts = 3
        await session.commit()
        
        # Successful login
        await auth_service.authenticate_user(
            "test@example.com", "TestPassword123!"
        )
        
        # Check that attempts were reset
        await session.refresh(test_user)
        assert test_user.failed_login_attempts == 0
        assert test_user.locked_until is None


class TestEmailVerification:
    """Tests for email verification."""

    @pytest.mark.asyncio
    async def test_send_verification_email(
        self, session: AsyncSession, auth_service: AuthService, test_user: User
    ):
        """Test sending verification email."""
        # Clear existing verification token
        test_user.email_verification_token = None
        test_user.is_verified = False
        await session.commit()
        
        await auth_service.send_verification_email(
            user_id=test_user.id,
            email=test_user.email,
            firm_id=test_user.firm_id,
            frontend_url="http://localhost:3000",
        )
        
        # Check that token was set
        await session.refresh(test_user)
        assert test_user.email_verification_token is not None
        assert test_user.is_verified is False

    @pytest.mark.asyncio
    async def test_verify_email_token_success(
        self, session: AsyncSession, auth_service: AuthService, test_user: User
    ):
        """Test successful email verification."""
        # Set verification token
        token = "test_verification_token"
        test_user.email_verification_token = token
        test_user.is_verified = False
        await session.commit()
        
        await auth_service.verify_email_token(token)
        
        # Check that email is verified
        await session.refresh(test_user)
        assert test_user.is_verified is True
        assert test_user.email_verification_token is None
        assert test_user.email_verified_at is not None

    @pytest.mark.asyncio
    async def test_verify_email_token_invalid(
        self, auth_service: AuthService, test_user: User
    ):
        """Test email verification with invalid token."""
        with pytest.raises(ValidationError, match="Invalid or expired"):
            await auth_service.verify_email_token("invalid_token")

    @pytest.mark.asyncio
    async def test_verify_email_token_already_verified(
        self, session: AsyncSession, auth_service: AuthService, test_user: User
    ):
        """Test email verification when already verified."""
        test_user.is_verified = True
        test_user.email_verification_token = None
        await session.commit()
        
        # Should still work (idempotent)
        # But token should be invalid
        with pytest.raises(ValidationError, match="Invalid or expired"):
            await auth_service.verify_email_token("any_token")


class TestPasswordReset:
    """Tests for password reset."""

    @pytest.mark.asyncio
    async def test_request_password_reset(
        self, session: AsyncSession, auth_service: AuthService, test_user: User
    ):
        """Test requesting password reset."""
        await auth_service.request_password_reset(
            email=test_user.email,
            frontend_url="http://localhost:3000",
        )
        
        # Check that reset token was set
        await session.refresh(test_user)
        assert test_user.password_reset_token is not None
        assert test_user.password_reset_expires_at is not None
        assert test_user.password_reset_expires_at > datetime.utcnow()

    @pytest.mark.asyncio
    async def test_request_password_reset_nonexistent_user(
        self, auth_service: AuthService
    ):
        """Test password reset for non-existent user (should not reveal)."""
        # Should not raise error (security: don't reveal if user exists)
        await auth_service.request_password_reset(
            email="nonexistent@example.com",
            frontend_url="http://localhost:3000",
        )

    @pytest.mark.asyncio
    async def test_request_password_reset_oauth_user(
        self, session: AsyncSession, auth_service: AuthService, test_firm: Firm
    ):
        """Test password reset for OAuth-only user."""
        # Create OAuth-only user
        oauth_user = User(
            id=str(uuid.uuid4()),
            email="oauth@example.com",
            name="OAuth User",
            hashed_password=None,
            firm_id=test_firm.id,
        )
        session.add(oauth_user)
        await session.commit()
        
        # Should not raise error (security: don't reveal if user has password)
        await auth_service.request_password_reset(
            email="oauth@example.com",
            frontend_url="http://localhost:3000",
        )
        
        # Check that no token was set
        await session.refresh(oauth_user)
        assert oauth_user.password_reset_token is None

    @pytest.mark.asyncio
    async def test_confirm_password_reset_success(
        self, session: AsyncSession, auth_service: AuthService, test_user: User
    ):
        """Test successful password reset."""
        # Set reset token
        token = "test_reset_token"
        test_user.password_reset_token = token
        test_user.password_reset_expires_at = datetime.utcnow() + timedelta(hours=24)
        old_password_hash = test_user.hashed_password
        await session.commit()
        
        new_password = "NewPassword123!"
        await auth_service.confirm_password_reset(token, new_password)
        
        # Check that password was changed
        await session.refresh(test_user)
        assert test_user.hashed_password != old_password_hash
        assert test_user.password_reset_token is None
        assert test_user.password_reset_expires_at is None
        
        # Verify new password works
        assert auth_service.verify_password(new_password, test_user.hashed_password)

    @pytest.mark.asyncio
    async def test_confirm_password_reset_invalid_token(
        self, auth_service: AuthService
    ):
        """Test password reset with invalid token."""
        with pytest.raises(ValidationError, match="Invalid or expired"):
            await auth_service.confirm_password_reset("invalid_token", "NewPassword123!")

    @pytest.mark.asyncio
    async def test_confirm_password_reset_expired_token(
        self, session: AsyncSession, auth_service: AuthService, test_user: User
    ):
        """Test password reset with expired token."""
        # Set expired token
        token = "expired_token"
        test_user.password_reset_token = token
        test_user.password_reset_expires_at = datetime.utcnow() - timedelta(hours=1)
        await session.commit()
        
        with pytest.raises(ValidationError, match="expired"):
            await auth_service.confirm_password_reset(token, "NewPassword123!")

    @pytest.mark.asyncio
    async def test_confirm_password_reset_weak_password(
        self, session: AsyncSession, auth_service: AuthService, test_user: User
    ):
        """Test password reset with weak password."""
        # Set reset token
        token = "test_reset_token"
        test_user.password_reset_token = token
        test_user.password_reset_expires_at = datetime.utcnow() + timedelta(hours=24)
        await session.commit()
        
        # Use a password that's 8+ characters but missing required elements (uppercase, digit, special)
        # This will trigger "Password must contain" error instead of length error
        with pytest.raises(ValidationError, match="Password must contain"):
            await auth_service.confirm_password_reset(token, "weakpassword")

