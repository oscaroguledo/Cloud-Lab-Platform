"""Every setting and tunable value, from environment variables with ``.env`` fallbacks.
The real environment beats ``.env.prod``/``.env.dev``, which beats ``.env``."""

import os
from functools import lru_cache

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url


def _env_files() -> tuple[str, ...]:
    environment = os.getenv("ENVIRONMENT", "dev").lower()
    specific = ".env.prod" if environment in ("production", "prod") else ".env.dev"
    return (".env", specific)  # later files override earlier ones; missing files are ignored


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_env_files(), extra="ignore")

    # Core
    app_name: str = "Wagenabe"  # shown in emails and the API docs
    app_description: str = (
        "Wagenabe identity and access management: multi-organization contractor accounts, "
        "role-based access control, user onboarding and sessions."
    )
    app_version: str = "0.1.0"
    platform_organization_name: str = "Wagenabe Platform"  # where super admins belong
    environment: str = "dev"
    server_port: int = 8080
    frontend_url: str = "http://localhost:5173"  # base of the links sent in emails
    allowed_hosts: str = ""  # comma-separated Host headers to accept; empty accepts any
    # Load balancers whose X-Forwarded-For is believed (IPs or CIDRs, comma-separated). Empty
    # trusts none, so the client address is the socket peer and cannot be forged by a header.
    trusted_proxies: str = ""

    # Database (PostgreSQL). DATABASE_DSN is accepted as an older name for DATABASE_URL.
    database_url: str = Field(validation_alias=AliasChoices("DATABASE_URL", "DATABASE_DSN"))
    # The owner role, used only for migrations. Unset: the app role runs them (the dev default).
    migration_database_url: str | None = Field(
        default=None, validation_alias="MIGRATION_DATABASE_URL"
    )
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_echo: bool = False  # log every SQL statement
    auto_migrate: bool = True  # apply pending migrations on startup

    # Auth
    jwt_access_secret: str
    jwt_refresh_secret: str
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"

    # Account security
    # None means "required in production, optional elsewhere"; see `email_verification_required`.
    require_email_verification: bool | None = None
    login_max_attempts: int = 5  # failed logins before the account is temporarily locked
    login_lockout_minutes: int = 15
    temporary_password_ttl_days: int = 7
    email_code_ttl_minutes: int = 15  # how long an emailed verification code works
    email_code_max_attempts: int = 5  # wrong guesses before the code is destroyed
    password_reset_ttl_minutes: int = 60
    email_resend_cooldown_seconds: int = 60  # no new code or reset link sooner than this
    known_devices_limit: int = 20  # browsers remembered per user for "new sign-in" emails
    mfa_period_seconds: int = 30  # how long an authenticator code lasts (apps assume 30)
    mfa_recovery_code_count: int = 8
    # How long a removed user's email, address and browser stay in the audit log, for
    # investigations, before they are blanked (the user id and what happened stay).
    audit_email_retention_days: int = 90
    # The audit log is split by month; months older than this are dropped (with their entries).
    audit_retention_years: int = 7
    audit_partitions_ahead_months: int = 3  # empty months made in advance
    # Encrypts authenticator secrets at rest. Empty derives a key from the refresh secret (not for
    # production, where rotating that secret would lock everyone out of two-step verification).
    mfa_secret_key: str = ""

    # Rate limiting (Redis) and request size. A Redis outage never blocks requests.
    redis_url: str = "redis://localhost:6379/0"
    rate_limit_enabled: bool = True
    # Every limit: name -> (calls allowed, per this many seconds). RATE_LIMITS='{"auth": [60, 60]}'
    # overrides only the names it lists. "-account" is per email, "-pair" per email and IP.
    rate_limits: dict[str, tuple[int, int]] = {
        "anonymous": (600, 60),  # any API call without a token, per address (a flood guard)
        "user": (120, 60),  # any API call, per signed-in user and address together
        "auth": (120, 60),  # sign-in, registration, codes and resets, per address
        "refresh": (600, 60),  # token refresh, per address
        "register-email": (5, 3600),
        "register-pair": (3, 3600),
        "login-account": (30, 900),
        "login-pair": (8, 60),
        "refresh-session": (30, 60),
        "verify-account": (20, 900),
        "verify-pair": (10, 900),
        "resend-account": (5, 900),
        "resend-pair": (3, 900),
        "forgot-account": (5, 900),
        "forgot-pair": (3, 900),
        "password-change": (10, 900),
        "mfa": (10, 900),
        "close": (10, 900),
        "user-create": (30, 60),
        "user-bulk": (10, 60),
        "user-reset": (20, 60),
        "export": (5, 900),  # copies of a person's data
        "audit-export": (10, 900),  # downloads of the audit log
    }
    # Body caps. Most requests are a few KiB even with every field at its maximum length;
    # the large routes (bulk member creation, role scopes) can reach ~140 KiB in that worst case.
    max_request_body_bytes: int = 65_536
    max_large_body_bytes: int = 262_144
    large_body_routes: tuple[str, ...] = (r"/api/v1/users/bulk",)  # path patterns given the big cap

    # Email is sent through the Brevo transactional API (https://www.brevo.com).
    email_from: str = "Wagenabe <no-reply@example.com>"
    brevo_api_key: str = ""
    brevo_api_url: str = "https://api.brevo.com/v3/smtp/email"
    email_send_attempts: int = 3  # network errors, 429 and 5xx are retried
    email_retry_backoff_seconds: tuple[float, ...] = (0.5, 1.0)  # wait before attempt 2, 3...
    # The outbox: an email that fails is tried again after each of these waits, then marked
    # failed for platform staff. Workers look for due emails this often.
    email_retry_minutes: tuple[int, ...] = (1, 5, 15, 60, 180, 360)
    email_outbox_poll_seconds: int = 10
    email_backlog_warn_seconds: int = 900  # warn when the oldest waiting email is this old
    email_outbox_keep_days: int = 30  # sent, failed and suppressed rows are deleted after this
    email_recipient_hourly_limit: int = 20  # more to one address in an hour are suppressed
    email_dedupe_seconds: int = 60  # the same email to the same address again is suppressed
    # Who sends, on every email (Canada's anti-spam law, CASL). The address is required in prod.
    company_legal_name: str = "Wagenabe"
    company_mailing_address: str = ""
    company_contact_email: str = "support@example.com"

    @field_validator("rate_limits", mode="after")
    @classmethod
    def _keep_default_limits(cls, value: dict) -> dict:
        """An override changes only the limits it names; the others keep their defaults."""
        return {**cls.model_fields["rate_limits"].default, **value}

    @model_validator(mode="after")
    def _check_secrets(self) -> "Settings":
        if len(self.jwt_access_secret) < 32 or len(self.jwt_refresh_secret) < 32:
            raise ValueError("JWT secrets must be at least 32 characters")
        if self.jwt_access_secret == self.jwt_refresh_secret:
            raise ValueError("JWT_ACCESS_SECRET and JWT_REFRESH_SECRET must differ")
        return self

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in ("production", "prod")

    @property
    def email_verification_required(self) -> bool:
        """Whether a new owner must verify their email before signing in."""
        if self.require_email_verification is None:
            return self.is_production
        return self.require_email_verification

    @property
    def cors_origins(self) -> list[str]:
        """Any origin in development; only the frontend in production."""
        return [self.frontend_url] if self.is_production else ["*"]

    @property
    def allowed_host_list(self) -> list[str]:
        return [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]

    def validate_environment(self) -> dict:
        """Extra checks for deployed environments: ``{"is_valid": bool, "problems": [...]}``."""
        problems = []
        if self.is_production:
            for name in ("jwt_access_secret", "jwt_refresh_secret"):
                if getattr(self, name).startswith("change-me"):
                    problems.append(f"{name.upper()} is still the example placeholder")
            if "localhost" in self.frontend_url:
                problems.append("FRONTEND_URL still points at localhost")
            if "*" in self.trusted_proxies:
                problems.append("TRUSTED_PROXIES must list the load balancers, not '*'")
            if not self.mfa_secret_key:
                problems.append("MFA_SECRET_KEY is required in production")
            if not self.company_mailing_address:
                problems.append("COMPANY_MAILING_ADDRESS is required in production (CASL)")
            if not self.brevo_api_key:
                problems.append(
                    "BREVO_API_KEY is required in production: email is sent through Brevo"
                )
        return {"is_valid": not problems, "problems": problems}

    def async_database_url(self) -> tuple[URL, dict]:
        """Turn a libpq-style URL into an asyncpg URL plus connect args.
        asyncpg does not understand ``sslmode``, so it is translated to ``ssl``."""
        url = make_url(self.database_url).set(drivername="postgresql+asyncpg")
        query = dict(url.query)
        sslmode = query.pop("sslmode", None)
        connect_args = {"ssl": sslmode} if sslmode else {}
        return url.set(query=query), connect_args


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
