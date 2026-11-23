"""OAuth callback handler for Google and Microsoft SSO."""

import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_structured_logger
from modules.identity.models.sso import SSOProvider
from modules.identity.models.user import User
from modules.identity.services.auth import AuthService
from modules.identity.services.user import UserService

logger = get_structured_logger(__name__)


class OAuthUserInfo:
    """Standardized user info from OAuth provider."""

    def __init__(
        self,
        provider_user_id: str,
        email: str,
        name: str,
        picture_url: Optional[str] = None,
        email_verified: bool = False,
    ):
        self.provider_user_id = provider_user_id
        self.email = email
        self.name = name
        self.picture_url = picture_url
        self.email_verified = email_verified


class OAuthHandler:
    """Handle OAuth callbacks from Google and Microsoft."""

    def __init__(self):
        self.auth_service = AuthService()
        self.user_service = UserService()

    async def handle_google_callback(
        self, db: AsyncSession, user_info: OAuthUserInfo, org_id: uuid.UUID
    ) -> tuple[User, bool]:
        """
        Handle Google OAuth callback.
        Returns: (user, is_new_user)
        """
        return await self._handle_oauth_callback(
            db, SSOProvider.GOOGLE, user_info, org_id
        )

    async def handle_microsoft_callback(
        self, db: AsyncSession, user_info: OAuthUserInfo, org_id: uuid.UUID
    ) -> tuple[User, bool]:
        """
        Handle Microsoft/Azure AD OAuth callback.
        Returns: (user, is_new_user)
        """
        return await self._handle_oauth_callback(
            db, SSOProvider.MICROSOFT, user_info, org_id
        )

    async def _handle_oauth_callback(
        self,
        db: AsyncSession,
        provider: SSOProvider,
        user_info: OAuthUserInfo,
        org_id: uuid.UUID,
    ) -> tuple[User, bool]:
        """
        Generic OAuth callback handler.

        Flow:
        1. Check if SSO connection exists → user exists
        2. If not, check if email exists → link to existing user
        3. If not, create new user and SSO connection
        """
        # Step 1: Check for existing SSO connection
        sso_conn = await self.auth_service.get_sso_connection(
            db, provider, user_info.provider_user_id
        )

        if sso_conn:
            # User already has this provider linked
            logger.info(
                "SSO login via existing connection",
                provider=provider,
                user_id=sso_conn.user_id,
            )
            user = await self.user_service.get_by_id(db, sso_conn.user_id)
            return user, False

        # Step 2: Check if email exists
        existing_user = await self.user_service.get_by_email(db, user_info.email)

        if existing_user:
            # Link this SSO provider to existing user
            logger.info(
                "SSO linked to existing user",
                provider=provider,
                user_id=existing_user.id,
            )
            await self.auth_service.create_sso_connection(
                db,
                existing_user.id,
                provider,
                user_info.provider_user_id,
                user_info.email,
                profile_data={"name": user_info.name, "picture": user_info.picture_url},
            )
            return existing_user, False

        # Step 3: Create new user
        logger.info("New user created via SSO", provider=provider, email=user_info.email)

        # Parse name into first/last
        names = user_info.name.split(" ", 1) if user_info.name else ["User", ""]
        first_name = names[0]
        last_name = names[1] if len(names) > 1 else ""

        # Create user with temporary password (never used)
        import secrets

        temp_password = secrets.token_urlsafe(32)
        new_user = await self.user_service.create_with_password(
            db,
            email=user_info.email,
            password=temp_password,
            first_name=first_name or "User",
            last_name=last_name or "",
            organization_id=org_id,
            role_id=uuid.uuid4(),  # Would be fetched from org's default role
            verification_status="verified" if user_info.email_verified else "unverified",
            avatar_url=user_info.picture_url,
        )

        # Create SSO connection
        await self.auth_service.create_sso_connection(
            db,
            new_user.id,
            provider,
            user_info.provider_user_id,
            user_info.email,
            profile_data={"name": user_info.name, "picture": user_info.picture_url},
        )

        return new_user, True


# Provider configurations
GOOGLE_CONFIG = {
    "client_id": "YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com",
    "client_secret": "YOUR_GOOGLE_CLIENT_SECRET",
    "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth",
    "token_url": "https://oauth2.googleapis.com/token",
    "userinfo_url": "https://openidconnect.googleapis.com/v1/userinfo",
    "scopes": ["openid", "email", "profile"],
}

MICROSOFT_CONFIG = {
    "tenant": "common",  # or your specific tenant ID
    "client_id": "YOUR_AZURE_CLIENT_ID",
    "client_secret": "YOUR_AZURE_CLIENT_SECRET",
    "authorization_url": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize",
    "token_url": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
    "userinfo_url": "https://graph.microsoft.com/v1.0/me",
    "scopes": ["openid", "email", "profile"],
}
