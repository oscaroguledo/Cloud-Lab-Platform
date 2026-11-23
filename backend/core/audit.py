"""Writing audit entries from any module, through the log the app was started with.
Entries join the caller's database session and transaction; secrets in details are refused."""

import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

# Every action any module may record: modules add theirs with ``register_actions``.
ACTIONS: set[str] = set()

# A text value under a key like these is a secret and must never reach the log.
SECRET_KEY = re.compile(r"(^|_)(password|secret|token|hash|key|otp|code)s?$")
ALLOWED_KEYS = {"code"}  # a rule set's code (for example "ottawa-zoning") is not a secret


def register_actions(catalogue: type) -> type:
    """Add a module's ``Action`` class (its upper-case string attributes) to the catalogue."""
    ACTIONS.update(v for k, v in vars(catalogue).items() if k.isupper() and isinstance(v, str))
    return catalogue


def _check(action: str, details: dict[str, Any]) -> None:
    """Refuse an action nobody registered (a typo) and a secret-looking text value."""
    if action not in ACTIONS:
        raise ValueError(f"Unknown audit action {action!r}: add it to the module's Action class")
    for key, value in details.items():
        if isinstance(value, str) and key not in ALLOWED_KEYS and SECRET_KEY.search(key.lower()):
            raise ValueError(f"Audit details must not hold a secret ({key!r})")


class CoreAction:
    """What the shared plumbing records itself."""

    RATE_LIMITED = "security.rate_limited"


register_actions(CoreAction)


class Auditor(Protocol):
    async def record(
        self,
        db: AsyncSession,
        *,
        action: str,
        outcome: str = "success",
        organization_id: uuid.UUID | None = None,
        actor_id: uuid.UUID | None = None,
        actor_email: str | None = None,
        target_type: str | None = None,
        target_id: str | None = None,
        details: dict[str, Any] | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> None: ...

    async def forget_after(
        self, db: AsyncSession, subject_id: uuid.UUID, due_at: datetime
    ) -> None: ...

    async def about(self, db: AsyncSession, subject_id: uuid.UUID) -> list[dict]: ...


async def audit(
    db: AsyncSession,
    action: str,
    *,
    actor=None,
    organization_id: uuid.UUID | None = None,
    actor_id: uuid.UUID | None = None,
    actor_email: str | None = None,
    target: tuple[str, object] | None = None,
    failure: bool = False,
    **details: Any,
) -> None:
    """Record one event on db (nothing happens if the app has no audit log).
    Before sign-in pass actor_id and actor_email, not actor. Commit before raising on a failure."""
    _check(action, details)
    auditor: Auditor | None = db.info.get("auditor")
    if auditor is None:
        return
    ctx = db.info.get("request_context")
    if actor is not None:
        organization_id = organization_id or actor.organization_id
        actor_id = actor_id or actor.id
        actor_email = actor_email or actor.email
    await auditor.record(
        db,
        action=action,
        outcome="failure" if failure else "success",
        organization_id=organization_id,
        actor_id=actor_id,
        actor_email=actor_email,
        target_type=target[0] if target else None,
        target_id=str(target[1]) if target else None,
        details={k: v for k, v in details.items() if v is not None},
        ip=ctx.ip if ctx else None,
        user_agent=ctx.user_agent if ctx else None,
    )


async def forget_later(db: AsyncSession, subject_id: uuid.UUID, after: timedelta) -> None:
    """Have a person's emails, addresses and browsers blanked from the log once ``after`` has
    passed (the retention period). What they did, and their id, stay."""
    auditor: Auditor | None = db.info.get("auditor")
    if auditor is not None:
        await auditor.forget_after(db, subject_id, datetime.now(UTC) + after)


async def entries_about(db: AsyncSession, subject_id: uuid.UUID) -> list[dict]:
    """The log entries a person made or that name them (for a copy of their data)."""
    auditor: Auditor | None = db.info.get("auditor")
    return await auditor.about(db, subject_id) if auditor is not None else []
