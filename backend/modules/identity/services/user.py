"""User service: business logic for user management."""

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import service as auth_service
from core.logging import get_structured_logger
from modules.identity.models.user import User
from modules.identity.services.base import BaseService

logger = get_structured_logger(__name__)


class UserService(BaseService[User]):
    """Service for user operations: creation, updates, queries, and authentication."""

    def __init__(self):
        super().__init__(User)

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """Fetch a user by email address."""
        result = await db.execute(select(User).where(User.email == email.lower()))
        return result.scalar_one_or_none()

    async def create_with_password(
        self, db: AsyncSession, email: str, password: str, **user_data
    ) -> User:
        """Create a new user with hashed password."""
        # Hash password
        password_hash = await auth_service.passwords.hash(password)

        # Create user
        user = await self.create(
            db,
            email=email.lower(),
            password_hash=password_hash,
            **user_data,
        )
        logger.info("User created", user_id=user.id, email=email)
        return user

    async def verify_password(self, user: User, password: str) -> bool:
        """Verify a user's password."""
        return await auth_service.passwords.verify(password, user.password_hash)

    async def set_password(self, db: AsyncSession, user: User, new_password: str) -> User:
        """Update a user's password."""
        user.password_hash = await auth_service.passwords.hash(new_password)
        user.must_change_password = False
        await db.flush()
        logger.info("Password changed", user_id=user.id)
        return user

    async def activate_mfa(self, db: AsyncSession, user: User, secret: str) -> User:
        """Enable two-factor authentication for a user."""
        user.mfa_secret = auth_service.box.seal(user, secret)
        user.mfa_enabled = True
        await db.flush()
        logger.info("MFA enabled", user_id=user.id)
        return user

    async def disable_mfa(self, db: AsyncSession, user: User) -> User:
        """Disable two-factor authentication for a user."""
        user.mfa_secret = None
        user.mfa_enabled = False
        user.mfa_last_step = None
        user.mfa_recovery_hashes = []
        await db.flush()
        logger.info("MFA disabled", user_id=user.id)
        return user

    async def record_login(self, db: AsyncSession, user: User) -> User:
        """Update last login timestamp."""
        from datetime import UTC, datetime

        user.last_login = datetime.now(UTC)
        await db.flush()
        return user

    async def list_by_organization(
        self, db: AsyncSession, organization_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> tuple[list[User], int]:
        """Fetch users in an organization."""
        return await self.list(
            db, limit=limit, offset=offset, organization_id=organization_id
        )
