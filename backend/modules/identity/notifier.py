"""What identity needs from a notification service (app.main passes one in).
The kind strings are the contract; the parameters each takes are listed beside it."""

from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

# kind -> parameters (besides ``to``)
ACCOUNT_CREATED = "account_created"  # first_name, organization_name
VERIFY_EMAIL = "verify_email"  # first_name, code
RESET_PASSWORD = "reset_password"  # first_name, token
EMAIL_CHANGED = "email_changed"  # first_name, old_email, new_email
PASSWORD_CHANGED = "password_changed"  # first_name
NEW_SIGN_IN = "new_sign_in"  # first_name, device, ip, time
ACCOUNT_LOCKED = "account_locked"  # first_name, minutes
MFA_ENABLED = "mfa_enabled"  # first_name
MFA_DISABLED = "mfa_disabled"  # first_name
ROLE_CHANGED = "role_changed"  # first_name, organization_name, role
ACCOUNT_STATUS_CHANGED = "account_status_changed"  # first_name, organization_name, status
ORGANIZATION_CLOSED = "organization_closed"  # first_name, organization_name


class Notifier(Protocol):
    async def stage(
        self, db: AsyncSession, kind: str, *, to: str, **params: object
    ) -> object: ...

    async def deliver_due(self) -> int: ...


class Notify(Protocol):
    """Add a notification to the caller's open transaction, so it is sent only if the change that
    caused it commits. Call it before the commit; it goes out right after the response."""

    async def send(self, kind: str, *, to: str, **params: object) -> None: ...
