"""Token request/response schemas."""

import uuid
from typing import Optional

from pydantic import Field

from modules.identity.schemas.base import BaseSchema, UUIDSchema


class OneTimeTokenCreate(BaseSchema):
    """Request to create a one-time token."""

    user_id: uuid.UUID
    token_type: str = Field(..., description="Purpose of the token")
    email: Optional[str] = Field(None, description="Email being verified, if applicable")
    metadata: dict = Field(default_factory=dict, description="Additional context")


class OneTimeTokenResponse(UUIDSchema):
    """Response containing token information."""

    user_id: uuid.UUID
    token_type: str
    email: Optional[str] = None
    attempts: int
    max_attempts: int
    expires_at: str
    used_at: Optional[str] = None


class TokenVerifyRequest(BaseSchema):
    """Request to verify a one-time token."""

    token: str = Field(..., description="The plaintext token from the email")
    token_type: str = Field(..., description="Expected token type")


class TokenVerifyResponse(BaseSchema):
    """Response after token verification."""

    success: bool
    message: str
    remaining_attempts: int
