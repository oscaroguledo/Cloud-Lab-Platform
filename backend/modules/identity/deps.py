"""Identity's own dependencies: unlike the token-only core ones they load the user from the
database, so suspensions, role changes and sign-outs apply immediately."""

import uuid
from typing import Annotated

from fastapi import BackgroundTasks, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.api.dependencies import (
    ContextDep,
    CurrentPrincipal,
    SessionDep,
    SettingsDep,
)
from app.core.api.pagination import Pagination
from app.core.database.isolation import bypass, scope_to
from app.modules.identity import errors
from app.modules.identity.models import User
from app.modules.identity.notifier import Notifier
from app.modules.identity.services.common import ensure_can_sign_in, load_user, user_scopes
from app.modules.identity.services.sessions import SessionService

__all__ = [
    "ContextDep",
    "CurrentSession",
    "CurrentUser",
    "CurrentUserAnyState",
    "NotifyDep",
    "PublicDb",
    "Pagination",
    "SessionDep",
    "SettingsDep",
    "require_scope",
]


class BackgroundNotify:
    """Stages notifications in the request's own transaction, then sends them after the response."""

    def __init__(self, notifier: Notifier, background: BackgroundTasks, db: AsyncSession):
        self._notifier = notifier
        self._background = background
        self._db = db
        self._queued = False

    async def send(self, kind: str, *, to: str, language: str, **params: object) -> None:
        await self._notifier.stage(self._db, kind, to=to, language=language, **params)
        if not self._queued:  # one send round per request, once its transaction is committed
            self._background.add_task(self._notifier.deliver_due)
            self._queued = True


def get_notify(request: Request, background: BackgroundTasks, db: SessionDep) -> BackgroundNotify:
    return BackgroundNotify(request.app.state.notifier, background, db)


NotifyDep = Annotated[BackgroundNotify, Depends(get_notify)]


async def _authenticate(principal: CurrentPrincipal, db: SessionDep) -> User:
    """The signed-in user (role, scopes, organization), after checking session and account."""
    if principal.session_id is None:
        raise errors.InvalidToken()
    await scope_to(
        db, principal.organization_id
    )  # from here on, the database shows only this organization
    user = await load_user(db, principal.user_id)
    if not await SessionService(db).is_active(principal.session_id, user.id):
        raise errors.InvalidToken()  # signed out, or the session was revoked
    ensure_can_sign_in(user)
    return user


async def public_db(db: SessionDep) -> AsyncSession:
    """For routes that run before sign-in (sign-in, registration, codes, resets).
    They find an account by email across organizations, and each checks its own secret first."""
    await bypass(db)
    return db


PublicDb = Annotated[AsyncSession, Depends(public_db)]


async def current_user_any_state(principal: CurrentPrincipal, db: SessionDep) -> User:
    """The signed-in user, even while they still owe a password change."""
    return await _authenticate(principal, db)


async def current_user(user: Annotated[User, Depends(current_user_any_state)]) -> User:
    """The signed-in user. Refused until a temporary password has been replaced."""
    if user.must_change_password:
        raise errors.PasswordChangeRequired()
    return user


CurrentUser = Annotated[User, Depends(current_user)]
CurrentUserAnyState = Annotated[User, Depends(current_user_any_state)]


async def current_session(principal: CurrentPrincipal) -> uuid.UUID:
    """The id of the session making this request."""
    assert principal.session_id is not None
    return principal.session_id


CurrentSession = Annotated[uuid.UUID, Depends(current_session)]


def require_scope(scope: str):
    """Dependency factory: the caller's role must grant ``scope``. Returns the user."""

    async def checker(user: CurrentUser) -> User:
        if scope not in user_scopes(user):
            raise errors.MissingPermission(scope)
        return user

    return Depends(checker)
