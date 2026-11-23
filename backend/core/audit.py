"""Audit logging: actions tracked for compliance and security investigations."""

import enum
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


class CoreAction(str, enum.Enum):
    """Core system actions tracked in the audit log."""

    # Auth
    LOGIN_SUCCESS = "auth.login_success"
    LOGIN_FAILURE = "auth.login_failure"
    LOGOUT = "auth.logout"
    REGISTER = "identity.register"
    PASSWORD_CHANGE = "identity.password_change"
    PASSWORD_RESET = "identity.password_reset"
    MFA_ENABLED = "identity.mfa_enabled"
    MFA_DISABLED = "identity.mfa_disabled"

    # Security
    RATE_LIMITED = "security.rate_limited"
    UNAUTHORIZED_ACCESS = "security.unauthorized_access"
    INVALID_TOKEN = "security.invalid_token"

    # User management
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"


async def audit(
    db: AsyncSession,
    action: CoreAction,
    *,
    actor_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    failure: bool = False,
    **details: Any,
) -> None:
    """Record an audit log entry.

    Implementation depends on the audit schema being defined in the database models.
    This is a placeholder that logs to structured logging for now.
    """
    from core.logging import get_structured_logger

    logger = get_structured_logger("audit")
    logger.info(
        str(action),
        actor_id=actor_id,
        organization_id=organization_id,
        failure=failure,
        **details,
    )
