"""Base schemas used across the identity module."""

import uuid
from datetime import datetime
from typing import Generic, TypeVar, Optional

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class TimestampedSchema(BaseSchema):
    """Schema with timestamp fields for audit and tracking."""

    created_at: datetime
    updated_at: Optional[datetime] = None


class UUIDSchema(TimestampedSchema):
    """Schema with UUID primary key."""

    id: uuid.UUID


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response format."""

    items: list[T]
    total: int
    limit: int
    offset: int
