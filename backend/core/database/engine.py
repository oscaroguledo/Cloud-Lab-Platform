"""Database access: the async engine, resilient sessions, health checks and UTC-safe types."""

import asyncio
import os
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from sqlalchemy import DateTime, TypeDecorator, Uuid, select
from sqlalchemy.exc import DisconnectionError, OperationalError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.api.exceptions import DatabaseException
from core.config import Settings
from core.logging import get_structured_logger

logger = get_structured_logger(__name__)


class GUID(TypeDecorator):
    """A UUID column: native ``uuid`` on PostgreSQL, ``CHAR(36)`` elsewhere. Values are always
    ``uuid.UUID`` objects in Python."""

    impl = Uuid
    cache_ok = True


def uuid7() -> uuid.UUID:
    """A time-ordered (version 7) UUID: a millisecond timestamp then random bits.
    As a primary key, new rows land at the end of the index."""
    millis = time.time_ns() // 1_000_000
    rand = int.from_bytes(os.urandom(10), "big")
    value = (
        (millis & ((1 << 48) - 1)) << 80  # 48-bit timestamp
        | 0x7 << 76  # version 7
        | ((rand >> 68) & 0xFFF) << 64  # 12 random bits
        | 0b10 << 62  # RFC 4122 variant
        | (rand & ((1 << 62) - 1))  # 62 random bits
    )
    return uuid.UUID(int=value)


class UTCDateTime(TypeDecorator):
    """``DateTime(timezone=True)`` that treats a naive datetime as UTC.
    Drivers would read it as server-local time and could silently shift it."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

    def process_result_value(self, value, dialect):
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


def create_engine(settings: Settings) -> AsyncEngine:
    """Build the async engine (also used by the Alembic migration environment)."""
    url, connect_args = settings.async_database_url()
    # The session time zone is pinned to UTC on every connection: a naive datetime bound as a
    # timestamptz would otherwise be read in the server's zone before being stored.
    connect_args = {**connect_args, "server_settings": {"timezone": "UTC"}}
    return create_async_engine(
        url,
        connect_args=connect_args,
        echo=settings.db_echo,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=30,
    )


class DatabaseManager:
    """Owns the engine and session factory, with connection retry and health checks.
    One instance lives on ``app.state.db``; handlers get sessions through ``get_db``."""

    def __init__(self, settings: Settings):
        self.engine: AsyncEngine = create_engine(settings)
        # expire_on_commit=False keeps loaded attributes usable after commit; async sessions
        # cannot lazy-load, so everything a response needs is loaded eagerly.
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)
        self._connection_failures = 0
        self._last_health_check = 0.0

    async def dispose(self) -> None:
        await self.engine.dispose()

    async def health_check(self) -> dict:
        """Run a trivial query and report latency and failure count."""
        start = time.perf_counter()
        try:
            async with self.session_factory() as session:
                await session.execute(select(1))
            response_time = (time.perf_counter() - start) * 1000
            self._connection_failures = 0
            self._last_health_check = time.time()
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "connection_failures": self._connection_failures,
                "last_check": self._last_health_check,
            }
        except Exception as exc:
            self._connection_failures += 1
            logger.error(
                "Database health check failed",
                connection_failures=self._connection_failures,
                exception=exc,
            )
            return {
                "status": "unhealthy",
                "response_time_ms": round((time.perf_counter() - start) * 1000, 2),
                "connection_failures": self._connection_failures,
                "error": type(exc).__name__,
                "last_check": time.time(),
            }

    @asynccontextmanager
    async def session_with_retry(
        self, max_retries: int = 3, retry_delay: float = 1.0, backoff_factor: float = 2.0
    ) -> AsyncIterator[AsyncSession]:
        """Yield a session with an established connection, retrying with exponential backoff.
        Only acquiring the connection is retried; the caller's work is never re-run."""
        session = self.session_factory()
        attempt = 0
        while True:
            try:
                await session.connection()  # checks a connection out of the pool (and pings it)
                break
            except (DisconnectionError, OperationalError, OSError) as exc:
                self._connection_failures += 1
                if attempt == max_retries:
                    await session.close()
                    logger.error(
                        "Database connection failed",
                        attempts=attempt + 1,
                        total_failures=self._connection_failures,
                        exception=exc,
                    )
                    raise DatabaseException(
                        f"Database unavailable after {max_retries + 1} attempts"
                    ) from exc
                delay = retry_delay * backoff_factor**attempt
                logger.warning(
                    "Database connection failed, retrying",
                    attempt=attempt + 1,
                    retry_in=f"{delay}s",
                    error=type(exc).__name__,
                )
                await asyncio.sleep(delay)
                attempt += 1
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
