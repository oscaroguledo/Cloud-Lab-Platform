"""Turn the database's "that value is already taken" refusal into our own error."""

from contextlib import asynccontextmanager

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

UNIQUE_VIOLATION = "23505"


def is_unique_violation(exc: IntegrityError) -> bool:
    code = getattr(exc.orig, "sqlstate", None) or getattr(exc.orig, "pgcode", None)
    return code == UNIQUE_VIOLATION


def violated_constraint(exc: IntegrityError) -> str:
    """The name of the constraint a failed statement broke ('' if unknown)."""
    cause = getattr(exc.orig, "__cause__", None)
    return getattr(cause, "constraint_name", None) or getattr(exc.orig, "constraint_name", "") or ""


@asynccontextmanager
async def unique_check(db: AsyncSession, error: Exception, constraint: str | None = None):
    """Run the block; if the database refuses it because a value that must be unique is already
    taken (optionally: by the named constraint), undo it and raise ``error`` instead."""
    try:
        yield
    except IntegrityError as exc:
        await db.rollback()
        broke_it = constraint is None or constraint in violated_constraint(exc)
        if is_unique_violation(exc) and broke_it:
            raise error from exc
        raise
