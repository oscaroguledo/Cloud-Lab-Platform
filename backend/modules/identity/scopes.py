"""Permission scopes (``resource:action``) checked by identity, seeded by migration.
Roles are granted scopes, and access tokens carry the caller's scopes."""


class Scopes:
    """Names of grantable identity permissions."""

    USERS_READ = "users:read"
    USERS_CREATE = "users:create"
    USERS_UPDATE = "users:update"  # edit a user's profile and change their role
    USERS_CHANGE_EMAIL = "users:change_email"  # change the address a user signs in with
    USERS_SUSPEND = "users:suspend"  # set a user's status: active, inactive or suspended
    USERS_REMOVE = "users:remove"
    USERS_RESET_PASSWORD = "users:reset_password"
    USERS_EXPORT = "users:export"  # download everything kept about a user (an access request)
    ROLES_READ = "roles:read"
    ROLES_MANAGE = "roles:manage"
    PERMISSIONS_READ = "permissions:read"
    PERMISSIONS_MANAGE = "permissions:manage"  # edit the catalogue: super admins only
    ORGANIZATIONS_MANAGE = "organizations:manage"  # list/create/edit any organisation: super admins
    ORGANIZATIONS_READ = "organizations:read"
    ORGANIZATIONS_UPDATE = "organizations:update"
    ORGANIZATIONS_CLOSE = "organizations:close"
    SESSIONS_READ = "sessions:read"  # see another user's signed-in devices
    SESSIONS_REVOKE = "sessions:revoke"  # sign another user out
    AUDIT_READ = "audit:read"  # read the organisation's audit log (the audit module checks it)
    AUDIT_READ_ALL = "audit:read_all"  # read every organisation's audit log: super admins
    RULES_READ = (
        "rules:read"  # read published rule sets and their rules (the rules module checks it)
    )
    RULES_MANAGE = "rules:manage"  # write draft rule sets and rules: platform staff
    RULES_VERIFY = "rules:verify"  # mark a rule as checked against its source: platform staff
    RULES_PUBLISH = "rules:publish"  # publish or retire a rule set: platform staff
    NOTIFICATIONS_MANAGE = "notifications:manage"  # see and retry the email outbox: platform staff

    # Scopes only platform staff (super admins) may hold; no organisation role ever gets them.
    PLATFORM_ONLY = (
        PERMISSIONS_MANAGE, ORGANIZATIONS_MANAGE, AUDIT_READ_ALL,
        RULES_MANAGE, RULES_VERIFY, RULES_PUBLISH, NOTIFICATIONS_MANAGE,
    )  # fmt: skip


# Built from the names above, so a new scope is listed once. The owner role holds every
# organisation scope, including ones added later (see ``role_grants``).
Scopes.ALL = tuple(v for k, v in vars(Scopes).items() if k.isupper() and isinstance(v, str))
Scopes.ORGANIZATION_ALL = tuple(s for s in Scopes.ALL if s not in Scopes.PLATFORM_ONLY)
