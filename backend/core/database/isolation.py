"""Database isolation and scoping: multi-organization access control."""

import uuid
from sqlalchemy.ext.asyncio import AsyncSession


async def scope_to(db: AsyncSession, organization_id: uuid.UUID) -> None:
    """Scope the session to a specific organization for multi-tenant isolation.

    Sets the organization context in session info for automatic filtering
    of queries and audit log entries.
    """
    db.info["organization_id"] = organization_id


async def bypass(db: AsyncSession) -> None:
    """Bypass organization scoping for platform-wide operations (e.g., anonymous requests).

    Used for audit entries and operations that don't belong to any organization.
    """
    db.info["bypass_scoping"] = True
