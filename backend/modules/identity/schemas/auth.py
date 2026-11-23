"""Authentication schemas for login, MFA, SSO, and token operations."""

from typing import Optional

from pydantic import EmailStr, Field

from modules.identity.schemas.base import BaseSchema


class LoginRequest(BaseSchema):
    """Request for email/password authentication."""

    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="User password")
    device_name: Optional[str] = Field(None, max_length=255)
    device_hash: Optional[str] = Field(None, description="Browser fingerprint")


class LoginResponse(BaseSchema):
    """Response after successful login."""

    access_token: str
    refresh_token: str
    user_id: str
    mfa_required: bool
    mfa_method: Optional[str] = None  # "totp", "email", "sms", etc.


class MFAVerifyRequest(BaseSchema):
    """Request to verify MFA code."""

    code: str = Field(..., min_length=6, max_length=6, description="6-digit TOTP code")
    session_token: str = Field(..., description="Temporary session token")


class MFAVerifyResponse(BaseSchema):
    """Response after MFA verification."""

    access_token: str
    refresh_token: str
    success: bool


class MFASetupRequest(BaseSchema):
    """Request to enable MFA."""

    password: str = Field(..., description="User password for verification")


class MFASetupResponse(BaseSchema):
    """Response with MFA setup info."""

    secret: str = Field(..., description="Base32 encoded secret for authenticator app")
    qr_code_url: str = Field(..., description="QR code URL for easy scanning")
    recovery_codes: list[str] = Field(..., description="Recovery codes if device is lost")


class MFADisableRequest(BaseSchema):
    """Request to disable MFA."""

    code: str = Field(..., min_length=6, max_length=6, description="Current 6-digit TOTP code")
    password: str = Field(..., description="User password for verification")


class RefreshTokenRequest(BaseSchema):
    """Request to refresh access token."""

    refresh_token: str


class RefreshTokenResponse(BaseSchema):
    """Response with new access token."""

    access_token: str
    expires_in: int


class SSOCallbackRequest(BaseSchema):
    """OAuth callback parameters."""

    provider: str = Field(..., description="SSO provider name")
    code: str = Field(..., description="Authorization code from provider")
    state: str = Field(..., description="State parameter for CSRF protection")
    redirect_uri: Optional[str] = None


class SSOCallbackResponse(BaseSchema):
    """Response after SSO callback."""

    access_token: str
    refresh_token: str
    user_id: str
    is_new_user: bool
    mfa_required: bool


class SSOConnectionResponse(BaseSchema):
    """Response containing SSO connection info."""

    provider: str
    provider_email: str
    connected_at: str
    last_used_at: Optional[str] = None


class LogoutRequest(BaseSchema):
    """Request to logout."""

    all_devices: bool = Field(False, description="Logout all devices")
    reason: Optional[str] = Field(None, max_length=255)


class PasswordChangeRequest(BaseSchema):
    """Request to change password."""

    current_password: str
    new_password: str = Field(..., min_length=8, description="New password")
    confirm_password: str = Field(..., description="Password confirmation")


class PasswordResetRequestSchema(BaseSchema):
    """Request to initiate password reset."""

    email: EmailStr = Field(..., description="Email for password reset")


class PasswordResetConfirmSchema(BaseSchema):
    """Request to confirm password reset with token."""

    token: str = Field(..., description="Password reset token from email")
    new_password: str = Field(..., min_length=8)
    confirm_password: str


class EmailVerificationRequest(BaseSchema):
    """Request to verify email."""

    token: str = Field(..., description="Email verification token from email link")


class EmailVerificationResendRequest(BaseSchema):
    """Request to resend email verification."""

    email: EmailStr


class TokenPair(BaseSchema):
    access_token: str
    refresh_token: str
    expires_in: int  # access token lifetime in seconds
