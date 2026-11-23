import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.engine import GUID, UTCDateTime, uuid7
from modules.identity.models.base import CHAR_LENGTH, Base, ref, table_args

ZERO_UUID = "00000000-0000-0000-0000-000000000000"
MIN_LEVEL = 1  # the lowest level: a plain member
MAX_LEVEL = 99  # the highest level any role but the owner can have
OWNER_LEVEL = 100  # only the owner role is this high
DEFAULT_LEVEL = MIN_LEVEL  # the level of a new custom role unless one is given


class RolePermission(Base):
    """Grants one permission scope to a role."""

    __tablename__ = "role_permissions"
    __table_args__ = table_args()

    role_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey(ref("roles.id"), ondelete="CASCADE"), primary_key=True
    )
    scope: Mapped[str] = mapped_column(
        String(100), ForeignKey(ref("permissions.scope"), ondelete="CASCADE"), primary_key=True
    )


class Role(Base):
    """Groups permissions; belongs to an organization. Rows with none are default templates."""

    __tablename__ = "roles"
    __table_args__ = table_args(
        # Target of the composite foreign key that keeps a user's role in the user's organization.
        UniqueConstraint("organization_id", "id", name="roles_organization_id_id_key"),
        CheckConstraint("max_users IS NULL OR max_users >= 1", name="roles_max_users_check"),
        CheckConstraint("level BETWEEN 1 AND 100", name="roles_level_check"),
        CheckConstraint("NOT is_owner OR level = 100", name="roles_owner_level_check"),
    )

    # Common fields
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid7)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        UTCDateTime(), onupdate=func.now(), nullable=True
    )

    # Core fields
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(), ForeignKey(ref("organizations.id"), ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(String(CHAR_LENGTH), default="")
    is_owner: Mapped[bool] = mapped_column(Boolean, default=False)  # the owner role: all access
    # Built in: one of the standard roles every organisation starts with (or super_admin). It
    # cannot be renamed or deleted; custom roles belong to one organisation only.
    builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    # Rank: you can manage users and roles at or below your own level. Only owners are at 100.
    level: Mapped[int] = mapped_column(SmallInteger, default=DEFAULT_LEVEL)
    max_users: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # seat limit

    # Relationships
    permission_links: Mapped[list[RolePermission]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, lazy="raise"
    )
    # The role's scopes as plain strings, e.g. ["members:read", "roles:read"].
    scopes = association_proxy(
        "permission_links", "scope", creator=lambda scope: RolePermission(scope=scope)
    )


_organization_or_zero = func.coalesce(Role.organization_id, text(f"'{ZERO_UUID}'::uuid"))

# Names are unique per organization (ignoring case), and among the templates (NULL organization_id).
Index("roles_organization_name_key", _organization_or_zero, func.lower(Role.name), unique=True)
# Exactly one owner role per organization (and one among the templates).
Index(
    "roles_one_owner_role_key",
    _organization_or_zero,
    unique=True,
    postgresql_where=Role.is_owner.is_(True),
)
