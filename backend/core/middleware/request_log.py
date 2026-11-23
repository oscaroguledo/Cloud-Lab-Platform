"""One log line per request with its status and latency (uvicorn's access log is turned off)."""

import time

from fastapi import Request

from core.logging import get_structured_logger

logger = get_structured_logger(__name__)


async def request_log(request: Request, call_next):
    start = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        if status_code >= 500:
            emit = logger.error
        elif status_code >= 400:
            emit = logger.warning
        else:
            emit = logger.info
        emit(
            "request",
            method=request.method,
            path=request.url.path,
            status=status_code,
            latency=f"{(time.perf_counter() - start) * 1000:.2f}ms",
            ip=request.client.host if request.client else "-",
        )
