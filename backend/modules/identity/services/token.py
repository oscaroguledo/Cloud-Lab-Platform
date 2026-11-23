"""Token service: business logic for one-time tokens."""

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import service as auth_service
from core.config import get_settings
from core.logging import get_structured_logger
from modules.identity.models.token import OneTimeToken, TokenType
from modules.identity.services.base import BaseService

logger = get_structured_logger(__name__)


class TokenService(BaseService[OneTimeToken]):
    """Service for one-time token operations: creation, verification, cleanup."""

    def __init__(self):
        super().__init__(OneTimeToken)

    async def create_token(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        token_type: TokenType,
        ttl_minutes: int = 15,
        email: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> tuple[OneTimeToken, str]:
        """Create a new one-time token and return both the model and plaintext token.

        Returns: (token_model, plaintext_token_for_email)
        """
        settings = get_settings()

        # Generate token
        plaintext = auth_service.email_tokens.new()
        token_hash = auth_service.email_tokens.hash(plaintext)

        # Create record
        token = await self.create(
            db,
            user_id=user_id,
            token_hash=token_hash,
            token_type=token_type.value,
            email=email,
            expires_at=datetime.now(UTC) + timedelta(minutes=ttl_minutes),
            metadata=metadata or {},
        )

        logger.info(
            "Token created",
            user_id=user_id,
            token_type=token_type,
            expires_in_minutes=ttl_minutes,
        )

        return token, plaintext

    async def verify_token(
        self, db: AsyncSession, plaintext: str, token_type: TokenType
    ) -> Optional[OneTimeToken]:
        """Verify a token: check hash, type, expiry, and attempts."""
        token_hash = auth_service.email_tokens.hash(plaintext)

        # Find token
        result = await db.execute(
            select(OneTimeToken).where(
                OneTimeToken.token_hash == token_hash,
                OneTimeToken.token_type == token_type.value,
            )
        )
        token = result.scalar_one_or_none()

        if not token:
            logger.warning("Token not found or wrong type", token_type=token_type)
            return None

        # Check expiry
        if token.expires_at < datetime.now(UTC):
            logger.warning("Token expired", token_id=token.id, token_type=token_type)
            return None

        # Check already used
        if token.used_at:
            logger.warning("Token already used", token_id=token.id, token_type=token_type)
            return None

        # Check attempts
        if token.attempts >= token.max_attempts:
            logger.warning("Too many attempts", token_id=token.id, token_type=token_type)
            return None

        return token

    async def mark_used(self, db: AsyncSession, token: OneTimeToken) -> OneTimeToken:
        """Mark a token as used."""
        token.used_at = datetime.now(UTC)
        await db.flush()
        logger.info("Token marked used", token_id=token.id)
        return token

    async def increment_attempts(self, db: AsyncSession, token: OneTimeToken) -> OneTimeToken:
        """Increment failed attempt counter."""
        token.attempts += 1
        await db.flush()
        return token

    async def cleanup_expired(self, db: AsyncSession) -> int:
        """Delete expired tokens. Returns count deleted."""
        from sqlalchemy import delete

        stmt = delete(OneTimeToken).where(OneTimeToken.expires_at < datetime.now(UTC))
        result = await db.execute(stmt)
        await db.flush()
        count = result.rowcount
        logger.info("Expired tokens cleaned up", count=count)
        return count

    async def cleanup_used(self, db: AsyncSession, days: int = 7) -> int:
        """Delete tokens marked used older than N days. Returns count deleted."""
        from sqlalchemy import delete

        cutoff = datetime.now(UTC) - timedelta(days=days)
        stmt = delete(OneTimeToken).where(
            OneTimeToken.used_at.isnot(None), OneTimeToken.used_at < cutoff
        )
        result = await db.execute(stmt)
        await db.flush()
        count = result.rowcount
        logger.info("Old used tokens cleaned up", count=count, days=days)
        return count
