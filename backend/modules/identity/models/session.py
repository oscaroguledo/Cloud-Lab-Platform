import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.engine import GUID, UTCDateTime, uuid7
from app.modules.identity.models.base import Base, ref, table_args

if TYPE_CHECKING:
    from app.modules.identity.models.user import User


class UserSession(Base):
    """One signed-in device; the refresh token carries the session id and a rotating ``jti``.
    Only ``current_jti`` is valid: an older one means replay, so the session is deleted."""

    __tablename__ = "sessions"
    __table_args__ = table_args(
        Index("idx_sessions_user_id", "user_id"),
        Index("idx_sessions_expires_at", "expires_at"),
    )

    # Common fields
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid7)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())

    # Core fields
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey(ref("users.id"), ondelete="CASCADE")
    )
    current_jti: Mapped[str] = mapped_column(String(36))

    # Where it was opened from
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # fits an IPv6 address

    # Activity tracking
    last_used_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="sessions", lazy="raise")
