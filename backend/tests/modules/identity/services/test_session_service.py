"""
Tests for SessionService: session management, revocation, cleanup.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from modules.identity.services.session import SessionService


@pytest.mark.asyncio
@pytest.mark.db
class TestSessionService:
    """Test SessionService operations."""

    async def test_create_session(
        self, async_session: AsyncSession, test_user, session_service: SessionService
    ):
        """Test creating a new session."""
        session = await session_service.create_session(
            async_session,
            test_user.id,
            device_hash="device123",
            user_agent="Mozilla/5.0",
            ip_address="192.168.1.1",
        )

        assert session is not None
        assert session.user_id == test_user.id
        assert session.is_active is True
        assert session.device_hash == "device123"

    async def test_get_active_session(
        self, async_session: AsyncSession, test_session, session_service: SessionService
    ):
        """Test retrieving active session."""
        session = await session_service.get_active_session(async_session, test_session.id)
        assert session is not None
        assert session.id == test_session.id

    async def test_get_inactive_session_returns_none(
        self, async_session: AsyncSession, test_session, session_service: SessionService
    ):
        """Test that inactive session is not returned."""
        # Revoke session
        test_session.is_active = False
        await async_session.flush()

        session = await session_service.get_active_session(async_session, test_session.id)
        assert session is None

    async def test_list_user_sessions(
        self, async_session: AsyncSession, test_user, test_session, session_service: SessionService
    ):
        """Test listing user's sessions."""
        sessions, total = await session_service.list_user_sessions(async_session, test_user.id)
        assert len(sessions) >= 1
        assert total >= 1

    async def test_list_active_user_sessions(
        self, async_session: AsyncSession, test_user, session_service: SessionService
    ):
        """Test listing active sessions for user."""
        # Create a session
        await session_service.create_session(async_session, test_user.id)

        sessions = await session_service.list_active_user_sessions(async_session, test_user.id)
        assert len(sessions) >= 1

    async def test_update_activity(
        self, async_session: AsyncSession, test_session, session_service: SessionService
    ):
        """Test updating session activity timestamp."""
        from datetime import UTC, datetime

        old_activity = test_session.last_activity_at
        await session_service.update_activity(async_session, test_session)
        await async_session.refresh(test_session)

        assert test_session.last_activity_at is not None
        assert test_session.last_activity_at > (old_activity or datetime.now(UTC))

    async def test_revoke_session(
        self, async_session: AsyncSession, test_session, session_service: SessionService
    ):
        """Test revoking a session."""
        await session_service.revoke_session(
            async_session, test_session, reason="User logout"
        )
        await async_session.refresh(test_session)

        assert test_session.is_active is False
        assert test_session.revoked_at is not None
        assert test_session.revoke_reason == "User logout"

    async def test_revoke_all_user_sessions(
        self, async_session: AsyncSession, test_user, session_service: SessionService
    ):
        """Test revoking all sessions for a user."""
        # Create multiple sessions
        await session_service.create_session(async_session, test_user.id)
        await session_service.create_session(async_session, test_user.id)

        count = await session_service.revoke_all_user_sessions(
            async_session, test_user.id, reason="Security event"
        )

        assert count >= 1

        # Verify all are revoked
        sessions = await session_service.list_active_user_sessions(async_session, test_user.id)
        assert len(sessions) == 0
