"""
Tests for AuthService: authentication flows, MFA, SSO, password management.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import service as auth_service
from modules.identity.models.sso import SSOProvider
from modules.identity.models.token import TokenType
from modules.identity.services.auth import AuthService


@pytest.mark.asyncio
@pytest.mark.auth
class TestPasswordAuthentication:
    """Test password-based authentication."""

    async def test_authenticate_valid_password(
        self, async_session: AsyncSession, test_user, auth_service: AuthService
    ):
        """Test successful password authentication."""
        result = await auth_service.authenticate_password(
            async_session, test_user.email, "Test@123"
        )
        assert result is not None
        assert result.id == test_user.id
        assert result.failed_login_attempts == 0

    async def test_authenticate_invalid_password(
        self, async_session: AsyncSession, test_user, auth_service: AuthService
    ):
        """Test authentication with wrong password."""
        result = await auth_service.authenticate_password(
            async_session, test_user.email, "WrongPassword"
        )
        assert result is None

    async def test_authenticate_nonexistent_user(
        self, async_session: AsyncSession, auth_service: AuthService
    ):
        """Test authentication with nonexistent user."""
        result = await auth_service.authenticate_password(
            async_session, "nonexistent@example.com", "Password123"
        )
        assert result is None

    async def test_account_lockout_after_failed_attempts(
        self, async_session: AsyncSession, test_user, auth_service: AuthService
    ):
        """Test account lockout after 5 failed login attempts."""
        for _ in range(5):
            await auth_service.authenticate_password(
                async_session, test_user.email, "WrongPassword"
            )
            await async_session.refresh(test_user)

        # 6th attempt should fail (account locked)
        result = await auth_service.authenticate_password(
            async_session, test_user.email, "Test@123"
        )
        assert result is None
        assert test_user.locked_until is not None


@pytest.mark.asyncio
@pytest.mark.mfa
class TestMFAVerification:
    """Test multi-factor authentication."""

    async def test_verify_mfa_code_valid(self, test_user, auth_service: AuthService):
        """Test valid TOTP code verification."""
        # Generate a secret and store it
        secret = auth_service.totp.new_secret()
        test_user.mfa_secret = auth_service.box.seal(None, secret)
        test_user.mfa_enabled = True

        # Generate code for current time
        code = auth_service.totp.code(secret, auth_service.totp.step(None))

        # Verify
        result = await auth_service.verify_mfa_code(test_user, code)
        assert result is True

    async def test_verify_mfa_code_invalid(self, test_user, auth_service: AuthService):
        """Test invalid TOTP code."""
        secret = auth_service.totp.new_secret()
        test_user.mfa_secret = auth_service.box.seal(None, secret)
        test_user.mfa_enabled = True

        result = await auth_service.verify_mfa_code(test_user, "000000")
        assert result is False

    async def test_mfa_not_enabled(self, test_user, auth_service: AuthService):
        """Test MFA check when not enabled."""
        test_user.mfa_enabled = False
        result = await auth_service.require_mfa(test_user)
        assert result is False


@pytest.mark.asyncio
@pytest.mark.oauth
class TestSSOManagement:
    """Test Single Sign-On and OAuth management."""

    async def test_create_sso_connection(
        self, async_session: AsyncSession, test_user, auth_service: AuthService
    ):
        """Test creating SSO connection."""
        connection = await auth_service.create_sso_connection(
            async_session,
            test_user.id,
            SSOProvider.GOOGLE,
            provider_user_id="123456789",
            provider_email=test_user.email,
            profile_data={"name": "Test User"},
        )

        assert connection is not None
        assert connection.user_id == test_user.id
        assert connection.provider == "google"
        assert connection.provider_user_id == "123456789"

    async def test_get_sso_connection(
        self, async_session: AsyncSession, test_user, auth_service: AuthService
    ):
        """Test retrieving SSO connection."""
        # Create connection
        await auth_service.create_sso_connection(
            async_session,
            test_user.id,
            SSOProvider.GOOGLE,
            provider_user_id="123456789",
            provider_email=test_user.email,
        )

        # Retrieve
        connection = await auth_service.get_sso_connection(
            async_session, SSOProvider.GOOGLE, "123456789"
        )
        assert connection is not None
        assert connection.user_id == test_user.id

    async def test_get_nonexistent_sso_connection(
        self, async_session: AsyncSession, auth_service: AuthService
    ):
        """Test retrieving non-existent SSO connection."""
        connection = await auth_service.get_sso_connection(
            async_session, SSOProvider.GOOGLE, "nonexistent"
        )
        assert connection is None


@pytest.mark.asyncio
@pytest.mark.auth
class TestTokenGeneration:
    """Test JWT token generation and validation."""

    async def test_decode_token(self, test_user, test_session, auth_service: AuthService):
        """Test token decoding."""
        from core.config import get_settings

        settings = get_settings()
        token = await auth_service.create_access_token(settings, test_user, test_session)

        decoded = await auth_service.decode_token(token)
        assert decoded is not None
        assert decoded["sub"] == str(test_user.id)
        assert decoded["org"] == str(test_user.organization_id)

    async def test_decode_invalid_token(self, auth_service: AuthService):
        """Test decoding invalid token."""
        result = await auth_service.decode_token("invalid.token.here")
        assert result is None
