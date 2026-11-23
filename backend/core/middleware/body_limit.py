"""Reject oversized request bodies before they are read into memory (HTTP 413)."""

import re

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from core.api.response import Response


class BodyLimitMiddleware:
    """Pure ASGI, so it can stop a chunked upload as it streams, not just trust Content-Length.
    ``large_routes`` are path patterns allowed the bigger cap (see ``large_body_routes``)."""

    def __init__(
        self,
        app: ASGIApp,
        max_bytes: int,
        large_bytes: int | None = None,
        large_routes: tuple[str, ...] = (),
    ):
        self.app = app
        self.max_bytes = max_bytes
        self.large_bytes = large_bytes or max_bytes
        self.large_routes = [re.compile(pattern) for pattern in large_routes]

    def _limit_for(self, path: str) -> int:
        """The cap for this path: higher for the few routes that accept long lists."""
        if any(route.fullmatch(path) for route in self.large_routes):
            return self.large_bytes
        return self.max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        max_bytes = self._limit_for(scope["path"])
        declared = dict(scope["headers"]).get(b"content-length")
        if declared and declared.isdigit() and int(declared) > max_bytes:
            return await self._reject(scope, receive, send, max_bytes)

        if declared is not None:
            # The server already enforces a declared length, so this much is all that can arrive.
            return await self.app(scope, receive, send)

        # A chunked upload has no Content-Length: read it here up to the cap, then replay it, so the
        # 413 is decided before the framework can turn a read error into a 400.
        messages: list[Message] = []
        seen = 0
        while True:
            message = await receive()
            messages.append(message)
            if message["type"] != "http.request":
                break  # the client went away
            seen += len(message.get("body", b""))
            if seen > max_bytes:
                return await self._reject(scope, receive, send, max_bytes)
            if not message.get("more_body", False):
                break

        replay = iter(messages)

        async def replayed() -> Message:
            return next(replay, None) or await receive()

        await self.app(scope, replayed, send)

    async def _reject(self, scope: Scope, receive: Receive, send: Send, max_bytes: int) -> None:
        response = Response.error(
            f"Request body is larger than {max_bytes} bytes",
            413,
            error_code="PAYLOAD_TOO_LARGE",
        )
        await response(scope, receive, send)
