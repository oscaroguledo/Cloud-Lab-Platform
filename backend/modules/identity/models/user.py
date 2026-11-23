import uuid
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.engine import GUID, UTCDateTime, uuid7
from modules.identity.models.base import (
    CHAR_LENGTH,
    Base,
    enum_check,
    ref,
    table_args,
)
from modules.identity.models.role import Role

if TYPE_CHECKING:
    from modules.identity.models.token import OneTimeToken
    from modules.identity.models.organization import Organization
    from modules.identity.models.session import UserSession


class AccountStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"  # switched off (for example someone who left); reversible
    SUSPENDED = "suspended"  # blocked from signing in; reversible


class VerificationStatus(StrEnum):
    UNVERIFIED = "unverified"  # an owner who has not yet confirmed their email address
    VERIFIED = (
        "verified"  # confirmed by email, or vouched for by the administrator who created them
    )


class User(Base):
    """A member of exactly one organization, signing in with their email address and password."""

    __tablename__ = "users"
    __table_args__ = table_args(
        # A user's role must belong to the user's own organization.
        ForeignKeyConstraint(
            ["organization_id", "role_id"],
            [ref("roles.organization_id"), ref("roles.id")],
            name="users_organization_role_fkey",
        ),
        CheckConstraint(
            "gender IS NULL OR "
            "gender IN ('female','male','non_binary','other','prefer_not_to_say')",
            name="users_gender_check",
        ),
        enum_check("account_status", AccountStatus, "users_account_status_check"),
        enum_check("verification_status", VerificationStatus, "users_verification_status_check"),
        Index("idx_users_role_id", "role_id"),
        Index("idx_users_account_status", "account_status"),
        Index("idx_users_organization_created", "organization_id", "created_at"),
    )

    # Common fields
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid7)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        UTCDateTime(), onupdate=func.now(), nullable=True
    )

    # Organization and access
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey(ref("organizations.id"), ondelete="CASCADE")
    )
    role_id: Mapped[uuid.UUID] = mapped_column(GUID())

    # Core identity fields - frequently queried. The email is the sign-in name, stored lowercase.
    email: Mapped[str] = mapped_column(String(CHAR_LENGTH))
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(CHAR_LENGTH))
    # True while the password is one an administrator chose: it must be replaced at first sign-in.
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    # An administrator-set password stops working at this time (NULL once the member chose one).
    password_expires_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime(), nullable=True)

    # Status fields as columns for fast filtering
    account_status: Mapped[AccountStatus] = mapped_column(String(20), default=AccountStatus.ACTIVE)
    verification_status: Mapped[VerificationStatus] = mapped_column(
        String(20), default=VerificationStatus.UNVERIFIED
    )

    # Contact and profile information
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    # Free-form per-user settings (theme, notification choices...); the API keeps it small.
    preferences: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    # An IANA name, validated by the API.
    timezone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Two-step verification: the secret is encrypted, and the recovery codes are stored hashed.
    mfa_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_last_step: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    mfa_recovery_hashes: Mapped[list[str]] = mapped_column(JSONB, default=list)
    # Hashes of the browsers this user signed in with, so a new one can be flagged by email.
    known_devices: Mapped[list[str]] = mapped_column(JSONB, default=list)

    # Activity tracking and sign-in protection
    last_login: Mapped[Optional[datetime]] = mapped_column(UTCDateTime(), nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(UTCDateTime(), nullable=True)

    # Relationships (async sessions cannot lazy-load, so each is fetched explicitly when needed)
    role: Mapped[Role] = relationship(
        primaryjoin="User.role_id == Role.id",
        foreign_keys="User.role_id",
        viewonly=True,
        lazy="raise",
    )
    organization: Mapped["Organization"] = relationship(
        back_populates="users", foreign_keys="User.organization_id", lazy="raise"
    )
    sessions: Mapped[list["UserSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True, lazy="raise"
    )
    one_time_tokens: Mapped[list["OneTimeToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True, lazy="raise"
    )

    @property
    def is_active(self) -> bool:
        """True when account_status is 'active'."""
        return self.account_status == AccountStatus.ACTIVE

    @property
    def is_inactive(self) -> bool:
        """True when account_status is 'inactive'."""
        return self.account_status == AccountStatus.INACTIVE

    @property
    def is_suspended(self) -> bool:
        """True when account_status is 'suspended'."""
        return self.account_status == AccountStatus.SUSPENDED

    @property
    def verified(self) -> bool:
        """True when verification_status is 'verified'."""
        return self.verification_status == VerificationStatus.VERIFIED

    @property
    def password_expired(self) -> bool:
        """True when an administrator-set password was not replaced in time."""
        return (
            self.must_change_password
            and self.password_expires_at is not None
            and self.password_expires_at < datetime.now(UTC)
        )

    @property
    def is_locked(self) -> bool:
        """True while a temporary sign-in lockout is in force."""
        return self.locked_until is not None and self.locked_until > datetime.now(UTC)


# One account per email address across the whole platform (case-insensitive).
Index("users_email_key", func.lower(User.email), unique=True)
