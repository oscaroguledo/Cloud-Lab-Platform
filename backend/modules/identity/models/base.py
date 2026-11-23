"""Foundation shared by every identity model: the ``identity`` schema, base class and helpers."""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, MetaData
from sqlalchemy.orm import DeclarativeBase

from core.database.engine import GUID, UTCDateTime

# Every table of this module lives in this Postgres schema, and nothing outside the module may
# reference these tables. That is what lets the module move to its own database.
SCHEMA = "identity"

# Default length of free-text columns.
CHAR_LENGTH = 255


def table_args(*constraints):
    """``__table_args__`` for a model: its constraints and indexes, placed in the schema."""
    return (*constraints, {"schema": SCHEMA})


def ref(column: str) -> str:
    """A schema-qualified foreign-key target: ``ref("roles.id")`` is ``"identity.roles.id"``."""
    return f"{SCHEMA}.{column}"


def enum_check(column: str, enum: type[StrEnum], name: str) -> CheckConstraint:
    """Restrict a text column to an enum's values, so the enum is the only list of them."""
    values = ",".join(f"'{member.value}'" for member in enum)
    return CheckConstraint(f"{column} IN ({values})", name=name)


class Base(DeclarativeBase):
    # Also set on the metadata, so a table added without an explicit schema still lands here.
    metadata = MetaData(schema=SCHEMA)
    type_annotation_map = {uuid.UUID: GUID, datetime: UTCDateTime}
    # Re-read server-generated values (timestamps) after INSERT/UPDATE: async sessions cannot
    # lazy-load them afterwards.
    __mapper_args__ = {"eager_defaults": True}
