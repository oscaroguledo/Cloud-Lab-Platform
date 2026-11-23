"""Signed-in sessions with rotating refresh tokens and reuse detection."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core import auth
from core.api.dependencies import RequestContext
from core.config import Settings
from core.database.engine import uuid7
from modules.identity import errors
from modules.identity.audit import Action, audit
from modules.identity.models import User, UserSession
from modules.identity.schemas import SessionOut, TokenPair
from modules.identity.services.common import ensure_can_sign_in, load_user, user_scopes


class SessionService:
    """Manage signed-in sessions for one database session."""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _make_tokens(settings: Settings, user: User, session_id: uuid.UUID, jti: str) -> TokenPair:
        # Until the temporary password is changed the token grants nothing, so other services
        # (which read scopes from the token) deny everything too.
        scopes = [] if user.must_change_password else sorted(user_scopes(user))
        return TokenPair(
            access_token=auth.service.jwt.access(
                settings, user.id, user.organization_id, scopes, session_id
            ),
            refresh_token=auth.service.jwt.refresh(settings, user.id, session_id, jti),
            expires_in=settings.access_token_expire_minutes * 60,
        )

    async def start(self, settings: Settings, user: User, ctx: RequestContext) -> TokenPair:
        """Open a session for a signed-in user (the caller commits; ``user`` needs its role)."""
        now = datetime.now(UTC)
        await self.db.execute(  # keep the table lean: forget this user's expired sessions
            delete(UserSession).where(UserSession.user_id == user.id, UserSession.expires_at < now)
        )
        session_id, jti = uuid7(), str(uuid.uuid4())
        self.db.add(
            UserSession(
                id=session_id,
                user_id=user.id,
                current_jti=jti,
                user_agent=ctx.user_agent,
                ip=ctx.ip,
                expires_at=now + timedelta(days=settings.refresh_token_expire_days),
            )
        )
        return self._make_tokens(settings, user, session_id, jti)

    async def rotate(
        self, settings: Settings, ctx: RequestContext, refresh_token: str
    ) -> TokenPair:
        """Exchange a refresh token for a new pair; the presented token stops working.
        A conditional UPDATE lets one concurrent request win; replay deletes the session."""
        claims = auth.service.jwt.decode(
            refresh_token, settings.jwt_refresh_secret, settings.algorithm
        )
        try:
            user_id, session_id = uuid.UUID(claims["sub"]), uuid.UUID(claims["sid"])
        except (KeyError, ValueError) as exc:
            raise errors.InvalidToken() from exc

        user = await load_user(self.db, user_id)
        try:
            ensure_can_sign_in(user)
        except errors.APIException as exc:
            await self._refresh_failed(user, session_id, exc.error_code)
            raise

        now = datetime.now(UTC)
        new_jti = str(uuid.uuid4())
        result = await self.db.execute(
            update(UserSession)
            .where(
                UserSession.id == session_id,
                UserSession.user_id == user_id,
                UserSession.current_jti == claims["jti"],
                UserSession.expires_at > now,
            )
            .values(current_jti=new_jti, last_used_at=now, ip=ctx.ip, user_agent=ctx.user_agent)
            .returning(UserSession.id)
        )
        if result.first() is None:
            session = await self.db.get(UserSession, session_id)
            if session is not None and session.expires_at > now:  # an old token: replay
                await audit(
                    self.db, Action.TOKEN_REUSE, failure=True, actor=user,
                    target=("session", session_id),
                )  # fmt: skip
            else:
                reason = "session_expired" if session is not None else "session_ended"
                await self._refresh_failed(user, session_id, reason)
            if session is not None:
                await self.end([user_id], only_session=session_id)
            await self.db.commit()
            raise errors.InvalidToken()
        await self.db.commit()
        return self._make_tokens(settings, user, session_id, new_jti)

    async def _refresh_failed(self, user: User, session_id: uuid.UUID, reason: str) -> None:
        """Log a refresh refused for a validly signed token, and commit before the error."""
        await audit(
            self.db, Action.REFRESH_FAILED, failure=True, actor=user,
            target=("session", session_id), reason=reason,
        )  # fmt: skip
        await self.db.commit()

    async def end(
        self,
        user_ids: list[uuid.UUID],
        *,
        except_session: uuid.UUID | None = None,
        only_session: uuid.UUID | None = None,
    ) -> int:
        """Delete sessions of the given users (the caller commits). Returns how many."""
        conditions = [UserSession.user_id.in_(user_ids)]
        if except_session:
            conditions.append(UserSession.id != except_session)
        if only_session:
            conditions.append(UserSession.id == only_session)
        result = await self.db.execute(delete(UserSession).where(*conditions))
        return result.rowcount or 0

    async def list(self, user_id: uuid.UUID, current: uuid.UUID | None) -> list[SessionOut]:
        rows = (
            await self.db.scalars(
                select(UserSession)
                .where(UserSession.user_id == user_id, UserSession.expires_at > datetime.now(UTC))
                .order_by(UserSession.last_used_at.desc())
            )
        ).all()
        return [
            SessionOut(
                id=s.id,
                current=s.id == current,
                ip=s.ip,
                user_agent=s.user_agent,
                created_at=s.created_at,
                last_used_at=s.last_used_at,
                expires_at=s.expires_at,
            )  # fmt: skip
            for s in rows
        ]

    async def is_active(self, session_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        session = await self.db.get(UserSession, session_id)
        return bool(
            session and session.user_id == user_id and session.expires_at > datetime.now(UTC)
        )

    async def revoke_one(self, user: User, session_id: uuid.UUID) -> None:
        """Sign out one of the user's devices."""
        if not await self.end([user.id], only_session=session_id):
            raise errors.SessionNotFound()
        await audit(
            self.db, Action.SESSION_REVOKED, actor=user, target=("session", session_id),
            by="self",
        )  # fmt: skip
        await self.db.commit()

    async def revoke_all(self, user: User, keep: uuid.UUID | None) -> int:
        """Sign out every device (except ``keep``, normally the current one)."""
        count = await self.end([user.id], except_session=keep)
        if count:
            await audit(
                self.db, Action.SESSION_REVOKED, actor=user, target=("user", user.id),
                by="self", count=count,
            )  # fmt: skip
        await self.db.commit()
        return count
