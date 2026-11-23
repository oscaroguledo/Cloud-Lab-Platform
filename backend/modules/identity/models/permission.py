from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.identity.models.base import CHAR_LENGTH, Base, table_args


class Permission(Base):
    """A grantable capability, e.g. ``members:read``. The scope is its own key: nothing else is
    needed to identify one, and roles refer to it directly."""

    __tablename__ = "permissions"
    __table_args__ = table_args()

    scope: Mapped[str] = mapped_column(String(100), primary_key=True)
    description: Mapped[str] = mapped_column(String(CHAR_LENGTH), default="")
