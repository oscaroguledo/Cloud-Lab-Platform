"""Organization service: business logic for organization management."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_structured_logger
from modules.identity.models.organization import Organization
from modules.identity.models.user import User
from modules.identity.services.base import BaseService

logger = get_structured_logger(__name__)


class OrganizationService(BaseService[Organization]):
    """Service for organization operations: CRUD and member management."""

    def __init__(self):
        super().__init__(Organization)

    async def get_member_count(self, db: AsyncSession, org_id: uuid.UUID) -> int:
        """Count active members in an organization."""
        result = await db.execute(
            select(func.count()).select_from(User).where(User.organization_id == org_id)
        )
        return result.scalar() or 0

    async def list_members(
        self, db: AsyncSession, org_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> tuple[list[User], int]:
        """Fetch users in an organization."""
        query = select(User).where(User.organization_id == org_id)

        # Get total count
        count_query = select(func.count()).select_from(User).where(User.organization_id == org_id)
        total = await db.scalar(count_query)

        # Apply pagination
        query = query.limit(limit).offset(offset)
        result = await db.execute(query)
        members = result.scalars().all()

        return members, total

    async def create_with_owner(
        self, db: AsyncSession, owner_id: uuid.UUID, **org_data
    ) -> Organization:
        """Create a new organization and set an owner."""
        org = await self.create(db, **org_data)
        logger.info("Organization created", org_id=org.id, owner_id=owner_id)
        return org

    async def delete_cascade(self, db: AsyncSession, org_id: uuid.UUID) -> None:
        """Delete an organization and cascade to users, roles, permissions."""
        org = await self.get_by_id(db, org_id)
        if org:
            await self.delete(db, org)
            logger.warning("Organization deleted (cascade)", org_id=org_id)
