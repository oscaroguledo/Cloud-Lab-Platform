"""FastAPI request context and dependency extraction."""

import uuid
from fastapi import Request


def get_request_context(request: Request) -> dict:
    """Extract request context for audit logging and diagnostics."""
    return {
        "method": request.method,
        "path": request.url.path,
        "client_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }
