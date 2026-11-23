"""Tokens: one-time use tokens for email verification, password reset, and sensitive operations."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Optional

from sqlalchemy import (
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from core.database.engine import GUID, UTCDateTime, uuid7
from modules.identity.models.base import CHAR_LENGTH, Base, enum_check, ref, table_args


class TokenType(StrEnum):
    """Purpose of the one-time token."""

    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"
    ACCOUNT_RECOVERY = "account_recovery"
    DEVICE_CONFIRMATION = "device_confirmation"


class OneTimeToken(Base):
    """One-time tokens sent via email for verification, password reset, and sensitive operations.

    The token hash is stored (never the plaintext). The hash is shared in the email link,
    and verifying it checks the hash in the database. Once used, it's deleted.
    """

    __tablename__ = "one_time_tokens"
    __table_args__ = table_args(
        ForeignKey(ref("users.id"), ondelete="CASCADE", name="one_time_tokens_user_id_fkey"),
        Index("idx_one_time_tokens_user_type", "user_id", "token_type"),
        Index("idx_one_time_tokens_expires_at", "expires_at"),
        enum_check("token_type", TokenType, "one_time_tokens_type_check"),
    )

    # Identification
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid7)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID())

    # Token data
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    token_type: Mapped[TokenType] = mapped_column(String(30))

    # Lifecycle
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime())
    used_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime(), nullable=True)

    # Tracking
    attempts: Mapped[int] = mapped_column(default=0)  # failed verification attempts
    max_attempts: Mapped[int] = mapped_column(default=5)

    # Context (what email is being verified, what operation prompted this, etc.)
    email: Mapped[Optional[str]] = mapped_column(String(CHAR_LENGTH), nullable=True)
    metadata: Mapped[dict] = mapped_column(default=dict)
