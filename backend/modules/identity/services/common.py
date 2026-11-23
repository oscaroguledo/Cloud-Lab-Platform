"""Helpers shared by the identity services."""

import hashlib
import uuid
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.api.dependencies import RequestContext
from app.core.config import Settings
from app.modules.identity import errors
from app.modules.identity.models import AccountStatus, Organization, Role, RolePermission, User
from app.modules.identity.notifier import NEW_SIGN_IN, ORGANIZATION_CLOSED, Notify
from app.modules.identity.scopes import Scopes


def role_scopes_loader():
    """Loader option: a role together with its permission links (so ``role.scopes`` works)."""
    return selectinload(Role.permission_links)


def user_loader() -> tuple:
    """Loader options: a user with their role and its scopes, and their organization."""
    return (
        selectinload(User.role).selectinload(Role.permission_links),
        selectinload(User.organization),
    )


async def load_user(db: AsyncSession, user_id: uuid.UUID) -> User:
    """A user with their role, its scopes and their organization loaded."""
    user = await db.scalar(
        select(User)
        .where(User.id == user_id)
        .options(*user_loader())
        .execution_options(populate_existing=True)
    )
    if user is None:
        raise errors.InvalidToken()
    return await attach_scopes(db, user)


def normalize_email(email: str) -> str:
    return email.strip().lower()


async def find_account(db: AsyncSession, email: str) -> User | None:
    """The user with this email address (case-insensitive), if any."""
    return await db.scalar(select(User).where(func.lower(User.email) == normalize_email(email)))


async def count_role_users(db: AsyncSession, role_id: uuid.UUID) -> int:
    stmt = select(func.count()).select_from(User).where(User.role_id == role_id)
    return await db.scalar(stmt) or 0


async def lock_organization(db: AsyncSession, organization_id: uuid.UUID) -> Organization:
    """Row-lock the organization (FOR NO KEY UPDATE) so changes cannot both remove the last admin.
    This mode does not block foreign-key FOR KEY SHARE locks, which used to deadlock."""
    organization = await db.scalar(
        select(Organization)
        .where(Organization.id == organization_id)
        .with_for_update(key_share=True)
        .execution_options(populate_existing=True)
    )
    if organization is None:
        raise errors.OrganizationNotFound()
    return organization


async def check_has_owner(db: AsyncSession, organization_id: uuid.UUID) -> None:
    """Raise LastOwner unless an active user still holds the owner role (call after the change)."""
    await db.flush()
    owners = await db.scalar(
        select(func.count(distinct(User.id)))
        .select_from(User)
        .join(Role, Role.id == User.role_id)
        .where(
            User.organization_id == organization_id,
            User.account_status == AccountStatus.ACTIVE,
            Role.is_owner.is_(True),
        )
    )
    if not owners:
        raise errors.LastOwner()


def role_grants(role: Role) -> frozenset[str]:
    """What a role grants. The owner role always grants every organisation scope, plus any custom
    permission a super admin added to the catalogue (those are linked to it when created)."""
    granted = frozenset(role.scopes)
    if role.is_owner:
        return (granted | frozenset(Scopes.ORGANIZATION_ALL)) - frozenset(Scopes.PLATFORM_ONLY)
    return granted


async def effective_scopes(
    db: AsyncSession, organization_id: uuid.UUID
) -> dict[uuid.UUID, frozenset[str]]:
    """What each role of an organisation can really do: its own scopes plus those of every role
    on a lower level, so a higher role can do all that the roles beneath it can."""
    rows = await db.execute(
        select(Role.id, Role.level, Role.is_owner, RolePermission.scope)
        .outerjoin(RolePermission, RolePermission.role_id == Role.id)
        .where(Role.organization_id == organization_id)
    )
    own: dict[uuid.UUID, set[str]] = {}
    ranks: dict[int, list[uuid.UUID]] = {}
    owners = set()
    for role_id, level, is_owner_role, scope in rows:
        if role_id not in own:
            own[role_id] = set()
            ranks.setdefault(level, []).append(role_id)
        if scope:
            own[role_id].add(scope)
        if is_owner_role:
            owners.add(role_id)
    platform_only, result, below = frozenset(Scopes.PLATFORM_ONLY), {}, set()
    for level in sorted(ranks):
        for role_id in ranks[level]:
            if role_id in owners:  # the owner role always holds every organisation scope
                full = own[role_id] | below | set(Scopes.ORGANIZATION_ALL)
                result[role_id] = frozenset(full) - platform_only
            else:
                result[role_id] = frozenset(own[role_id] | (below - platform_only))
        for role_id in ranks[level]:  # only roles on a *lower* level are inherited
            below |= own[role_id]
    return result


