"""Authentication service: login, MFA, SSO, password management."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import service as auth_service
from core.config import get_settings
from core.logging import get_structured_logger
from modules.identity.models.session import UserSession
from modules.identity.models.sso import SSOConnection, SSOProvider
from modules.identity.models.token import OneTimeToken, TokenType
from modules.identity.models.user import User
from modules.identity.services.base import BaseService

logger = get_structured_logger(__name__)


class AuthService(BaseService[User]):
    """Service for authentication operations: login, MFA, SSO, tokens."""

    def __init__(self):
        super().__init__(User)

    # -- Password Authentication --

    async def authenticate_password(
        self, db: AsyncSession, email: str, password: str
    ) -> Optional[User]:
        """Authenticate user by email and password. Returns user if valid, None otherwise."""
        from modules.identity.services.user import UserService

        user_service = UserService()
        user = await user_service.get_by_email(db, email)

        if not user:
            # Still hash dummy password to avoid timing attacks
            await auth_service.passwords.verify(password, auth_service.passwords._dummy_hash)
            return None

        # Check if account is locked
        if user.locked_until and user.locked_until > datetime.now(UTC):
            logger.warning("Login blocked: account locked", user_id=user.id)
            return None

        # Verify password
        if not await auth_service.passwords.verify(password, user.password_hash):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.now(UTC) + timedelta(minutes=15)
            await db.flush()
            logger.warning("Login failed: invalid password", user_id=user.id)
            return None

        # Reset failed attempts
        user.failed_login_attempts = 0
        user.locked_until = None
        await db.flush()

        return user

    async def require_mfa(self, user: User) -> bool:
        """Check if user has MFA enabled."""
        return user.mfa_enabled

    async def generate_mfa_session(self, db: AsyncSession, user: User) -> str:
        """Generate a temporary session token for MFA verification."""
        import secrets

        token = secrets.token_urlsafe(32)
        # In production, store this in Redis with TTL of 5 minutes
        logger.info("MFA session generated", user_id=user.id)
        return token

    async def verify_mfa_code(self, user: User, code: str) -> bool:
        """Verify TOTP code for MFA."""
        if not user.mfa_secret:
            return False

        decrypted = auth_service.box.open(None, user.mfa_secret)
        if not decrypted:
            logger.warning("Could not decrypt MFA secret", user_id=user.id)
            return False

        settings = get_settings()
        step = auth_service.totp.check(settings, decrypted, code, user.mfa_last_step)

        if step is None:
            logger.warning("Invalid TOTP code", user_id=user.id)
            return False

        return True

    async def update_mfa_step(self, db: AsyncSession, user: User, step: int) -> User:
        """Update last used MFA step to prevent replay attacks."""
        user.mfa_last_step = step
        await db.flush()
        return user

    # -- SSO/OAuth --

    async def get_sso_connection(
        self, db: AsyncSession, provider: SSOProvider, provider_user_id: str
    ) -> Optional[SSOConnection]:
        """Fetch SSO connection by provider and provider user ID."""
        result = await db.execute(
            select(SSOConnection).where(
                and_(
                    SSOConnection.provider == provider.value,
                    SSOConnection.provider_user_id == provider_user_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def create_sso_connection(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        provider: SSOProvider,
        provider_user_id: str,
        provider_email: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        id_token: Optional[str] = None,
        token_expires_at: Optional[datetime] = None,
        profile_data: Optional[dict] = None,
    ) -> SSOConnection:
        """Create a new SSO connection for a user."""
        connection = SSOConnection(
            user_id=user_id,
            provider=provider.value,
            provider_user_id=provider_user_id,
            provider_email=provider_email,
            access_token=access_token,
            refresh_token=refresh_token,
            id_token=id_token,
            token_expires_at=token_expires_at,
            profile_data=profile_data or {},
        )
        db.add(connection)
        await db.flush()
        logger.info(
            "SSO connection created",
            user_id=user_id,
            provider=provider,
        )
        return connection

    async def update_sso_tokens(
        self,
        db: AsyncSession,
        connection: SSOConnection,
        access_token: str,
        refresh_token: Optional[str] = None,
        token_expires_at: Optional[datetime] = None,
    ) -> SSOConnection:
        """Update OAuth tokens for an SSO connection."""
        connection.access_token = access_token
        if refresh_token:
            connection.refresh_token = refresh_token
        if token_expires_at:
            connection.token_expires_at = token_expires_at
        connection.last_used_at = datetime.now(UTC)
        await db.flush()
        return connection

    # -- JWT Token Management --

    async def create_access_token(
        self, settings, user: User, session: UserSession
    ) -> str:
        """Generate JWT access token."""
        # Get user permissions
        scopes = ["user:read"]  # Base scope, would fetch from role in production
        return auth_service.jwt.access(
            settings,
            user.id,
            user.organization_id,
            scopes,
            session.id,
        )

    async def create_refresh_token(
        self, settings, user: User, session: UserSession, jti: str
    ) -> str:
        """Generate JWT refresh token."""
        return auth_service.jwt.refresh(settings, user.id, session.id, jti)

    async def decode_token(self, token: str) -> Optional[dict]:
        """Decode and verify JWT."""
        settings = get_settings()
        try:
            return auth_service.jwt.decode(token, settings.jwt_access_secret)
        except Exception as e:
            logger.warning("Token decode failed", error=str(e))
            return None

    # -- Email Verification --

    async def initiate_email_verification(
        self, db: AsyncSession, user: User
    ) -> tuple[OneTimeToken, str]:
        """Create email verification token."""
        from modules.identity.services.token import TokenService

        token_service = TokenService()
        settings = get_settings()
        return await token_service.create_token(
            db,
            user.id,
            TokenType.EMAIL_VERIFICATION,
            ttl_minutes=settings.email_code_ttl_minutes,
            email=user.email,
        )

    async def verify_email(self, db: AsyncSession, user: User) -> User:
        """Mark email as verified."""
        user.verification_status = "verified"
        await db.flush()
        logger.info("Email verified", user_id=user.id)
        return user

    # -- Password Reset --

    async def initiate_password_reset(
        self, db: AsyncSession, user: User
    ) -> tuple[OneTimeToken, str]:
        """Create password reset token."""
        from modules.identity.services.token import TokenService

        token_service = TokenService()
        settings = get_settings()
        return await token_service.create_token(
            db,
            user.id,
            TokenType.PASSWORD_RESET,
            ttl_minutes=settings.password_reset_ttl_minutes,
            email=user.email,
        )

    async def reset_password(self, db: AsyncSession, user: User, new_password: str) -> User:
        """Reset user password."""
        from modules.identity.services.user import UserService

        user_service = UserService()
        user = await user_service.set_password(db, user, new_password)
        logger.info("Password reset", user_id=user.id)
        return user
