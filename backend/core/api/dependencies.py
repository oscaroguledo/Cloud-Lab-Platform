"""FastAPI dependency injection: session management, auth, request context."""

import uuid
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.api.exceptions import InvalidToken, MissingBearer, MissingPermission
from core.auth import service as auth_service
from core.config import get_settings
from core.database.engine import DatabaseManager
from core.logging import get_structured_logger

logger = get_structured_logger(__name__)


async def get_db(request: Request) -> AsyncSession:
    """Get a database session from the app state."""
    db_manager: DatabaseManager = request.app.state.db
    async with db_manager.session_with_retry() as session:
        yield session


async def get_current_user(request: Request) -> dict:
    """Extract and validate the JWT from the Authorization header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise MissingBearer()

    try:
        scheme, token = auth_header.split()
        if scheme.lower() != "bearer":
            raise ValueError()
    except ValueError:
        raise MissingBearer()

    settings = get_settings()
    claims = auth_service.jwt.decode(token, settings.jwt_access_secret, settings.algorithm)
    return claims


async def require_scope(required_scope: str):
    """Create a dependency that checks for a specific scope."""
    async def _check_scope(user: Annotated[dict, Depends(get_current_user)]) -> dict:
        scopes: list[str] = user.get("scopes", [])
        if required_scope not in scopes:
            raise MissingPermission(required_scope)
        return user
    return _check_scope


def get_request_context(request: Request) -> dict:
    """Extract request context for audit logging and diagnostics."""
    return {
        "method": request.method,
        "path": request.url.path,
        "client_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }


CurrentUser = Annotated[dict, Depends(get_current_user)]
Database = Annotated[AsyncSession, Depends(get_db)]
