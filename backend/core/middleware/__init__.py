"""Every HTTP middleware, installed in one place. A request passes them in reverse order of
installation: request log, rate limit, security headers, trusted hosts, body cap, then CORS."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import Settings
from core.middleware.body_limit import BodyLimitMiddleware
from core.middleware.rate_limit import rate_limit
from core.middleware.request_log import request_log
from core.middleware.security import security_headers


def add_middleware(app: FastAPI, settings: Settings) -> None:
    # Any origin in development; only the frontend in production. Credentials need an explicit
    # origin list (browsers reject "*" together with credentials).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.is_production,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(
        BodyLimitMiddleware,
        max_bytes=settings.max_request_body_bytes,
        large_bytes=settings.max_large_body_bytes,
        large_routes=settings.large_body_routes,
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_host_list or ["*"])
    for dispatch in (security_headers, rate_limit, request_log):
        app.add_middleware(BaseHTTPMiddleware, dispatch=dispatch)
