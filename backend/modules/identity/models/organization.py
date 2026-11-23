import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.engine import GUID, UTCDateTime, uuid7
from modules.identity.models.base import CHAR_LENGTH, Base, enum_check, table_args

if TYPE_CHECKING:
    from modules.identity.models.user import User


class OrganizationSize(StrEnum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class OrganizationKind(StrEnum):
    PERSONAL = "personal"  # one person using the app on their own
    BUSINESS = "business"  # a firm with a name of its own


class OrganizationStatus(StrEnum):
    ACTIVE = "active"
    CLOSED = "closed"  # nobody can sign in; every session has been ended


class Organization(Base):
    """An organisation (a design-build firm); every user belongs to exactly one. Its owners are the
    users who hold the owner role (there can be several)."""

    __tablename__ = "organizations"
    __table_args__ = table_args(
        enum_check("status", OrganizationStatus, "organizations_status_check"),
        enum_check("size", OrganizationSize, "organizations_size_check"),
        enum_check("kind", OrganizationKind, "organizations_kind_check"),
    )

    # Common fields
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid7)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        UTCDateTime(), onupdate=func.now(), nullable=True
    )

    # Core fields - frequently queried
    name: Mapped[str] = mapped_column(String(CHAR_LENGTH))
    size: Mapped[OrganizationSize] = mapped_column(String(20), default=OrganizationSize.SMALL)
    kind: Mapped[OrganizationKind] = mapped_column(String(20), default=OrganizationKind.BUSINESS)
    status: Mapped[OrganizationStatus] = mapped_column(
        String(20), default=OrganizationStatus.ACTIVE
    )
    # The single organisation that holds the platform's own staff (the super admins).
    is_platform: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    users: Mapped[list["User"]] = relationship(
        back_populates="organization",
        foreign_keys="User.organization_id",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )

    @property
    def is_closed(self) -> bool:
        """True when status is 'closed'."""
        return self.status == OrganizationStatus.CLOSED


# At most one platform organisation.
Index(
    "organizations_one_platform_key",
    Organization.is_platform,
    unique=True,
    postgresql_where=Organization.is_platform.is_(True),
)
