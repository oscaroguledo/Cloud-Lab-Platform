"""API layer: exceptions, pagination, response formatting, and handlers."""

from core.api.exceptions import (
    APIException,
    AuthenticationException,
    AuthorizationException,
    BadRequestException,
    ConflictException,
    DatabaseException,
    InvalidToken,
    MissingBearer,
    MissingPermission,
    NotFoundException,
    RateLimitException,
    install_exception_handlers,
)
from core.api.pagination import Envelope, Page, PageParams, Pagination, get_pagination
from core.api.response import Response

__all__ = [
    "APIException",
    "AuthenticationException",
    "AuthorizationException",
    "BadRequestException",
    "ConflictException",
    "DatabaseException",
    "InvalidToken",
    "MissingBearer",
    "MissingPermission",
    "NotFoundException",
    "RateLimitException",
    "install_exception_handlers",
    "Response",
    "Page",
    "PageParams",
    "Pagination",
    "Envelope",
    "get_pagination",
]
