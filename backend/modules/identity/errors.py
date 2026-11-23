"""Identity errors on the shared API exceptions, each with a stable ``error_code``.
Shared token errors are re-exported so callers import from one place."""

from app.core.api.exceptions import (
    APIException,
    AuthenticationException,
    AuthorizationException,
    BadRequestException,
    ConflictException,
    InvalidToken,
    MissingBearer,
    MissingPermission,
    NotFoundException,
)

__all__ = ["APIException", "InvalidToken", "MissingBearer", "MissingPermission"]


# -- authentication -------------------------------------------------------------------------------


class InvalidCredentials(AuthenticationException):
    def __init__(self):
        super().__init__(
            "Invalid organisation, username or password", error_code="INVALID_CREDENTIALS"
        )


class AccountLocked(InvalidCredentials):
    """The failure that locked the account: answered like any wrong password, and the owner is
    emailed (see ``locked_handler``)."""

    def __init__(self, user):
        super().__init__()
        self.user = user


class MfaRequired(AuthenticationException):
    def __init__(self):
        super().__init__("Enter the code from your authenticator app", error_code="MFA_REQUIRED")


class InvalidMfaCode(BadRequestException):
    def __init__(self):
        super().__init__("That code is not valid", error_code="INVALID_MFA_CODE")


class MfaAlreadyOn(ConflictException):
    def __init__(self):
        super().__init__("Two-step verification is already on", error_code="MFA_ALREADY_ON")


class MfaNotOn(BadRequestException):
    def __init__(self):
        super().__init__("Two-step verification is not on", error_code="MFA_NOT_ON")


class PasswordExpired(AuthorizationException):
    def __init__(self):
        super().__init__(
            "Your temporary password has expired; ask an administrator for a new one",
            error_code="PASSWORD_EXPIRED",
        )


class PasswordUnchanged(BadRequestException):
    def __init__(self):
        super().__init__(
            "The new password must be different from the current one",
            error_code="PASSWORD_UNCHANGED",
        )


class AccountDisabled(AuthorizationException):
    def __init__(self):
        super().__init__("This account is suspended", error_code="ACCOUNT_DISABLED")


class AccountInactive(AuthorizationException):
    def __init__(self):
        super().__init__("This account is inactive", error_code="ACCOUNT_INACTIVE")


class EmailNotVerified(AuthorizationException):
    def __init__(self):
        super().__init__("Verify your email address to sign in", error_code="EMAIL_NOT_VERIFIED")


class OrganizationClosed(AuthorizationException):
    def __init__(self):
        super().__init__("This organisation has been closed", error_code="ORGANIZATION_CLOSED")


class InvalidPassword(BadRequestException):
    def __init__(self):
        super().__init__("The password is incorrect", error_code="INVALID_PASSWORD")


class InvalidOneTimeToken(BadRequestException):
    def __init__(self):
        super().__init__(
            "This link is invalid or has expired", error_code="INVALID_OR_EXPIRED_TOKEN"
        )


class InvalidVerificationCode(BadRequestException):
    def __init__(self):
        super().__init__(
            "This code is wrong or has expired; request a new one",
            error_code="INVALID_VERIFICATION_CODE",
        )


class EmailTaken(ConflictException):
    def __init__(self):
        super().__init__("This email is already registered", error_code="EMAIL_TAKEN")


class PasswordChangeRequired(AuthorizationException):
    def __init__(self):
        super().__init__(
            "You must change your temporary password before doing anything else",
            error_code="PASSWORD_CHANGE_REQUIRED",
        )


# -- members and organization ---------------------------------------------------------------


class UserNotFound(NotFoundException):
    def __init__(self):
        super().__init__("User not found", resource="user", error_code="USER_NOT_FOUND")


class OrganizationNotFound(NotFoundException):
    def __init__(self):
        super().__init__(
            "Organisation not found", resource="organization", error_code="ORGANIZATION_NOT_FOUND"
        )


class OwnerProtected(AuthorizationException):
    def __init__(self, message: str = "Only an owner can do this to an owner"):
        super().__init__(message, error_code="OWNER_PROTECTED")


class OwnerOnly(AuthorizationException):
    def __init__(self):
        super().__init__("Only an owner of the organisation can do this", error_code="OWNER_ONLY")


class CannotActOnSelf(BadRequestException):
    def __init__(self, message: str = "You cannot do this to your own account"):
        super().__init__(message, error_code="CANNOT_ACT_ON_SELF")


class PrivilegeEscalation(AuthorizationException):
    def __init__(self, message: str = "You cannot grant or manage privileges you do not hold"):
        super().__init__(message, error_code="PRIVILEGE_ESCALATION")


class LastOwner(ConflictException):
    def __init__(self):
        super().__init__(
            "The organisation must keep at least one active owner", error_code="LAST_OWNER"
        )


# -- roles ----------------------------------------------------------------------------------------


class RoleExists(ConflictException):
    def __init__(self):
        super().__init__("A role with this name already exists", error_code="ROLE_EXISTS")


class UnknownScope(BadRequestException):
    def __init__(self):
        super().__init__("Unknown permission scope", error_code="UNKNOWN_SCOPE")


class RoleNotFound(NotFoundException):
    def __init__(self):
        super().__init__("Role not found", resource="role", error_code="ROLE_NOT_FOUND")


class OwnerRoleLocked(AuthorizationException):
    def __init__(self):
        super().__init__(
            "The owner role holds every permission and cannot be changed or deleted",
            error_code="OWNER_ROLE_LOCKED",
        )


class RoleFull(ConflictException):
    def __init__(self):
        super().__init__(
            "This role has reached its maximum number of users", error_code="ROLE_FULL"
        )


class LimitBelowMembers(ConflictException):
    def __init__(self):
        super().__init__(
            "The limit is lower than the role's current number of users",
            error_code="LIMIT_BELOW_MEMBERS",
        )


class BuiltinRoleProtected(ConflictException):
    def __init__(self):
        super().__init__(
            "Built-in roles cannot be renamed or deleted", error_code="BUILTIN_ROLE_PROTECTED"
        )


class PlatformProtected(AuthorizationException):
    def __init__(self):
        super().__init__(
            "The platform organisation cannot be closed", error_code="PLATFORM_PROTECTED"
        )


class PermissionExists(ConflictException):
    def __init__(self):
        super().__init__("That permission already exists", error_code="PERMISSION_EXISTS")


class PermissionNotFound(NotFoundException):
    def __init__(self):
        super().__init__(
            "Permission not found", resource="permission", error_code="PERMISSION_NOT_FOUND"
        )


class BuiltinPermissionProtected(ConflictException):
    def __init__(self):
        super().__init__(
            "Built-in permissions are used by the code and cannot be deleted",
            error_code="BUILTIN_PERMISSION_PROTECTED",
        )


class PermissionInUse(ConflictException):
    def __init__(self):
        super().__init__(
            "That permission is still granted to a role; remove it from the roles first",
            error_code="PERMISSION_IN_USE",
        )


class RoleInUse(ConflictException):
    def __init__(self):
        super().__init__("The role is still assigned to users", error_code="ROLE_IN_USE")


class SessionNotFound(NotFoundException):
    def __init__(self):
        super().__init__("Session not found", resource="session", error_code="SESSION_NOT_FOUND")
