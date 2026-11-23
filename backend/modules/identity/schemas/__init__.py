"""Identity schemas: request/response validation and serialization."""

from modules.identity.schemas.auth import (
    EmailVerificationRequest,
    EmailVerificationResendRequest,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    MFADisableRequest,
    MFASetupRequest,
    MFASetupResponse,
    MFAVerifyRequest,
    MFAVerifyResponse,
    PasswordChangeRequest,
    PasswordResetConfirmSchema,
    PasswordResetRequestSchema,
    RefreshTokenRequest,
    RefreshTokenResponse,
)
from modules.identity.schemas.base import BaseSchema, PaginatedResponse
from modules.identity.schemas.organization import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
)
from modules.identity.schemas.permission import (
    PermissionCreate,
    PermissionResponse,
    PermissionUpdate,
)
from modules.identity.schemas.role import RoleCreate, RoleResponse, RoleUpdate
from modules.identity.schemas.session import (
    SessionCreate,
    SessionListResponse,
    SessionLogoutRequest,
    SessionResponse,
    SessionRevokeRequest,
    SessionUpdate,
)
from modules.identity.schemas.sso import (
    SSOAuthorizationRequest,
    SSOAuthorizationResponse,
    SSOConnectionCreate,
    SSOConnectionRemove,
    SSOConnectionResponse,
    SSOListResponse,
    SSOTokenExchangeRequest,
    SSOUserInfo,
)
from modules.identity.schemas.token import OneTimeTokenCreate, OneTimeTokenResponse
from modules.identity.schemas.user import UserCreate, UserResponse, UserUpdate

__all__ = [
    # Base
    "BaseSchema",
    "PaginatedResponse",
    # Auth
    "LoginRequest",
    "LoginResponse",
    "MFAVerifyRequest",
    "MFAVerifyResponse",
    "MFASetupRequest",
    "MFASetupResponse",
    "MFADisableRequest",
    "RefreshTokenRequest",
    "RefreshTokenResponse",
    "LogoutRequest",
    "PasswordChangeRequest",
    "PasswordResetRequestSchema",
    "PasswordResetConfirmSchema",
    "EmailVerificationRequest",
    "EmailVerificationResendRequest",
    # SSO
    "SSOAuthorizationRequest",
    "SSOAuthorizationResponse",
    "SSOTokenExchangeRequest",
    "SSOUserInfo",
    "SSOConnectionCreate",
    "SSOConnectionRemove",
    "SSOConnectionResponse",
    "SSOListResponse",
    # User
    "UserCreate",
    "UserResponse",
    "UserUpdate",
    # Organization
    "OrganizationCreate",
    "OrganizationResponse",
    "OrganizationUpdate",
    # Role
    "RoleCreate",
    "RoleResponse",
    "RoleUpdate",
    # Permission
    "PermissionCreate",
    "PermissionResponse",
    "PermissionUpdate",
    # Session
    "SessionCreate",
    "SessionResponse",
    "SessionUpdate",
    "SessionListResponse",
    "SessionRevokeRequest",
    "SessionLogoutRequest",
    # Token
    "OneTimeTokenCreate",
    "OneTimeTokenResponse",
]
