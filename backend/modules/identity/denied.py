"""Log requests that were refused for lack of permission or level, then answer as usual."""

import uuid

from fastapi import Request
from starlette.background import BackgroundTask

from app.core import auth
from app.core.api.dependencies import get_request_context
from app.core.api.exceptions import APIException, MissingPermission, api_exception_handler
from app.core.database.isolation import scope_to
from app.core.logging import get_structured_logger
from app.modules.identity import errors
from app.modules.identity.audit import Action, audit
from app.modules.identity.models import User
from app.modules.identity.notifier import ACCOUNT_LOCKED

logger = get_structured_logger(__name__)

# The refusals worth a record: someone tried something their permissions or level do not allow.
DENIALS = (MissingPermission, errors.PrivilegeEscalation, errors.OwnerProtected, errors.OwnerOnly)


async def record_denial(request: Request, exc: APIException) -> None:
    """Write an ``access.denied`` entry for the signed-in caller. Never raises: if the log is
    down, the denial goes to the error log in full instead, so it is never lost silently."""
    settings = request.app.state.settings
    header = request.headers.get("authorization", "")
    route = request.scope.get("route")
    where = {
        "reason": exc.error_code,
        "method": request.method,
        "route": getattr(route, "path_format", request.url.path),
        "ip": get_request_context(request).ip,
    }
    user_id = None
    try:
        claims = auth.service.jwt.decode(header.removeprefix("Bearer "), settings.jwt_access_secret)
        organization_id, user_id = uuid.UUID(claims["org"]), uuid.UUID(claims["sub"])
        async with request.app.state.db.session_factory() as db:
            db.info["auditor"] = request.app.state.auditor
            db.info["request_context"] = get_request_context(request)
            await scope_to(db, organization_id)
            user = await db.get(User, user_id)
            await audit(
                db, Action.ACCESS_DENIED, failure=True, organization_id=organization_id,
                actor_id=user_id, actor_email=user.email if user else None,
                message=exc.message, **where,
            )  # fmt: skip
            await db.commit()
    except Exception as error:  # a bad token, a missing user or a broken log: still answer
        logger.error(
            "Access denied, but the audit log could not record it",
            user_id=str(user_id) if user_id else None, error=type(error).__name__, **where,
        )  # fmt: skip


async def denied_handler(request: Request, exc: APIException):
    await record_denial(request, exc)
    return await api_exception_handler(request, exc)


async def locked_handler(request: Request, exc: errors.AccountLocked):
    """Answer a sign-in that locked the account like a wrong password, then email its owner.
    A normal background task would be dropped, because the request ends in an error."""
    response = await api_exception_handler(request, exc)
    user = exc.user
    response.background = BackgroundTask(
        request.app.state.notifier.send,
        ACCOUNT_LOCKED,
        to=user.email,
        language=user.language,
        first_name=user.first_name,
        minutes=request.app.state.settings.login_lockout_minutes,
    )
    return response
