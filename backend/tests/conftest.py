"""
Pytest configuration and shared fixtures for Cloud Lab Platform tests.
"""

import asyncio
import uuid
from typing import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from core.config import Settings
from core.database.engine import DatabaseManager
from modules.identity.models.base import Base


# ============================================================================
# Settings & Configuration
# ============================================================================

@pytest.fixture
def test_settings() -> Settings:
    """Provide test configuration."""
    return Settings(
        environment="test",
        app_name="Test App",
        database_url="sqlite+aiosqlite:///:memory:",
        jwt_access_secret="test-secret-at-least-32-characters-long",
        jwt_refresh_secret="test-refresh-secret-at-least-32-chars",
        redis_url="redis://localhost:6379/1",  # Use DB 1 for tests
        rate_limit_enabled=False,
        mfa_secret_key="test-mfa-key-at-least-32-characters",
        brevo_api_key="",  # Skip email in tests
    )


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
async def async_engine(test_settings: Settings):
    """Create test database engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide test database session."""
    async_session_maker = DatabaseManager(Settings(
        environment="test",
        database_url="sqlite+aiosqlite:///:memory:",
        jwt_access_secret="test" * 8,
        jwt_refresh_secret="test" * 8,
    )).session_factory

    async with async_session_maker() as session:
        yield session
        await session.rollback()


# ============================================================================
# User Fixtures
# ============================================================================

@pytest.fixture
async def test_organization(async_session: AsyncSession):
    """Create test organization."""
    from modules.identity.models.organization import Organization

    org = Organization(
        id=uuid.uuid4(),
        name="Test Organization",
        description="For testing",
    )
    async_session.add(org)
    await async_session.flush()
    return org


@pytest.fixture
async def test_role(async_session: AsyncSession, test_organization):
    """Create test role."""
    from modules.identity.models.role import Role

    role = Role(
        id=uuid.uuid4(),
        name="Test Role",
        organization_id=test_organization.id,
        description="For testing",
    )
    async_session.add(role)
    await async_session.flush()
    return role


@pytest.fixture
async def test_user(async_session: AsyncSession, test_organization, test_role):
    """Create test user."""
    from modules.identity.models.user import User
    from core.auth import service as auth_service

    password_hash = await auth_service.passwords.hash("Test@123")

    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        first_name="Test",
        last_name="User",
        password_hash=password_hash,
        organization_id=test_organization.id,
        role_id=test_role.id,
        account_status="active",
        verification_status="verified",
    )
    async_session.add(user)
    await async_session.flush()
    return user


@pytest.fixture
async def test_session(async_session: AsyncSession, test_user):
    """Create test session."""
    from modules.identity.models.session import UserSession
    from datetime import UTC, datetime, timedelta

    session = UserSession(
        id=uuid.uuid4(),
        user_id=test_user.id,
        is_active=True,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    async_session.add(session)
    await async_session.flush()
    return session


# ============================================================================
# Service Fixtures
# ============================================================================

@pytest.fixture
def auth_service():
    """Provide auth service."""
    from modules.identity.services.auth import AuthService
    return AuthService()


@pytest.fixture
def user_service():
    """Provide user service."""
    from modules.identity.services.user import UserService
    return UserService()


@pytest.fixture
def organization_service():
    """Provide organization service."""
    from modules.identity.services.organization import OrganizationService
    return OrganizationService()


@pytest.fixture
def role_service():
    """Provide role service."""
    from modules.identity.services.role import RoleService
    return RoleService()


@pytest.fixture
def permission_service():
    """Provide permission service."""
    from modules.identity.services.permission import PermissionService
    return PermissionService()


@pytest.fixture
def session_service():
    """Provide session service."""
    from modules.identity.services.session import SessionService
    return SessionService()


@pytest.fixture
def token_service():
    """Provide token service."""
    from modules.identity.services.token import TokenService
    return TokenService()


# ============================================================================
# Event Loop
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
