"""The audit actions identity records: the contract with whoever reads the log."""

from app.core.audit import audit, entries_about, forget_later, register_actions

__all__ = ["Action", "audit", "entries_about", "forget_later"]


@register_actions
class Action:
    REGISTER = "auth.register"
    LOGIN = "auth.login"
    LOGIN_FAILED = "auth.login_failed"
    ACCOUNT_LOCKED = "auth.account_locked"
    LOGOUT = "auth.logout"
    TOKEN_REUSE = "auth.token_reuse_detected"
    REFRESH_FAILED = "auth.refresh_failed"
    EMAIL_VERIFIED = "auth.email_verified"
    EMAIL_VERIFICATION_FAILED = "auth.email_verification_failed"
    PASSWORD_CHANGED = "auth.password_changed"
    PASSWORD_RESET_REQUESTED = "auth.password_reset_requested"
    PASSWORD_RESET = "auth.password_reset"

    MFA_ENABLED = "mfa.enabled"
    MFA_DISABLED = "mfa.disabled"

    ACCESS_DENIED = "access.denied"

    SESSION_REVOKED = "session.revoked"

    ORGANIZATION_CREATED = "organization.created"
    ORGANIZATION_UPDATED = "organization.updated"
    ORGANIZATION_CLOSED = "organization.closed"
    ORGANIZATIONS_VIEWED = "platform.organizations_viewed"  # super admins reading across them
    ORGANIZATION_VIEWED = "platform.organization_viewed"

    USER_CREATED = "user.created"
    USER_PROFILE_UPDATED = "user.profile_updated"
    USER_EMAIL_CHANGED = "user.email_changed"
    USER_ROLE_CHANGED = "user.role_changed"
    USER_STATUS_CHANGED = "user.status_changed"
    USER_PASSWORD_RESET = "user.password_reset"
    USER_REMOVED = "user.removed"
    USER_MFA_RESET = "user.mfa_reset"
    USER_DATA_EXPORTED = "user.data_exported"

    ROLE_CREATED = "role.created"
    ROLE_UPDATED = "role.updated"
    ROLE_DELETED = "role.deleted"
    ROLE_PERMISSIONS_CHANGED = "role.permissions_changed"

    PERMISSION_CREATED = "permission.created"
    PERMISSION_UPDATED = "permission.updated"
    PERMISSION_DELETED = "permission.deleted"
