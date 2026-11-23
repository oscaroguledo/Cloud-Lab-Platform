"""Session service: business logic for session and authentication state management."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.logging import get_structured_logger
from modules.identity.models.session import UserSession
from modules.identity.services.base import BaseService

logger = get_structured_logger(__name__)


class SessionService(BaseService[UserSession]):
    """Service for session operations: creation, validation, revocation."""

    def __init__(self):
        super().__init__(UserSession)

    async def create_session(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        device_hash: Optional[str] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> UserSession:
        """Create a new user session."""
        settings = get_settings()
        expires_at = datetime.now(UTC) + timedelta(
            days=settings.refresh_token_expire_days
        )

        session = await self.create(
            db,
            user_id=user_id,
            device_hash=device_hash,
            user_agent=user_agent,
            ip_address=ip_address,
            is_active=True,
            expires_at=expires_at,
            last_activity_at=datetime.now(UTC),
        )
        logger.info("Session created", user_id=user_id, session_id=session.id)
        return session

    async def get_active_session(
        self, db: AsyncSession, session_id: uuid.UUID
    ) -> Optional[UserSession]:
        """Fetch an active session that hasn't expired."""
        result = await db.execute(
            select(UserSession).where(
                UserSession.id == session_id,
                UserSession.is_active == True,
                UserSession.expires_at > datetime.now(UTC),
            )
        )
        return result.scalar_one_or_none()

    async def list_user_sessions(
        self, db: AsyncSession, user_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> tuple[list[UserSession], int]:
        """Fetch all sessions for a user."""
        return await self.list(db, limit=limit, offset=offset, user_id=user_id)

    async def list_active_user_sessions(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> list[UserSession]:
        """Fetch all active sessions for a user."""
        result = await db.execute(
            select(UserSession).where(
                UserSession.user_id == user_id,
                UserSession.is_active == True,
                UserSession.expires_at > datetime.now(UTC),
            )
        )
        return result.scalars().all()

    async def update_activity(self, db: AsyncSession, session: UserSession) -> UserSession:
        """Update last activity timestamp."""
        session.last_activity_at = datetime.now(UTC)
        await db.flush()
        return session

    async def revoke_session(
        self, db: AsyncSession, session: UserSession, reason: Optional[str] = None
    ) -> UserSession:
        """Revoke a session (logout)."""
        session.is_active = False
        session.revoked_at = datetime.now(UTC)
        session.revoke_reason = reason
        await db.flush()
        logger.info("Session revoked", session_id=session.id, reason=reason)
        return session

    async def revoke_all_user_sessions(
        self, db: AsyncSession, user_id: uuid.UUID, reason: Optional[str] = None
    ) -> int:
        """Revoke all sessions for a user."""
        from sqlalchemy import update

        stmt = (
            update(UserSession)
            .where(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.is_active == True,
                )
            )
            .values(
                is_active=False,
                revoked_at=datetime.now(UTC),
                revoke_reason=reason,
            )
        )
        result = await db.execute(stmt)
        await db.flush()
        count = result.rowcount
        logger.info("All user sessions revoked", user_id=user_id, count=count, reason=reason)
        return count

    async def cleanup_expired(self, db: AsyncSession) -> int:
        """Delete expired sessions. Returns count deleted."""
        from sqlalchemy import delete

        stmt = delete(UserSession).where(UserSession.expires_at < datetime.now(UTC))
        result = await db.execute(stmt)
        await db.flush()
        count = result.rowcount
        logger.info("Expired sessions cleaned up", count=count)
        return count

    async def cleanup_revoked(self, db: AsyncSession, days: int = 30) -> int:
        """Delete revoked sessions older than N days. Returns count deleted."""
        from sqlalchemy import delete

        cutoff = datetime.now(UTC) - timedelta(days=days)
        stmt = delete(UserSession).where(
            and_(
                UserSession.is_active == False,
                UserSession.revoked_at.isnot(None),
                UserSession.revoked_at < cutoff,
            )
        )
        result = await db.execute(stmt)
        await db.flush()
        count = result.rowcount
        logger.info("Old revoked sessions cleaned up", count=count, days=days)
        return count
