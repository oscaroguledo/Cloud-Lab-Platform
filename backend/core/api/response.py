"""Small response helpers shared by the API and exception handlers."""

from datetime import UTC, datetime
from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


class Response(JSONResponse):
    """Build consistent JSON responses without coupling routes to serialization details."""

    @staticmethod
    def success(
        data: Any = None,
        message: str = "Request completed successfully",
        status_code: int = 200,
    ) -> "Response":
        return Response(
            status_code=status_code,
            content={
                "success": True,
                "message": message,
                "data": jsonable_encoder(data),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

    @staticmethod
    def error(
        message: str,
        status_code: int,
        *,
        error_code: str,
        detail: Any = None,
        headers: dict[str, str] | None = None,
        **extra: Any,
    ) -> JSONResponse:
        content = {
            "success": False,
            "message": message,
            "error_code": error_code,
            "timestamp": datetime.now(UTC).isoformat(),
            "detail": detail,
            **extra,
        }
        return Response(status_code=status_code, content=content, headers=headers)

    @staticmethod
    def message(message: str, status_code: int = 200) -> "Response":
        return Response(
            status_code=status_code,
            content={
                "success": True,
                "message": message,
                "data": None,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
