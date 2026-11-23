"""Credentials and tokens: password hashing, emailed tokens, signed JWTs, authenticator codes
and the encryption of authenticator secrets. Every module uses the one ``service`` below."""

import asyncio
import base64
import hashlib
import hmac
import secrets
import struct
import time
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

import bcrypt
import jwt
from cryptography.fernet import Fernet
from cryptography.fernet import InvalidToken as UnreadableSecret

from app.core.api.exceptions import InvalidToken
from app.core.config import Settings


class PasswordService:
    """Hash and verify passwords without blocking the event loop."""

    def __init__(self) -> None:
        self._dummy_hash = bcrypt.hashpw(secrets.token_bytes(16), bcrypt.gensalt()).decode()

    async def hash(self, password: str) -> str:
        hashed = await asyncio.to_thread(bcrypt.hashpw, password.encode(), bcrypt.gensalt())
        return hashed.decode()

    def generate(self) -> str:
        """A random temporary password (12 URL-safe characters)."""
        return secrets.token_urlsafe(9)

    async def verify(self, password: str, hashed: str | None) -> bool:
        """Check a password, including a dummy hash for unknown accounts."""
        result = await asyncio.to_thread(
            bcrypt.checkpw, password.encode(), (hashed or self._dummy_hash).encode()
        )
        return result and hashed is not None


class EmailTokenService:
    """Generate and hash one-time URL-safe tokens."""

    def new(self) -> str:
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()

    def hash(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()


class JwtService:
    """Sign access and refresh tokens, and verify any token's signature and expiry."""

    def _sign(self, claims: dict, ttl: timedelta, secret: str, algorithm: str) -> str:
        now = datetime.now(UTC)
        claims = {"jti": str(uuid.uuid4()), **claims, "iat": now, "exp": now + ttl}
        return jwt.encode(claims, secret, algorithm=algorithm)

    def access(
        self,
        settings: Settings,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
        scopes: list[str],
        session_id: uuid.UUID,
    ) -> str:
        claims = {
            "sub": str(user_id),
            "org": str(organization_id),
            "scopes": scopes,
            "sid": str(session_id),
        }
        return self._sign(
            claims,
            timedelta(minutes=settings.access_token_expire_minutes),
            settings.jwt_access_secret,
            settings.algorithm,
        )

    @staticmethod
    def decode(token: str, secret: str, algorithm: str = "HS256") -> dict:
        """Verify a JWT's signature and expiry and return its claims.
        Only the identity module signs tokens; everyone else just verifies."""
        try:
            return jwt.decode(
                token, secret, algorithms=[algorithm], options={"require": ["exp", "sub"]}
            )
        except jwt.PyJWTError as exc:
            raise InvalidToken() from exc

    def refresh(
        self, settings: Settings, user_id: uuid.UUID, session_id: uuid.UUID, jti: str
    ) -> str:
        claims = {"sub": str(user_id), "sid": str(session_id), "jti": jti}
        return self._sign(
            claims,
            timedelta(days=settings.refresh_token_expire_days),
            settings.jwt_refresh_secret,
            settings.algorithm,
        )


class TotpService:
    """Authenticator-app codes (RFC 6238, 6 digits) and one-time recovery codes.
    The code period and the number of recovery codes come from the settings."""

    @staticmethod
    def new_secret() -> str:
        return base64.b32encode(secrets.token_bytes(20)).decode()

    @staticmethod
    def code(secret: str, step: int) -> str:
        digest = hmac.digest(base64.b32decode(secret), struct.pack(">Q", step), "sha1")
        offset = digest[-1] & 0x0F
        number = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
        return f"{number % 1_000_000:06d}"

    @staticmethod
    def step(settings: Settings) -> int:
        """The current time step: codes change once per ``mfa_period_seconds``."""
        return int(time.time()) // settings.mfa_period_seconds

    def check(
        self, settings: Settings, secret: str, code: str, last_step: int | None
    ) -> int | None:
        """The time step the code belongs to (this one and its neighbours count), or None.
        A step at or before ``last_step`` is refused, so a code works once."""
        now = self.step(settings)
        for step in (now - 1, now, now + 1):
            if (last_step is None or step > last_step) and hmac.compare_digest(
                self.code(secret, step), code
            ):
                return step
        return None

    @staticmethod
    def uri(settings: Settings, secret: str, email: str) -> str:
        """The otpauth link an authenticator app reads from a QR code."""
        issuer = settings.app_name
        label = quote(f"{issuer}:{email}")
        return (
            f"otpauth://totp/{label}?secret={secret}&issuer={quote(issuer)}"
            f"&period={settings.mfa_period_seconds}"
        )

    @staticmethod
    def new_recovery_codes(settings: Settings) -> list[str]:
        return [secrets.token_hex(5) for _ in range(settings.mfa_recovery_code_count)]

    @staticmethod
    def hash_recovery(code: str) -> str:
        return hashlib.sha256(code.strip().lower().encode()).hexdigest()


class SecretBox:
    """Encrypts authenticator secrets so a copy of the database alone does not reveal them."""

    @staticmethod
    def _fernet(settings: Settings) -> Fernet:
        material = settings.mfa_secret_key or f"mfa:{settings.jwt_refresh_secret}"
        return Fernet(base64.urlsafe_b64encode(hashlib.sha256(material.encode()).digest()))

    def seal(self, settings: Settings, plain: str) -> str:
        return self._fernet(settings).encrypt(plain.encode()).decode()

    def open(self, settings: Settings, sealed: str) -> str | None:
        try:
            return self._fernet(settings).decrypt(sealed.encode()).decode()
        except UnreadableSecret:
            return None


class SecurityService:
    """Identity security operations grouped by credential and token type."""

    def __init__(self) -> None:
        self.passwords = PasswordService()
        self.email_tokens = EmailTokenService()
        self.jwt = JwtService()
        self.totp = TotpService()
        self.box = SecretBox()


service = SecurityService()
