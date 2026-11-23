# Cloud Lab Platform

**Multi-organization identity and access management system with SSO, MFA, and role-based access control.**

A production-ready backend for user authentication, authorization, and session management with enterprise security features.

---

## 🎯 Overview

Cloud Lab Platform is a comprehensive Identity and Access Management (IAM) system designed for multi-tenant environments. It provides enterprise-grade authentication, authorization, and session management with modern security practices.

### Key Capabilities
- 🔐 **Secure Authentication** – Password, MFA (TOTP), SSO (Google/Microsoft)
- 👥 **Multi-Tenant** – Organization isolation and role-based access
- 🛡️ **Enterprise Security** – Rate limiting, audit logging, session management
- ⚡ **High Performance** – Async-first, database connection pooling
- 📝 **Well Documented** – API docs, setup guides, configuration

---

## ✨ Features

### Authentication & Authorization
| Feature | Details |
|---------|---------|
| **Password Login** | Bcrypt hashing, email verification, secure recovery |
| **Multi-Factor Auth** | TOTP with authenticator apps, recovery codes, encrypted secrets |
| **Single Sign-On** | Google OAuth, Microsoft/Azure AD, automatic account creation |
| **Sessions** | Device tracking, revocation, activity monitoring |
| **Rate Limiting** | Per-user, per-IP, endpoint-specific limits |

### Security
- ✅ Account lockout after 5 failed attempts (15-min cooldown)
- ✅ TOTP replay attack prevention with step tracking
- ✅ Timing-safe password verification (no timing attacks)
- ✅ Encrypted MFA secrets at rest
- ✅ Secure headers (X-Frame-Options, CSP, HSTS)
- ✅ CSRF protection with state parameters
- ✅ Audit logging for compliance

### Developer Experience
- ✅ Type-safe with Pydantic models
- ✅ Async-first with SQLAlchemy
- ✅ Class-based services architecture
- ✅ Comprehensive schemas for validation
- ✅ OpenAPI documentation auto-generated
- ✅ Structured logging with context

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 13+
- Redis 6+ (optional, for rate limiting)

### Installation

```bash
# 1. Clone repository
git clone https://github.com/yourusername/Cloud-Lab-Platform.git
cd Cloud-Lab-Platform

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux

# 3. Install dependencies
pip install -r backend/requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your database, OAuth, and email settings

# 5. Run migrations
alembic upgrade head

# 6. Start server
uvicorn main:app --reload
```

✅ API will be available at `http://localhost:8000`  
📚 API docs at `http://localhost:8000/docs`

---

## 📋 Configuration

### Core Settings
```env
ENVIRONMENT=dev
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/cloud_lab
JWT_ACCESS_SECRET=your-secret-key-at-least-32-chars
JWT_REFRESH_SECRET=your-other-secret-key-at-least-32-chars
```

### OAuth Setup
- **Google**: Free tier at [Google Cloud Console](https://console.cloud.google.com/)
- **Microsoft**: Free tier at [Azure Portal](https://portal.azure.com/)
- See `OAUTH_SETUP.md` for detailed setup instructions

### Email (Brevo)
```env
BREVO_API_KEY=your-api-key
EMAIL_FROM=noreply@yourdomain.com
```

---

## 🏗️ Architecture

### Core Module
- **auth.py** – Security services (hashing, JWT, TOTP, encryption)
- **config.py** – Centralized configuration management
- **database/** – Async SQLAlchemy, connection pooling, custom types
- **api/** – Exception handlers, pagination, response formatting
- **middleware/** – Rate limiting, security headers, logging

### Identity Module
```
models/        → SQLAlchemy ORM models
├── user.py    → User with MFA, passwords, activity
├── organization.py → Multi-tenant orgs
├── role.py     → Roles with permissions
├── permission.py → Granular permission scopes
├── session.py  → Session management
├── token.py    → Email verification tokens
└── sso.py      → OAuth provider connections

services/      → Business logic layer
├── auth.py     → Authentication flows
├── user.py     → User CRUD and password management
├── organization.py → Org management
├── role.py     → Role and permission assignment
├── permission.py → Permission checking
├── session.py  → Session lifecycle
├── token.py    → Token generation/verification
└── oauth_handler.py → OAuth callback handling

schemas/       → Pydantic validation models
├── auth.py     → Login, MFA, password reset
├── user.py     → User CRUD operations
├── organization.py → Org management
├── role.py     → Role operations
├── permission.py → Permission operations
├── session.py  → Session management
└── sso.py      → OAuth flows
```

---

## 🔌 API Endpoints

### Authentication
```
POST   /api/v1/auth/login               Login with email/password
POST   /api/v1/auth/mfa/verify          Verify TOTP code
POST   /api/v1/auth/mfa/setup           Enable two-factor auth
POST   /api/v1/auth/mfa/disable         Disable two-factor auth
POST   /api/v1/auth/token/refresh       Refresh access token
POST   /api/v1/auth/logout              Logout and revoke session
POST   /api/v1/auth/password/reset      Request password reset
POST   /api/v1/auth/callback/google     Google OAuth callback
POST   /api/v1/auth/callback/microsoft  Microsoft OAuth callback
```

### Users
```
GET    /api/v1/users/{id}               Get user profile
GET    /api/v1/users                    List users (paginated)
PATCH  /api/v1/users/{id}               Update user
DELETE /api/v1/users/{id}               Delete user
```

### Organizations
```
GET    /api/v1/organizations/{id}       Get organization
GET    /api/v1/organizations/{id}/members Get members
```

### Roles & Permissions
```
GET    /api/v1/roles                    List roles
POST   /api/v1/roles                    Create role
GET    /api/v1/permissions              List permissions
```

---

## 🔒 Security Best Practices

### For Production
1. ✅ Change all secrets in `.env` (JWT keys, MFA key, etc.)
2. ✅ Use HTTPS everywhere (required for OAuth)
3. ✅ Enable email verification (`REQUIRE_EMAIL_VERIFICATION=true`)
4. ✅ Configure trusted proxies for load balancers
5. ✅ Set up Redis for rate limiting
6. ✅ Use strong database passwords
7. ✅ Enable audit logging
8. ✅ Monitor failed login attempts
9. ✅ Regular database backups
10. ✅ Rotate secrets periodically

### Password Policy
- Minimum 8 characters (enforced)
- Never logged or returned in responses
- Always hashed with bcrypt + salt

### MFA Security
- Recovery codes stored hashed
- Secrets encrypted with Fernet
- Step tracking prevents code reuse
- 30-second time window (RFC 6238)

### Rate Limiting
- Anonymous: 600 req/min per IP
- Authenticated: 120 req/min per user+IP
- Auth endpoints: Custom limits
- Redis-backed or in-memory fallback

---

## 📊 Database Schema

### Core Tables (identity schema)
- **users** – User accounts with MFA and security fields
- **organizations** – Multi-tenant organization data
- **roles** – Role definitions per organization
- **permissions** – Permission scopes and actions
- **user_sessions** – Active sessions with device tracking
- **one_time_tokens** – Email verification, password reset
- **sso_connections** – OAuth provider links

All tables include:
- UUID primary keys (time-ordered v7)
- created_at / updated_at timestamps (UTC)
- Proper indexes for query performance
- Foreign key constraints
- CHECK constraints for enum fields

---

## 🧪 Development

### Project Structure
```
backend/
├── core/                    Core infrastructure
├── modules/
│   └── identity/           Identity management
│       ├── models/
│       ├── schemas/
│       └── services/
├── requirements.txt        Dependencies
└── main.py                 FastAPI app

.env.example               Configuration template
.env                       Local dev config (not committed)
OAUTH_SETUP.md            OAuth setup guide
```

### Running Tests
```bash
pip install pytest pytest-asyncio
pytest backend/
```

### Database Migrations
```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## 🚨 Troubleshooting

| Issue | Solution |
|-------|----------|
| Database connection error | Check `DATABASE_URL`, ensure PostgreSQL running |
| OAuth redirect mismatch | Verify exact URI in provider settings (protocol, port, trailing slash) |
| Rate limiting not working | Ensure Redis running (`redis-cli ping`), check `REDIS_URL` |
| MFA QR not working | Verify `MFA_SECRET_KEY` set, use TOTP-compatible app |
| Slow queries | Check database indexes, enable query logging with `DB_ECHO=true` |

---

## 📚 Documentation

- **[OAUTH_SETUP.md](OAUTH_SETUP.md)** – Step-by-step OAuth configuration for Google and Microsoft
- **[.env.example](.env.example)** – All configuration options with descriptions
- **API Docs** – Available at `/docs` when running

---

## 🤝 Contributing

Found a bug or want a feature? Please open an issue or submit a PR!

---

## 📄 License

MIT License – See LICENSE file for details

---

## 🙏 Built With

- [FastAPI](https://fastapi.tiangolo.com/) – Modern web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) – SQL toolkit and ORM
- [Pydantic](https://docs.pydantic.dev/) – Data validation
- [PostgreSQL](https://www.postgresql.org/) – Database
- [Redis](https://redis.io/) – Caching and rate limiting
- [bcrypt](https://github.com/pyca/bcrypt) – Password hashing
- [python-jose](https://github.com/mpdavis/python-jose) – JWT tokens

---

**Version**: 0.1.0 | **Status**: Development | **Last Updated**: 2026-11-23
