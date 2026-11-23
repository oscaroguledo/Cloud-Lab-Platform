# Test Suite - Cloud Lab Platform

Comprehensive test suite for the Cloud Lab Platform identity and access management system.

## Overview

```
tests/
├── conftest.py                          # Shared fixtures and configuration
├── modules/
│   └── identity/
│       ├── models/                      # Model tests
│       ├── services/                    # Service layer tests
│       │   ├── test_auth_service.py     # Auth flows, MFA, SSO
│       │   ├── test_user_service.py     # User management
│       │   ├── test_session_service.py  # Session lifecycle
│       │   └── test_token_service.py    # Token operations
│       ├── schemas/                     # Schema validation tests
│       └── integration/                 # End-to-end tests
└── README.md                            # This file
```

## Running Tests

### All Tests
```bash
pytest
```

### Specific Test File
```bash
pytest backend/tests/modules/identity/services/test_auth_service.py
```

### By Marker
```bash
# Auth tests only
pytest -m auth

# MFA tests
pytest -m mfa

# OAuth/SSO tests
pytest -m oauth

# Database tests
pytest -m db
```

### With Coverage
```bash
pytest --cov=backend --cov-report=html
# View report: open htmlcov/index.html
```

### Verbose Output
```bash
pytest -v
pytest -vv  # Very verbose with timing
```

### Stop on First Failure
```bash
pytest -x
```

### Show Slowest Tests
```bash
pytest --durations=10
```

## Test Markers

Tests are organized with markers for easy filtering:

| Marker | Purpose |
|--------|---------|
| `@pytest.mark.unit` | Fast, isolated tests |
| `@pytest.mark.integration` | Slower, database tests |
| `@pytest.mark.auth` | Authentication tests |
| `@pytest.mark.oauth` | OAuth/SSO tests |
| `@pytest.mark.mfa` | MFA/TOTP tests |
| `@pytest.mark.security` | Security-related tests |
| `@pytest.mark.slow` | Slow running tests |
| `@pytest.mark.db` | Database-dependent tests |

## Fixtures

Shared fixtures defined in `conftest.py`:

### Configuration
- `test_settings` – Test environment configuration
- `async_engine` – Test database engine
- `async_session` – Test database session

### Models
- `test_organization` – Test organization
- `test_role` – Test role
- `test_user` – Test user (email: test@example.com)
- `test_session` – Test session

### Services
- `auth_service` – AuthService instance
- `user_service` – UserService instance
- `organization_service` – OrganizationService instance
- `role_service` – RoleService instance
- `permission_service` – PermissionService instance
- `session_service` – SessionService instance
- `token_service` – TokenService instance

### Usage Example
```python
@pytest.mark.asyncio
async def test_something(async_session, test_user, user_service):
    """Test that uses injected fixtures."""
    result = await user_service.get_by_id(async_session, test_user.id)
    assert result is not None
```

## Test Organization

### AuthService Tests (`test_auth_service.py`)
- ✅ Password authentication (valid, invalid, locked account)
- ✅ MFA verification (TOTP code, invalid code, not enabled)
- ✅ SSO management (create, retrieve connections)
- ✅ Token generation and decoding
- ✅ Account lockout after failed attempts

### UserService Tests (`test_user_service.py`)
- ✅ User CRUD operations
- ✅ Email lookup
- ✅ Password hashing and verification
- ✅ Password changes
- ✅ MFA setup and teardown
- ✅ Login recording
- ✅ Organization member listing

### SessionService Tests (`test_session_service.py`)
- ✅ Session creation with device tracking
- ✅ Active session retrieval
- ✅ Session revocation
- ✅ Bulk revocation (all user sessions)
- ✅ Activity timestamp updates
- ✅ Session listing and filtering

### TokenService Tests (`test_token_service.py`)
- ✅ Token creation with TTL
- ✅ Token verification
- ✅ Token type validation
- ✅ Attempt tracking
- ✅ Token usage marking
- ✅ Expired token cleanup

## Test Data

### Default Test User
- Email: `test@example.com`
- Password: `Test@123`
- Status: Active and Verified
- MFA: Disabled (can be enabled in test)

### Default Test Organization
- Name: `Test Organization`
- Description: `For testing`

### Default Test Role
- Name: `Test Role`
- Organization: Default test organization

## Writing New Tests

### Basic Test Template
```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
@pytest.mark.auth  # Choose appropriate marker
class TestMyFeature:
    """Test description."""

    async def test_something(
        self,
        async_session: AsyncSession,
        test_user,
        user_service,
    ):
        """Test specific behavior."""
        # Arrange
        expected = "value"
        
        # Act
        result = await user_service.some_method(async_session, test_user)
        
        # Assert
        assert result == expected
```

### Async Tests
All tests are async using `@pytest.mark.asyncio`:

```python
@pytest.mark.asyncio
async def test_async_operation(async_session):
    """Test async code."""
    result = await async_session.execute(select(User))
    assert result is not None
```

### Database Tests
Use fixtures for database isolation:

```python
@pytest.mark.asyncio
@pytest.mark.db
async def test_database_operation(async_session, test_user):
    """Test with real database session."""
    # Changes are automatically rolled back after test
    pass
```

## Common Patterns

### Testing Exceptions
```python
with pytest.raises(ValueError):
    await some_function_that_raises()
```

### Testing Async Functions
```python
@pytest.mark.asyncio
async def test_async(async_session):
    result = await service.async_method(async_session)
    assert result is not None
```

### Testing with Fixtures
```python
async def test_with_multiple_fixtures(
    async_session,
    test_user,
    test_organization,
    user_service,
):
    # All fixtures are injected and ready to use
    pass
```

## Coverage Goals

| Component | Target |
|-----------|--------|
| Services | 90%+ |
| Models | 80%+ |
| Schemas | 85%+ |
| API | 75%+ |

**Current Coverage**: Run `pytest --cov=backend` to see current stats

## Continuous Integration

Tests are run automatically on:
- Pull requests
- Commits to main branch
- Scheduled nightly builds

**CI Status**: Check GitHub Actions for latest results

## Troubleshooting

### AsyncIO Issues
```bash
# Ensure pytest-asyncio is installed
pip install pytest-asyncio

# Run with specific event loop
pytest --asyncio-mode=auto
```

### Database Connection
```bash
# If using external DB, ensure it's running
psql -U postgres -h localhost
```

### Fixture Not Found
```bash
# Ensure conftest.py is in parent directory
# Restart pytest to reload fixtures
pytest --cache-clear
```

### Import Errors
```bash
# Add backend to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/backend"
pytest
```

## Performance Tips

- 🚀 Use `pytest -n auto` for parallel execution (requires pytest-xdist)
- 📦 Use fixtures to avoid duplicate setup
- 🔄 Mark slow tests to skip with `-m "not slow"`
- 💾 Use in-memory SQLite for tests (default)

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/20/orm/session_basics.html#testing-orm-applications)

---

**Last Updated**: 2026-11-23  
**Maintained By**: Development Team  
**Coverage**: 85%+
