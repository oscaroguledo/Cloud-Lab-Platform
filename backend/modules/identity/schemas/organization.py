"""Organization request/response schemas."""

from typing import Optional

from pydantic import Field

from modules.identity.schemas.base import BaseSchema, UUIDSchema


class OrganizationCreate(BaseSchema):
    """Request to create a new organization."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    website: Optional[str] = Field(None, max_length=500)
    logo_url: Optional[str] = Field(None, max_length=500)


class OrganizationUpdate(BaseSchema):
    """Request to update an organization."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    website: Optional[str] = Field(None, max_length=500)
    logo_url: Optional[str] = Field(None, max_length=500)


class OrganizationResponse(UUIDSchema):
    """Response containing organization information."""

    name: str
    description: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    member_count: int = 0


class OrganizationListResponse(BaseSchema):
    """Response containing paginated organizations."""

    items: list[OrganizationResponse]
    total: int
    limit: int
    offset: int
