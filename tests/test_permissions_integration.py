"""Integration tests proving litestar-permissions works end-to-end with an async Litestar app.

Tests cover:
- Permission-guarded routes (200 for authorized, 403 for unauthorized)
- Role-guarded routes (200 for correct role, 403 for wrong role)
- Superuser bypass of all permission/role checks
- Unauthenticated requests get 401
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

import pytest
from litestar import Litestar, get
from litestar.middleware.base import AbstractMiddleware
from litestar.testing import AsyncTestClient
from litestar.types import Receive, Scope, Send
from sqlalchemy import String, Uuid
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.pool import StaticPool

from litestar_permissions import PermissionsConfig, require_permission, require_role
from litestar_permissions.models import create_models
from litestar_permissions.resolver import PermissionResolver


# ---------------------------------------------------------------------------
# ORM Base + RBAC models (created once at module level)
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


rbac = create_models(Base)
Role = rbac["Role"]
Permission = rbac["Permission"]
RolePermission = rbac["RolePermission"]
UserRoleAssignment = rbac["UserRoleAssignment"]


class User(Base):
    """Minimal user model satisfying UserProtocol."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(Uuid(), primary_key=True, default=uuid4)
    username: Mapped[str] = mapped_column(String(100), unique=True)
    is_superuser: Mapped[bool] = mapped_column(default=False)


# ---------------------------------------------------------------------------
# Lightweight user object for scope injection (avoids detached ORM instances)
# ---------------------------------------------------------------------------
@dataclass
class ScopeUser:
    id: UUID | str
    is_superuser: bool = False


# ---------------------------------------------------------------------------
# In-memory user store populated during test seeding
# ---------------------------------------------------------------------------
USER_STORE: dict[str, ScopeUser] = {}


# ---------------------------------------------------------------------------
# Auth middleware: reads X-User-Id header -> injects user into scope
# ---------------------------------------------------------------------------
class FakeAuthMiddleware(AbstractMiddleware):
    """Injects user and db_session into scope BEFORE guards run.

    Guards execute before handler dependencies, so scope injection
    must happen in middleware, not in a Provide() dependency.
    """

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            # Inject user from header
            headers = dict(scope.get("headers", []))
            user_id_raw = headers.get(b"x-user-id")
            if user_id_raw is not None:
                user = USER_STORE.get(user_id_raw.decode())
                if user is not None:
                    scope["user"] = user

            # Inject per-request db session for guards
            if _SESSION_FACTORY is not None:
                async with _SESSION_FACTORY() as session:
                    scope["db_session"] = session
                    await self.app(scope, receive, send)
                    return

        await self.app(scope, receive, send)


# ---------------------------------------------------------------------------
# Module-level engine / session factory (set per-test by the fixture)
# ---------------------------------------------------------------------------
_SESSION_FACTORY: async_sessionmaker[AsyncSession] | None = None


# ---------------------------------------------------------------------------
# Guarded route handlers
# ---------------------------------------------------------------------------
@get("/posts", guards=[require_permission("posts:read")])
async def list_posts() -> dict[str, Any]:
    return {"posts": [{"id": 1, "title": "Hello World"}]}


@get("/posts/create", guards=[require_permission("posts:write")])
async def create_post() -> dict[str, Any]:
    return {"created": True}


@get("/admin/dashboard", guards=[require_role("admin")])
async def admin_dashboard() -> dict[str, Any]:
    return {"dashboard": "admin"}


@get("/public")
async def public_route() -> dict[str, Any]:
    return {"public": True}


# ---------------------------------------------------------------------------
# Shared config and models (no plugin -- we wire state manually to avoid
# calling create_models twice on the same Base/metadata).
# ---------------------------------------------------------------------------
PERMISSIONS_CONFIG = PermissionsConfig(
    user_key="user",
    superuser_bypass=True,
    cache_ttl=0,
)
RESOLVER = PermissionResolver(config=PERMISSIONS_CONFIG, models=rbac)