async def attach_scopes(db: AsyncSession, user: User) -> User:
    """Give a loaded user their effective scopes, which ``user_scopes`` then returns."""
    user.effective_scopes = (await effective_scopes(db, user.organization_id))[user.role_id]
    return user


def user_scopes(user: User) -> frozenset[str]:
    """What a user can do: their role's scopes and those of every lower role (see attach_scopes)."""
    return getattr(user, "effective_scopes", None) or role_grants(user.role)


def is_owner(user: User) -> bool:
    """True when the user holds the owner role (an organisation can have several owners)."""
    return user.role.is_owner


def ensure_can_grant(actor: User, scopes: Iterable[str]) -> None:
    """Nobody may hand out privileges they do not hold themselves (the owner holds them all)."""
    if is_owner(actor):
        return
    if not set(scopes) <= user_scopes(actor):
        raise errors.PrivilegeEscalation()


def ensure_can_edit_role(actor: User, role: Role) -> None:
    """A role can only be changed or deleted by someone whose level is at least the role's."""
    if not is_owner(actor) and role.level > actor.role.level:
        raise errors.PrivilegeEscalation("You cannot change a role above your own level")


def ensure_can_use_level(actor: User, level: int) -> None:
    """Nobody may put a role or a user at a level above their own."""
    if not is_owner(actor) and level > actor.role.level:
        raise errors.PrivilegeEscalation("You cannot go above your own level")


def ensure_can_manage(actor: User, target: User) -> None:
    """Users can be managed by someone at or above their level; only owners manage owners."""
    if is_owner(actor):
        return
    if is_owner(target):
        raise errors.OwnerProtected()
    if target.role.level > actor.role.level:
        raise errors.PrivilegeEscalation("You cannot manage a member whose level is above yours")


def ensure_can_sign_in(user: User) -> None:
    """Raise unless the account is active and its organisation is open."""
    if user.organization.is_closed:
        raise errors.OrganizationClosed()
    if user.is_suspended:
        raise errors.AccountDisabled()
    if user.is_inactive:
        raise errors.AccountInactive()


def temporary_expiry(settings: Settings) -> datetime:
    """When an administrator-set password stops working."""
    return datetime.now(UTC) + timedelta(days=settings.temporary_password_ttl_days)


def apply_profile(user: User, data) -> list[str]:
    """Copy the fields present in ``data`` (an UpdateProfileIn or UpdateUserIn) onto the user.
    Returns the names of the fields that actually changed."""
    changed = []
    for field, value in data.model_dump(exclude_none=True).items():
        if getattr(user, field) != value:
            setattr(user, field, value)
            changed.append(field)
    return sorted(changed)


async def alert(notify: Notify, kind: str, user: User, **params: object) -> None:
    """Email a user about a change to their account's security, in their own language."""
    await notify.send(
        kind, to=user.email, language=user.language, first_name=user.first_name, **params
    )


async def flag_new_device(
    settings: Settings, notify: Notify, user: User, ctx: RequestContext
) -> None:
    """Remember the browser a user just signed in with, and email them if it is new.
    The first sign-in only seeds the list, so nobody is alerted about their own first device."""
    mark = hashlib.sha256((ctx.user_agent or "").encode()).hexdigest()[:16]
    known = list(user.known_devices or [])
    if mark in known:
        return
    user.known_devices = [*known, mark][-settings.known_devices_limit :]
    if known:
        when = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
        device, ip = ctx.user_agent or "-", ctx.ip or "-"
        await alert(notify, NEW_SIGN_IN, user, device=device, ip=ip, time=when)


async def tell_members_closed(db: AsyncSession, notify: Notify, organization: Organization) -> None:
    """Email every member that their organisation was closed (the owner who closed it too)."""
    members = await db.execute(
        select(User.email, User.first_name, User.language).where(
            User.organization_id == organization.id
        )
    )
    for email, first_name, language in members:
        await notify.send(
            ORGANIZATION_CLOSED, to=email, language=language, first_name=first_name,
            organization_name=organization.name,
        )  # fmt: skip
