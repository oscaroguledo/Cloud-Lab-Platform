"""User request/response schemas."""

import uuid
from typing import Optional

from pydantic import EmailStr, Field

from modules.identity.schemas.base import BaseSchema, UUIDSchema


class UserCreate(BaseSchema):
    """Request to create a new user."""

    email: EmailStr = Field(..., description="User email address")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8, description="User password")
    organization_id: uuid.UUID
    role_id: uuid.UUID


class UserUpdate(BaseSchema):
    """Request to update a user."""

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    bio: Optional[str] = Field(None, max_length=1000)
    timezone: Optional[str] = Field(None, max_length=64)


class UserResponse(UUIDSchema):
    """Response containing user information."""

    email: str
    first_name: str
    last_name: str
    organization_id: uuid.UUID
    role_id: uuid.UUID
    account_status: str
    verification_status: str
    phone: Optional[str] = None
    timezone: Optional[str] = None
    mfa_enabled: bool
    last_login: Optional[str] = None


class UserListResponse(BaseSchema):
    """Response containing paginated users."""

    items: list[UserResponse]
    total: int
    limit: int
    offset: int
