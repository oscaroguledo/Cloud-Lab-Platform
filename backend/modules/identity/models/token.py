"""Tokens: one-time use tokens for email verification, password reset, and sensitive operations."""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.engine import GUID, UTCDateTime, uuid7
from modules.identity.models.base import CHAR_LENGTH, Base, enum_check, ref, table_args

if TYPE_CHECKING:
    from modules.identity.models.user import User


class TokenType(StrEnum):
    """Purpose of the one-time token."""

    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"
    ACCOUNT_RECOVERY = "account_recovery"
    DEVICE_CONFIRMATION = "device_confirmation"


class OneTimeToken(Base):
    """A one-time token sent by email. Only its hash is stored; the plaintext goes in the link."""

    __tablename__ = "one_time_tokens"
    __table_args__ = table_args(
        Index("idx_one_time_tokens_user_type", "user_id", "token_type"),
        Index("idx_one_time_tokens_expires_at", "expires_at"),
        enum_check("token_type", TokenType, "one_time_tokens_type_check"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid7)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey(ref("users.id"), ondelete="CASCADE")
    )

    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    token_type: Mapped[TokenType] = mapped_column(String(30))

    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime())
    used_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime(), nullable=True)

    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5)

    email: Mapped[Optional[str]] = mapped_column(String(CHAR_LENGTH), nullable=True)
    # ``metadata`` is reserved by SQLAlchemy's declarative base.
    context: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    user: Mapped["User"] = relationship(back_populates="one_time_tokens", lazy="raise")
