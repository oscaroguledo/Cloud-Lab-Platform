"""Shared FastAPI dependencies. Authentication is token-only: a Principal comes from the signed
access token, with no database or identity-module call."""

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core import auth
from core.api import exceptions
from core.config import Settings

bearer = HTTPBearer(auto_error=False)


# -- infrastructure ------------------------------------------------------------------------------


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    """A database session with its connection established (retried on failure)."""
    async with request.app.state.db.session_with_retry() as session:
        # What a module needs to leave an audit trail: who is calling, and the recorder the app was
        # started with (None when the app has none, as in the command line).
        session.info["request_context"] = get_request_context(request)
        session.info["auditor"] = getattr(request.app.state, "auditor", None)
        yield session  # an uncommitted transaction is rolled back if the request fails


SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[AsyncSession, Depends(get_db)]


@dataclass(frozen=True)
class RequestContext:
    """Who is calling and from where; recorded on sessions."""

    ip: str | None
    user_agent: str | None


def get_request_context(request: Request) -> RequestContext:
    """The address is the socket peer: forwarding headers are never trusted (they are spoofable)."""
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return RequestContext(ip=ip, user_agent=user_agent[:255] if user_agent else None)


ContextDep = Annotated[RequestContext, Depends(get_request_context)]


# -- authentication ------------------------------------------------------------------------------


@dataclass(frozen=True)
class Principal:
    user_id: uuid.UUID
    organization_id: uuid.UUID
    scopes: frozenset[str]
    session_id: uuid.UUID | None = None


def _principal_from_token(token: str, settings: Settings) -> Principal:
    claims = auth.service.jwt.decode(token, settings.jwt_access_secret, settings.algorithm)
    try:
        return Principal(
            user_id=uuid.UUID(claims["sub"]),
            organization_id=uuid.UUID(claims["org"]),
            scopes=frozenset(claims["scopes"]),
            session_id=uuid.UUID(claims["sid"]) if claims.get("sid") else None,
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise exceptions.InvalidToken() from exc


async def get_current_auth_user(
    settings: SettingsDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Principal | None:
    """Authentication: the caller's Principal, or None when not authenticated."""
    if credentials is None:
        return None
    try:
        return _principal_from_token(credentials.credentials, settings)
    except exceptions.APIException:
        return None  # a missing, expired or invalid token simply means "not authenticated"


async def require_auth(
    current_user: Annotated[Principal | None, Depends(get_current_auth_user)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Principal:
    """Raises 401 if the caller is not authenticated."""
    if current_user is None:
        raise exceptions.MissingBearer() if credentials is None else exceptions.InvalidToken()
    return current_user


CurrentPrincipal = Annotated[Principal, Depends(require_auth)]


def require_scope(scope: str):
    """Dependency factory: the token must carry ``scope``. Returns the Principal."""

    async def checker(principal: CurrentPrincipal) -> Principal:
        if scope not in principal.scopes:
            raise exceptions.MissingPermission(scope)
        return principal

    return Depends(checker)
