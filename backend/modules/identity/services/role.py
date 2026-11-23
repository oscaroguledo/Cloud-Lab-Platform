"""Role service: business logic for role and permission management."""

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_structured_logger
from modules.identity.models.permission import Permission
from modules.identity.models.role import Role
from modules.identity.models.user import User
from modules.identity.services.base import BaseService

logger = get_structured_logger(__name__)


class RoleService(BaseService[Role]):
    """Service for role operations: CRUD, permissions, and member tracking."""

    def __init__(self):
        super().__init__(Role)

    async def get_by_name(self, db: AsyncSession, name: str, org_id: uuid.UUID) -> Optional[Role]:
        """Fetch a role by name within an organization."""
        result = await db.execute(
            select(Role).where(Role.name == name, Role.organization_id == org_id)
        )
        return result.scalar_one_or_none()

    async def get_member_count(self, db: AsyncSession, role_id: uuid.UUID) -> int:
        """Count users with this role."""
        result = await db.execute(
            select(func.count()).select_from(User).where(User.role_id == role_id)
        )
        return result.scalar() or 0

    async def list_by_organization(
        self, db: AsyncSession, org_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> tuple[list[Role], int]:
        """Fetch roles in an organization."""
        return await self.list(db, limit=limit, offset=offset, organization_id=org_id)

    async def add_permission(
        self, db: AsyncSession, role: Role, permission: Permission
    ) -> Role:
        """Add a permission to a role."""
        if permission not in role.permissions:
            role.permissions.append(permission)
            await db.flush()
            logger.info("Permission added to role", role_id=role.id, permission_id=permission.id)
        return role

    async def remove_permission(
        self, db: AsyncSession, role: Role, permission: Permission
    ) -> Role:
        """Remove a permission from a role."""
        if permission in role.permissions:
            role.permissions.remove(permission)
            await db.flush()
            logger.info(
                "Permission removed from role", role_id=role.id, permission_id=permission.id
            )
        return role

    async def set_permissions(
        self, db: AsyncSession, role: Role, permissions: list[Permission]
    ) -> Role:
        """Replace all permissions for a role."""
        role.permissions = permissions
        await db.flush()
        logger.info("Role permissions updated", role_id=role.id, count=len(permissions))
        return role

    async def prevent_delete_if_has_members(
        self, db: AsyncSession, role_id: uuid.UUID
    ) -> bool:
        """Check if role can be safely deleted."""
        count = await self.get_member_count(db, role_id)
        if count > 0:
            logger.warning("Cannot delete role with members", role_id=role_id, members=count)
            return False
        return True
