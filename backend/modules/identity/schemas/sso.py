"""SSO/OAuth schemas."""

import uuid
from typing import Optional

from pydantic import Field

from modules.identity.schemas.base import BaseSchema, UUIDSchema


class SSOProviderConfig(BaseSchema):
    """SSO provider configuration."""

    provider: str = Field(..., description="Provider name: google, github, microsoft, okta, auth0")
    client_id: str = Field(..., description="OAuth client ID")
    client_secret: str = Field(..., description="OAuth client secret")
    authorization_url: str = Field(..., description="Authorization endpoint URL")
    token_url: str = Field(..., description="Token endpoint URL")
    userinfo_url: str = Field(..., description="User info endpoint URL")
    scopes: list[str] = Field(default_factory=list, description="OAuth scopes to request")


class SSOAuthorizationRequest(BaseSchema):
    """Request to initiate SSO flow."""

    provider: str = Field(..., description="SSO provider name")
    redirect_uri: str = Field(..., description="Redirect URI after auth")


class SSOAuthorizationResponse(BaseSchema):
    """Response with authorization URL."""

    authorization_url: str = Field(..., description="URL to redirect user to")
    state: str = Field(..., description="State parameter for CSRF protection")


class SSOTokenExchangeRequest(BaseSchema):
    """Request to exchange authorization code for tokens."""

    provider: str
    code: str = Field(..., description="Authorization code")
    state: str = Field(..., description="State parameter")
    redirect_uri: str


class SSOUserInfo(BaseSchema):
    """User information from SSO provider."""

    provider_user_id: str
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None
    email_verified: bool = False


class SSOConnectionCreate(BaseSchema):
    """Request to link an SSO provider."""

    provider: str = Field(..., description="SSO provider name")
    access_token: str = Field(..., description="Access token from provider")


class SSOConnectionRemove(BaseSchema):
    """Request to unlink an SSO provider."""

    provider: str = Field(..., description="Provider to unlink")
    password: Optional[str] = Field(None, description="Password confirmation if no other auth")


class SSOListResponse(BaseSchema):
    """Response with user's SSO connections."""

    connections: list["SSOConnectionResponse"]


class SSOConnectionResponse(UUIDSchema):
    """Response containing SSO connection info."""

    provider: str
    provider_email: str
    connected_at: str
    last_used_at: Optional[str] = None
    is_primary: bool = False
