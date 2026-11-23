"""Rate limiting, all in one place: fixed windows counted in Redis (or memory for tests), the
API-wide middleware, and the ``limit`` dependency for routes. Every limit is in settings."""

import time
import uuid
from dataclasses import dataclass
from typing import Annotated, Protocol

from fastapi import Depends, Request
from redis.asyncio import Redis

from core import auth
from core.api.dependencies import get_request_context
from core.api.exceptions import InvalidToken, RateLimitException, api_exception_handler
from core.api.response import Response
from core.audit import CoreAction, audit
from core.config import Settings
from core.database.isolation import bypass, scope_to
from core.logging import get_structured_logger

logger = get_structured_logger(__name__)


class Backend(Protocol):
    async def hit(self, key: str, window: int) -> tuple[int, int]:
        """Count one hit; return ``(hits in this window, seconds until the window resets)``."""

    async def close(self) -> None: ...


class RedisBackend:
    def __init__(self, url: str):
        self._redis = Redis.from_url(url, socket_connect_timeout=1, socket_timeout=1)

    async def hit(self, key: str, window: int) -> tuple[int, int]:
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, window, nx=True)  # only the first hit starts the window
            pipe.ttl(key)
            count, _, ttl = await pipe.execute()
        return int(count), max(int(ttl), 1)

    async def ping(self) -> bool:
        try:
            return bool(await self._redis.ping())
        except Exception:
            return False

    async def close(self) -> None:
        await self._redis.aclose()


class MemoryBackend:
    """Per-process counters: for tests, and a fallback that is better than no limit at all."""

    def __init__(self):
        self._windows: dict[str, tuple[int, float]] = {}

    async def hit(self, key: str, window: int) -> tuple[int, int]:
        now = time.monotonic()
        count, expires = self._windows.get(key, (0, now + window))
        if expires <= now:
            count, expires = 0, now + window
        self._windows[key] = (count + 1, expires)
        return count + 1, max(int(expires - now) + 1, 1)

    async def close(self) -> None:
        self._windows.clear()


@dataclass
class RateLimiter:
    backend: Backend
    enabled: bool = True

    async def check_all(self, settings: Settings, checks: list[tuple[str, str]]) -> None:
        """Run several ``(name, identity)`` checks against ``settings.rate_limits``.
        The first to trip raises."""
        for name, identity in checks:
            await self.check(name, identity, *settings.rate_limits[name])

    async def check(self, scope: str, identity: str, limit: int, window: int) -> None:
        """Raise a 429 once ``identity`` makes more than ``limit`` calls in ``window`` seconds."""
        if not self.enabled:
            return
        try:
            count, retry_after = await self.backend.hit(f"rl:{scope}:{identity}", window)
        except Exception as exc:  # Redis down: fail open
            logger.error("Rate limiter unavailable; allowing the request", error=str(exc))
            return
        if count > limit:
            exc = RateLimitException(
                "Too many requests; slow down and try again shortly",
                retry_after=retry_after,
                error_code="RATE_LIMITED",
            )
            exc.limit_name = scope
            exc.first_in_window = count == limit + 1  # only this one is written to the audit log
            raise exc


def build_limiter(url: str, enabled: bool) -> RateLimiter:
    return RateLimiter(RedisBackend(url), enabled)


# -- who is calling -------------------------------------------------------------------------------


def client_ip(request: Request) -> str:
    """The socket peer's address. Forwarding headers (X-Forwarded-For, ...) are never trusted:
    a client can write anything in them, which would let it pick its own rate-limit bucket."""
    return request.client.host if request.client else "-"


def _claims(request: Request) -> dict | None:
    """The claims of a validly signed access token, or None (anonymous or a bad token)."""
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        return None
    settings = request.app.state.settings
    try:
        return auth.service.jwt.decode(
            header[7:].strip(), settings.jwt_access_secret, settings.algorithm
        )
    except InvalidToken:
        return None


def caller(request: Request) -> str | None:
    """The user id in a validly signed access token, or None (anonymous or a bad token)."""
    claims = _claims(request)
    return str(claims["sub"]) if claims else None


def pair(request: Request) -> str:
    """Who is calling: user id and IP together, or just the IP when nobody is signed in.
    A stolen token or one address trying many accounts gets its own budget."""
    user = caller(request)
    ip = client_ip(request)
    return f"{user}:{ip}" if user else ip


# -- recording a rejection ------------------------------------------------------------------------


async def record_rejection(request: Request, exc: RateLimitException) -> None:
    """Write one ``security.rate_limited`` entry per caller and window (the first refusal).
    Never raises: if the log is down, the refusal goes to the error log instead."""
    if not getattr(exc, "first_in_window", False):
        return
    claims = _claims(request) or {}
    where = {"limit": exc.limit_name, "method": request.method, "route": request.url.path}
    try:
        organization_id = uuid.UUID(claims["org"]) if "org" in claims else None
        async with request.app.state.db.session_factory() as db:
            db.info["auditor"] = request.app.state.auditor
            db.info["request_context"] = get_request_context(request)
            if organization_id:
                await scope_to(db, organization_id)
            else:
                await bypass(db)  # anonymous: an entry of no organisation, for platform staff
            await audit(
                db, CoreAction.RATE_LIMITED, failure=True, organization_id=organization_id,
                actor_id=uuid.UUID(claims["sub"]) if "sub" in claims else None, **where,
            )  # fmt: skip
            await db.commit()
    except Exception as error:
        logger.error(
            "Rate limited, but the audit log could not record it", error=str(error), **where
        )


async def rate_limited_handler(request: Request, exc: RateLimitException):
    """Answer a 429 raised by a route's own limit, after recording it."""
    await record_rejection(request, exc)
    return await api_exception_handler(request, exc)


# -- the API-wide middleware and the per-route dependency -----------------------------------------


async def rate_limit(request: Request, call_next):
    """A ceiling on every API call: per user and address together when signed in (so people
    sharing an office never share one), else a flood guard per address."""
    if request.url.path.startswith("/api"):
        settings, limiter = request.app.state.settings, request.app.state.limiter
        signed_in = caller(request) is not None
        check = ("user", pair(request)) if signed_in else ("anonymous", client_ip(request))
        try:
            await limiter.check_all(settings, [check])
        except RateLimitException as exc:
            await record_rejection(request, exc)
            return Response.error(
                exc.message,
                429,
                error_code=exc.error_code,
                headers={"Retry-After": str(exc.retry_after)},
                retry_after=exc.retry_after,
            )
    return await call_next(request)


def limit(name: str, *, by_user: bool = False):
    """A route dependency enforcing ``settings.rate_limits[name]``.
    Counted per client IP, or with ``by_user`` per signed-in user and IP together."""

    async def dependency(request: Request) -> None:
        identity = pair(request) if by_user else client_ip(request)
        await request.app.state.limiter.check_all(request.app.state.settings, [(name, identity)])

    return Depends(dependency)


def get_limiter(request: Request) -> RateLimiter:
    return request.app.state.limiter


LimiterDep = Annotated[RateLimiter, Depends(get_limiter)]
