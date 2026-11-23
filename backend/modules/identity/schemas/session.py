"""Session request/response schemas."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import Field

from modules.identity.schemas.base import BaseSchema, UUIDSchema


class SessionCreate(BaseSchema):
    """Request to create a new session."""

    user_id: uuid.UUID
    device_hash: Optional[str] = Field(None, description="Browser fingerprint for tracking")
    user_agent: Optional[str] = Field(None, description="User agent string")
    ip_address: Optional[str] = Field(None, description="Client IP address")


class SessionUpdate(BaseSchema):
    """Request to update a session."""

    is_active: Optional[bool] = None
    last_activity_at: Optional[str] = None


class SessionResponse(UUIDSchema):
    """Response containing session information."""

    user_id: uuid.UUID
    device_hash: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    is_active: bool
    last_activity_at: Optional[str] = None
    expires_at: str


class SessionListResponse(BaseSchema):
    """Response containing paginated sessions."""

    items: list[SessionResponse]
    total: int
    limit: int
    offset: int


class SessionRevokeRequest(BaseSchema):
    """Request to revoke a session."""

    reason: Optional[str] = Field(None, max_length=255)


class SessionLogoutRequest(BaseSchema):
    """Request to logout (revoke current session)."""

    all_sessions: bool = Field(False, description="Logout all sessions if True")


class SessionOut(BaseSchema):
    id: uuid.UUID
    current: bool  # the session making this request
    ip: str | None
    user_agent: str | None
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime
