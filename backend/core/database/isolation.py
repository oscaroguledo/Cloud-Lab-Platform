"""Row-level security helpers: scope a session to one organization, or bypass the scope.
A session with neither setting sees nothing (fail closed). Modules write their own policies."""

from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session as SyncSession

ORGANIZATION_SETTING = "app.organization_id"
BYPASS_SETTING = "app.bypass"

_ORGANIZATION_KEY = "organization_id"
_BYPASS_KEY = "bypass"


def _apply(session: SyncSession, transaction, connection) -> None:
    """Runs at the start of every transaction: restore this session's scope on the connection."""
    if _ORGANIZATION_KEY not in session.info and _BYPASS_KEY not in session.info:
        return  # not scoped: nothing to set, so the policies see nothing
    connection.execute(_settings_statement(session.info))


def _settings_statement(info: dict):
    organization = info.get(_ORGANIZATION_KEY) or ""
    bypass = "on" if info.get(_BYPASS_KEY) else ""
    return select(
        func.set_config(ORGANIZATION_SETTING, organization, True),
        func.set_config(BYPASS_SETTING, bypass, True),
    )


event.listen(SyncSession, "after_begin", _apply)


async def scope_to(session: AsyncSession, organization_id) -> None:
    """Confine this session to one organization (replacing any earlier scope)."""
    session.info[_ORGANIZATION_KEY] = str(organization_id)
    session.info.pop(_BYPASS_KEY, None)
    await session.execute(_settings_statement(session.info))


async def bypass(session: AsyncSession) -> None:
    """See every organization. Use only where the caller has already checked it may."""
    session.info.pop(_ORGANIZATION_KEY, None)
    session.info[_BYPASS_KEY] = True
    await session.execute(_settings_statement(session.info))
