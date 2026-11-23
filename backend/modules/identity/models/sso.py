"""SSO/OAuth providers: external authentication integrations."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Optional

from sqlalchemy import ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.database.engine import GUID, UTCDateTime, uuid7
from modules.identity.models.base import CHAR_LENGTH, Base, enum_check, ref, table_args


class SSOProvider(StrEnum):
    """Supported OAuth/SSO providers."""

    GOOGLE = "google"
    GITHUB = "github"
    MICROSOFT = "microsoft"
    OKTA = "okta"
    AUTH0 = "auth0"


class SSOConnection(Base):
    """External SSO provider connection for a user."""

    __tablename__ = "sso_connections"
    __table_args__ = table_args(
        ForeignKey(ref("users.id"), ondelete="CASCADE", name="sso_connections_user_id_fkey"),
        Index("idx_sso_connections_provider_id", "provider", "provider_user_id"),
        Index("idx_sso_connections_user", "user_id"),
        enum_check("provider", SSOProvider, "sso_connections_provider_check"),
    )

    # Identification
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid7)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID())

    # Provider info
    provider: Mapped[SSOProvider] = mapped_column(String(50))
    provider_user_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    provider_email: Mapped[str] = mapped_column(String(CHAR_LENGTH))

    # OAuth tokens (encrypted at rest)
    access_token: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    refresh_token: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    id_token: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime(), nullable=True)

    # Connection metadata
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime(), onupdate=func.now())
    last_used_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime(), nullable=True)

    # Additional data from provider (name, picture, etc.)
    profile_data: Mapped[dict] = mapped_column(JSONB, default=dict)
