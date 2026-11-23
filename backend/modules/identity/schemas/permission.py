"""Permission request/response schemas."""

from typing import Optional

from pydantic import Field

from modules.identity.schemas.base import BaseSchema, UUIDSchema


class PermissionCreate(BaseSchema):
    """Request to create a new permission."""

    name: str = Field(..., min_length=1, max_length=255, description="Scope/resource name")
    description: Optional[str] = Field(None, max_length=1000)
    resource: str = Field(..., min_length=1, max_length=100, description="Resource identifier")
    action: str = Field(..., min_length=1, max_length=100, description="Action on resource")


class PermissionUpdate(BaseSchema):
    """Request to update a permission."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    resource: Optional[str] = Field(None, min_length=1, max_length=100)
    action: Optional[str] = Field(None, min_length=1, max_length=100)


class PermissionResponse(UUIDSchema):
    """Response containing permission information."""

    name: str
    description: Optional[str] = None
    resource: str
    action: str


class PermissionListResponse(BaseSchema):
    """Response containing paginated permissions."""

    items: list[PermissionResponse]
    total: int
    limit: int
    offset: int
