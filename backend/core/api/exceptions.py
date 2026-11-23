"""Uniform API errors: the exception classes and the handlers that render every failure.
Every error has the shape {"success", "message", "error_code", "timestamp", "detail"}."""

from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.api.response import Response
from core.logging import get_structured_logger

logger = get_structured_logger(__name__)


def _now() -> str:
    return datetime.now(UTC).isoformat()


class APIException(HTTPException):
    """Base API exception with a message, a machine-readable error code and a timestamp."""

    def __init__(
        self,
        status_code: int,
        message: str = "An unexpected API error occurred",
        detail: str | None = None,
        error_code: str | None = None,
        **kwargs: Any,
    ):
        self.message = message
        self.detail = detail or message
        self.error_code = error_code or f"ERR_{status_code}"
        self.timestamp = _now()
        super().__init__(status_code=status_code, detail=self.detail, **kwargs)


class BadRequestException(APIException):
    """Exception for requests that are well-formed but break a business rule."""

    def __init__(self, message: str = "Bad request", error_code: str | None = None):
        super().__init__(status_code=400, message=message, error_code=error_code or "BAD_REQUEST")


class AuthenticationException(APIException):
    """Exception for authentication errors."""

    def __init__(self, message: str = "Authentication failed", error_code: str | None = None):
        super().__init__(status_code=401, message=message, error_code=error_code or "AUTH_ERROR")


class AuthorizationException(APIException):
    """Exception for authorization errors."""

    def __init__(self, message: str = "Access denied", error_code: str | None = None):
        super().__init__(
            status_code=403, message=message, error_code=error_code or "AUTHORIZATION_ERROR"
        )


class NotFoundException(APIException):
    """Exception for resource not found errors."""

    def __init__(
        self,
        message: str = "Resource not found",
        resource: str | None = None,
        error_code: str | None = None,
    ):
        self.resource = resource
        super().__init__(status_code=404, message=message, error_code=error_code or "NOT_FOUND")


class ConflictException(APIException):
    """Exception for conflict errors."""

    def __init__(self, message: str = "Resource conflict", error_code: str | None = None):
        super().__init__(
            status_code=409, message=message, error_code=error_code or "CONFLICT_ERROR"
        )


class RateLimitException(APIException):
    """Exception for rate limiting errors."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int | None = None,
        error_code: str | None = None,
    ):
        self.retry_after = retry_after
        super().__init__(
            status_code=429, message=message, error_code=error_code or "RATE_LIMIT_ERROR"
        )


class DatabaseException(APIException):
    """Exception for database errors."""

    def __init__(self, message: str = "Database error occurred", error_code: str | None = None):
        super().__init__(
            status_code=500, message=message, error_code=error_code or "DATABASE_ERROR"
        )


# -- Errors every module and service shares (token handling) ------------------------------------


class InvalidToken(AuthenticationException):
    def __init__(self):
        super().__init__("Invalid or expired token", error_code="INVALID_TOKEN")


class MissingBearer(AuthenticationException):
    def __init__(self):
        super().__init__("Missing bearer token", error_code="MISSING_TOKEN")


class MissingPermission(AuthorizationException):
    def __init__(self, scope: str):
        super().__init__(f"Missing permission: {scope}", error_code="MISSING_PERMISSION")


# -- Handlers ------------------------------------------------------------------------------------


async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """Handle custom API exceptions."""
    extra: dict[str, Any] = {}
    for name in ("errors", "resource", "retry_after", "service"):
        value = getattr(exc, name, None)
        if value is not None:
            extra[name] = value
    return Response.error(
        exc.message,
        exc.status_code,
        error_code=exc.error_code,
        detail=exc.detail if exc.detail != exc.message else None,
        headers={"Retry-After": str(extra["retry_after"])} if "retry_after" in extra else None,
        **extra,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle standard HTTP exceptions (unknown route, wrong method, ...)."""
    return Response.error(
        str(exc.detail),
        exc.status_code,
        error_code=f"HTTP_{exc.status_code}",
        headers=getattr(exc, "headers", None),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle request validation errors, reporting each failing field."""
    errors = {}
    for error in exc.errors():
        loc = error["loc"]
        errors[".".join(str(part) for part in loc[1:]) or str(loc[0])] = error["msg"]
    return Response.error(
        "Validation failed",
        422,
        error_code="VALIDATION_ERROR",
        errors=errors,
    )


async def response_validation_exception_handler(
    request: Request, exc: ResponseValidationError
) -> JSONResponse:
    """Report contract failures without exposing internal response values."""
    logger.error("Response validation error", exception=exc)
    return Response.error(
        "The server returned an invalid response",
        500,
        error_code="RESPONSE_VALIDATION_ERROR",
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle database errors without leaking their details to the client."""
    logger.error("Database error", exception=exc)
    return Response.error(
        "A database error occurred",
        500,
        error_code="DATABASE_ERROR",
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.error("Unhandled error", exception=exc)
    return Response.error(
        "An unexpected error occurred",
        500,
        error_code="INTERNAL_ERROR",
    )


def install_exception_handlers(app: FastAPI) -> None:
    """Register every handler so all errors share one response shape."""
    app.add_exception_handler(APIException, api_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ResponseValidationError, response_validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