def create_test_app() -> Litestar:
    return Litestar(
        route_handlers=[list_posts, create_post, admin_dashboard, public_route],
        middleware=[FakeAuthMiddleware],
        state={
            "permissions_config": PERMISSIONS_CONFIG,
            "permissions_models": rbac,
            "permissions_resolver": RESOLVER,
        },
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
async def _setup_database():
    """Create the async engine, tables, and session factory for each test."""
    global _SESSION_FACTORY

    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    _SESSION_FACTORY = async_sessionmaker(engine, expire_on_commit=False)
    USER_STORE.clear()
    RESOLVER.invalidate_all()

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def seed_data() -> dict[str, str]:
    """Seed the database with users, roles, permissions, and assignments."""
    assert _SESSION_FACTORY is not None
    async with _SESSION_FACTORY() as session:
        # Users
        regular_user = User(username="alice", is_superuser=False)
        admin_user = User(username="bob", is_superuser=False)
        superuser = User(username="superadmin", is_superuser=True)
        no_perms_user = User(username="charlie", is_superuser=False)
        session.add_all([regular_user, admin_user, superuser, no_perms_user])
        await session.flush()

        # Populate in-memory auth store
        USER_STORE[str(regular_user.id)] = ScopeUser(id=regular_user.id, is_superuser=False)
        USER_STORE[str(admin_user.id)] = ScopeUser(id=admin_user.id, is_superuser=False)
        USER_STORE[str(superuser.id)] = ScopeUser(id=superuser.id, is_superuser=True)
        USER_STORE[str(no_perms_user.id)] = ScopeUser(id=no_perms_user.id, is_superuser=False)

        # Permissions
        perm_read = Permission(codename="posts:read", description="Read posts")
        perm_write = Permission(codename="posts:write", description="Write posts")
        session.add_all([perm_read, perm_write])
        await session.flush()

        # Roles
        reader_role = Role(name="reader", description="Can read posts")
        writer_role = Role(name="writer", description="Can write posts")
        admin_role = Role(name="admin", description="Admin role")
        session.add_all([reader_role, writer_role, admin_role])
        await session.flush()

        # Role -> Permission links
        session.add_all([
            RolePermission(role_id=reader_role.id, permission_id=perm_read.id),
            RolePermission(role_id=writer_role.id, permission_id=perm_write.id),
            RolePermission(role_id=admin_role.id, permission_id=perm_read.id),
            RolePermission(role_id=admin_role.id, permission_id=perm_write.id),
        ])

        # User -> Role assignments
        session.add(UserRoleAssignment(user_id=regular_user.id, role_id=reader_role.id))
        session.add(UserRoleAssignment(user_id=admin_user.id, role_id=admin_role.id))

        await session.commit()

        return {
            "regular_user_id": str(regular_user.id),
            "admin_user_id": str(admin_user.id),
            "superuser_id": str(superuser.id),
            "no_perms_user_id": str(no_perms_user.id),
        }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestPermissionGuard:
    """Tests for require_permission guard."""

    async def test_user_with_permission_can_access(self, seed_data: dict[str, str]) -> None:
        """Alice has posts:read via the reader role -- should get 200."""
        app = create_test_app()
        async with AsyncTestClient(app) as client:
            resp = await client.get("/posts", headers={"X-User-Id": seed_data["regular_user_id"]})
            assert resp.status_code == 200
            assert resp.json()["posts"][0]["title"] == "Hello World"

    async def test_user_without_permission_gets_403(self, seed_data: dict[str, str]) -> None:
        """Alice does NOT have posts:write -- should get 403."""
        app = create_test_app()
        async with AsyncTestClient(app) as client:
            resp = await client.get("/posts/create", headers={"X-User-Id": seed_data["regular_user_id"]})
            assert resp.status_code == 403

    async def test_user_with_no_roles_gets_403(self, seed_data: dict[str, str]) -> None:
        """Charlie has no roles at all -- should get 403 on any guarded route."""
        app = create_test_app()
        async with AsyncTestClient(app) as client:
            resp = await client.get("/posts", headers={"X-User-Id": seed_data["no_perms_user_id"]})
            assert resp.status_code == 403

    async def test_admin_has_both_permissions(self, seed_data: dict[str, str]) -> None:
        """Bob has admin role with both permissions -- should get 200 on both."""
        app = create_test_app()
        async with AsyncTestClient(app) as client:
            resp_read = await client.get("/posts", headers={"X-User-Id": seed_data["admin_user_id"]})
            assert resp_read.status_code == 200

            resp_write = await client.get("/posts/create", headers={"X-User-Id": seed_data["admin_user_id"]})
            assert resp_write.status_code == 200


class TestSuperuserBypass:
    """Tests for superuser bypassing all permission checks."""

    async def test_superuser_bypasses_permission_check(self, seed_data: dict[str, str]) -> None:
        """Superuser has no explicit roles but should bypass permission guards."""
        app = create_test_app()
        async with AsyncTestClient(app) as client:
            resp = await client.get("/posts", headers={"X-User-Id": seed_data["superuser_id"]})
            assert resp.status_code == 200

    async def test_superuser_bypasses_write_permission(self, seed_data: dict[str, str]) -> None:
        """Superuser should bypass posts:write guard too."""
        app = create_test_app()
        async with AsyncTestClient(app) as client:
            resp = await client.get("/posts/create", headers={"X-User-Id": seed_data["superuser_id"]})
            assert resp.status_code == 200

    async def test_superuser_bypasses_role_check(self, seed_data: dict[str, str]) -> None:
        """Superuser should bypass require_role('admin') guard."""
        app = create_test_app()
        async with AsyncTestClient(app) as client:
            resp = await client.get("/admin/dashboard", headers={"X-User-Id": seed_data["superuser_id"]})
            assert resp.status_code == 200


class TestRoleGuard:
    """Tests for require_role guard."""

    async def test_user_with_admin_role_can_access(self, seed_data: dict[str, str]) -> None:
        """Bob has the admin role -- should get 200."""
        app = create_test_app()
        async with AsyncTestClient(app) as client:
            resp = await client.get("/admin/dashboard", headers={"X-User-Id": seed_data["admin_user_id"]})
            assert resp.status_code == 200
            assert resp.json()["dashboard"] == "admin"

    async def test_user_without_admin_role_gets_403(self, seed_data: dict[str, str]) -> None:
        """Alice has reader role but NOT admin -- should get 403."""
        app = create_test_app()
        async with AsyncTestClient(app) as client:
            resp = await client.get("/admin/dashboard", headers={"X-User-Id": seed_data["regular_user_id"]})
            assert resp.status_code == 403

    async def test_user_with_no_roles_gets_403_on_role_guard(self, seed_data: dict[str, str]) -> None:
        """Charlie has no roles -- should get 403 on role-guarded route."""
        app = create_test_app()
        async with AsyncTestClient(app) as client:
            resp = await client.get("/admin/dashboard", headers={"X-User-Id": seed_data["no_perms_user_id"]})
            assert resp.status_code == 403


class TestUnauthenticated:
    """Tests for unauthenticated (no user) requests."""

    async def test_unauthenticated_gets_401_on_permission_guard(self) -> None:
        """No X-User-Id header means no user in scope -- should get 401."""
        app = create_test_app()
        async with AsyncTestClient(app) as client:
            resp = await client.get("/posts")
            assert resp.status_code == 401

    async def test_unauthenticated_gets_401_on_role_guard(self) -> None:
        """No user -- require_role should return 401."""
        app = create_test_app()
        async with AsyncTestClient(app) as client:
            resp = await client.get("/admin/dashboard")
            assert resp.status_code == 401

    async def test_public_route_works_without_auth(self) -> None:
        """Unguarded route should work without authentication."""
        app = create_test_app()
        async with AsyncTestClient(app) as client:
            resp = await client.get("/public")
            assert resp.status_code == 200
            assert resp.json()["public"] is True
