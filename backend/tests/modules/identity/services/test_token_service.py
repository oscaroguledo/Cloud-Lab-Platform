"""
Tests for TokenService: one-time token generation, verification, cleanup.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from modules.identity.models.token import TokenType
from modules.identity.services.token import TokenService


@pytest.mark.asyncio
@pytest.mark.db
class TestTokenService:
    """Test TokenService operations."""

    async def test_create_token(
        self, async_session: AsyncSession, test_user, token_service: TokenService
    ):
        """Test creating a one-time token."""
        token, plaintext = await token_service.create_token(
            async_session,
            test_user.id,
            TokenType.EMAIL_VERIFICATION,
            ttl_minutes=15,
        )

        assert token is not None
        assert plaintext is not None
        assert token.user_id == test_user.id
        assert token.token_type == "email_verification"
        assert token.attempts == 0

    async def test_verify_token_valid(
        self, async_session: AsyncSession, test_user, token_service: TokenService
    ):
        """Test verifying a valid token."""
        token, plaintext = await token_service.create_token(
            async_session,
            test_user.id,
            TokenType.PASSWORD_RESET,
        )

        verified = await token_service.verify_token(
            async_session, plaintext, TokenType.PASSWORD_RESET
        )
        assert verified is not None
        assert verified.id == token.id

    async def test_verify_token_invalid(
        self, async_session: AsyncSession, token_service: TokenService
    ):
        """Test verifying invalid token."""
        result = await token_service.verify_token(
            async_session, "invalid-token-hash", TokenType.PASSWORD_RESET
        )
        assert result is None

    async def test_verify_token_wrong_type(
        self, async_session: AsyncSession, test_user, token_service: TokenService
    ):
        """Test verifying token with wrong type."""
        token, plaintext = await token_service.create_token(
            async_session,
            test_user.id,
            TokenType.PASSWORD_RESET,
        )

        # Try to verify as different type
        result = await token_service.verify_token(
            async_session, plaintext, TokenType.EMAIL_VERIFICATION
        )
        assert result is None

    async def test_mark_token_used(
        self, async_session: AsyncSession, test_user, token_service: TokenService
    ):
        """Test marking token as used."""
        token, plaintext = await token_service.create_token(
            async_session,
            test_user.id,
            TokenType.EMAIL_VERIFICATION,
        )

        await token_service.mark_used(async_session, token)
        await async_session.refresh(token)

        assert token.used_at is not None

    async def test_increment_attempts(
        self, async_session: AsyncSession, test_user, token_service: TokenService
    ):
        """Test incrementing failed attempts."""
        token, plaintext = await token_service.create_token(
            async_session,
            test_user.id,
            TokenType.EMAIL_VERIFICATION,
        )

        for i in range(3):
            await token_service.increment_attempts(async_session, token)
            await async_session.refresh(token)
            assert token.attempts == i + 1

    async def test_verify_token_max_attempts_exceeded(
        self, async_session: AsyncSession, test_user, token_service: TokenService
    ):
        """Test token verification fails after max attempts."""
        token, plaintext = await token_service.create_token(
            async_session,
            test_user.id,
            TokenType.EMAIL_VERIFICATION,
            ttl_minutes=15,
        )

        # Exceed max attempts
        for _ in range(token.max_attempts):
            await token_service.increment_attempts(async_session, token)

        # Verification should fail
        result = await token_service.verify_token(
            async_session, plaintext, TokenType.EMAIL_VERIFICATION
        )
        assert result is None

    async def test_cleanup_expired_tokens(
        self, async_session: AsyncSession, test_user, token_service: TokenService
    ):
        """Test cleanup of expired tokens."""
        from datetime import UTC, datetime, timedelta

        # Create expired token
        token, _ = await token_service.create_token(
            async_session,
            test_user.id,
            TokenType.PASSWORD_RESET,
            ttl_minutes=-60,  # Expired 60 minutes ago
        )

        count = await token_service.cleanup_expired(async_session)
        assert count >= 1
