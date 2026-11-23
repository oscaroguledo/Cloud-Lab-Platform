"""Permission service: business logic for permission management."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_structured_logger
from modules.identity.models.permission import Permission
from modules.identity.services.base import BaseService

logger = get_structured_logger(__name__)


class PermissionService(BaseService[Permission]):
    """Service for permission operations: CRUD and scope checking."""

    def __init__(self):
        super().__init__(Permission)

    async def get_by_resource_action(
        self, db: AsyncSession, resource: str, action: str
    ) -> Optional[Permission]:
        """Fetch a permission by resource and action."""
        result = await db.execute(
            select(Permission).where(
                Permission.resource == resource, Permission.action == action
            )
        )
        return result.scalar_one_or_none()

    async def check_scope(self, db: AsyncSession, scopes: list[str], required: str) -> bool:
        """Check if required scope is in the list of scopes."""
        return required in scopes

    async def get_resource_actions(self, db: AsyncSession, resource: str) -> list[Permission]:
        """Fetch all permissions for a resource."""
        result = await db.execute(select(Permission).where(Permission.resource == resource))
        return result.scalars().all()

    async def seed_default_permissions(self, db: AsyncSession) -> None:
        """Seed default system permissions."""
        defaults = [
            # User management
            ("users:read", "user", "read", "Read user information"),
            ("users:write", "user", "write", "Create and update users"),
            ("users:delete", "user", "delete", "Delete users"),
            # Organization management
            ("org:read", "organization", "read", "Read organization info"),
            ("org:write", "organization", "write", "Update organization"),
            ("org:manage", "organization", "manage", "Full organization control"),
            # Role management
            ("roles:read", "role", "read", "Read roles"),
            ("roles:write", "role", "write", "Create and update roles"),
            ("roles:delete", "role", "delete", "Delete roles"),
            # Permission management
            ("permissions:read", "permission", "read", "Read permissions"),
            ("permissions:write", "permission", "write", "Manage permissions"),
        ]

        for name, resource, action, description in defaults:
            exists = await self.get_by_resource_action(db, resource, action)
            if not exists:
                await self.create(
                    db,
                    name=name,
                    resource=resource,
                    action=action,
                    description=description,
                )
                logger.info("Default permission seeded", name=name)
