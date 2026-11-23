"""
Tests for UserService: user creation, password management, MFA.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from modules.identity.services.user import UserService


@pytest.mark.asyncio
@pytest.mark.db
class TestUserService:
    """Test UserService operations."""

    async def test_get_user_by_email(
        self, async_session: AsyncSession, test_user, user_service: UserService
    ):
        """Test fetching user by email."""
        user = await user_service.get_by_email(async_session, test_user.email)
        assert user is not None
        assert user.email == test_user.email

    async def test_get_nonexistent_user_by_email(
        self, async_session: AsyncSession, user_service: UserService
    ):
        """Test fetching non-existent user."""
        user = await user_service.get_by_email(async_session, "nonexistent@example.com")
        assert user is None

    async def test_create_user_with_password(
        self, async_session: AsyncSession, test_organization, test_role, user_service: UserService
    ):
        """Test creating user with password hashing."""
        import uuid

        user = await user_service.create_with_password(
            async_session,
            email="newuser@example.com",
            password="SecurePass123",
            first_name="New",
            last_name="User",
            organization_id=test_organization.id,
            role_id=test_role.id,
        )

        assert user is not None
        assert user.email == "newuser@example.com"
        assert user.password_hash != "SecurePass123"  # Should be hashed

    async def test_verify_password_correct(
        self, async_session: AsyncSession, test_user, user_service: UserService
    ):
        """Test password verification with correct password."""
        result = await user_service.verify_password(test_user, "Test@123")
        assert result is True

    async def test_verify_password_incorrect(
        self, async_session: AsyncSession, test_user, user_service: UserService
    ):
        """Test password verification with incorrect password."""
        result = await user_service.verify_password(test_user, "WrongPassword")
        assert result is False

    async def test_set_password(
        self, async_session: AsyncSession, test_user, user_service: UserService
    ):
        """Test changing user password."""
        await user_service.set_password(async_session, test_user, "NewSecure@123")
        await async_session.refresh(test_user)

        # Old password should not work
        result = await user_service.verify_password(test_user, "Test@123")
        assert result is False

        # New password should work
        result = await user_service.verify_password(test_user, "NewSecure@123")
        assert result is True

    async def test_activate_mfa(
        self, async_session: AsyncSession, test_user, user_service: UserService
    ):
        """Test enabling MFA for user."""
        from core.auth import service as auth_service

        secret = auth_service.totp.new_secret()
        await user_service.activate_mfa(async_session, test_user, secret)
        await async_session.refresh(test_user)

        assert test_user.mfa_enabled is True
        assert test_user.mfa_secret is not None

    async def test_disable_mfa(
        self, async_session: AsyncSession, test_user, user_service: UserService
    ):
        """Test disabling MFA for user."""
        from core.auth import service as auth_service

        # First enable it
        secret = auth_service.totp.new_secret()
        await user_service.activate_mfa(async_session, test_user, secret)

        # Then disable it
        await user_service.disable_mfa(async_session, test_user)
        await async_session.refresh(test_user)

        assert test_user.mfa_enabled is False
        assert test_user.mfa_secret is None
        assert test_user.mfa_recovery_hashes == []

    async def test_record_login(
        self, async_session: AsyncSession, test_user, user_service: UserService
    ):
        """Test recording login timestamp."""
        from datetime import UTC, datetime

        old_login = test_user.last_login
        await user_service.record_login(async_session, test_user)
        await async_session.refresh(test_user)

        assert test_user.last_login is not None
        assert test_user.last_login > (old_login or datetime.now(UTC))

    async def test_list_by_organization(
        self, async_session: AsyncSession, test_user, test_organization, user_service: UserService
    ):
        """Test listing users in organization."""
        users, total = await user_service.list_by_organization(
            async_session, test_organization.id
        )
        assert len(users) >= 1
        assert total >= 1
        assert any(u.id == test_user.id for u in users)
