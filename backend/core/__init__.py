"""Cloud Lab Platform backend core: configuration, database, auth, logging, and API utilities."""

from core.api.dependencies import CurrentUser, Database, get_current_user, get_db, get_request_context
from core.auth import service as auth_service
from core.config import Settings, get_settings
from core.database.engine import DatabaseManager, GUID, UTCDateTime, uuid7
from core.logging import get_structured_logger

__all__ = [
    "auth_service",
    "get_settings",
    "Settings",
    "DatabaseManager",
    "GUID",
    "UTCDateTime",
    "uuid7",
    "get_structured_logger",
    "get_current_user",
    "get_db",
    "get_request_context",
    "CurrentUser",
    "Database",
]
