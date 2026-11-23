"""Role request/response schemas."""

import uuid
from typing import Optional

from pydantic import Field

from modules.identity.schemas.base import BaseSchema, UUIDSchema


class RoleCreate(BaseSchema):
    """Request to create a new role."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    organization_id: uuid.UUID
    is_system: bool = Field(False, description="System roles cannot be deleted")
    permission_ids: list[uuid.UUID] = Field(default_factory=list)


class RoleUpdate(BaseSchema):
    """Request to update a role."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    permission_ids: Optional[list[uuid.UUID]] = None


class RoleResponse(UUIDSchema):
    """Response containing role information."""

    name: str
    description: Optional[str] = None
    organization_id: uuid.UUID
    is_system: bool
    member_count: int = 0
    permission_count: int = 0


class RoleDetailResponse(RoleResponse):
    """Response containing role with permissions."""

    permissions: list["PermissionResponse"] = []


class RoleListResponse(BaseSchema):
    """Response containing paginated roles."""

    items: list[RoleResponse]
    total: int
    limit: int
    offset: int
