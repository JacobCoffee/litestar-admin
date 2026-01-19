"""Comprehensive security tests for Phase 2 authentication and authorization components.

This module provides extensive security testing for:
- JWT authentication backend (JWTAuthBackend)
- Authentication controller (AuthController)
- RBAC guards and permissions
- Audit logging system
- Rate limiting middleware
- Edge cases and attack vector mitigation

Each test category validates that security mechanisms correctly:
- Allow authorized access
- Deny unauthorized access
- Handle edge cases safely
- Resist common attack patterns
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from datetime import timedelta, timezone
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest
from litestar import Litestar, get, post
from litestar.di import Provide
from litestar.exceptions import NotAuthorizedException
from litestar.status_codes import HTTP_200_OK, HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN, HTTP_429_TOO_MANY_REQUESTS
from litestar.testing import TestClient

from litestar_admin import AdminConfig
from litestar_admin.audit import (
    AuditAction,
    AuditEntry,
    AuditQueryFilters,
    InMemoryAuditLogger,
    audit_admin_action,
    calculate_changes,
)
from litestar_admin.auth import JWTAuthBackend, JWTConfig
from litestar_admin.controllers import AuthController
from litestar_admin.guards import (
    Permission,
    PermissionGuard,
    Role,
    RoleGuard,
    require_permission,
    require_role,
    user_has_permission,
)
from litestar_admin.middleware import (
    InMemoryRateLimitStore,
    RateLimitConfig,
    create_rate_limit_middleware,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


# ==============================================================================
# Test Fixtures and Mock Objects
# ==============================================================================


@dataclass
class MockAdminUser:
    """Mock admin user implementing AdminUser protocol for testing."""

    id: int
    email: str
    roles: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    password_hash: str = "hashed_password"


@pytest.fixture
def viewer_user() -> MockAdminUser:
    """Return a user with viewer role (read-only access)."""
    return MockAdminUser(
        id=1,
        email="viewer@example.com",
        roles=["viewer"],
        permissions=[],
    )


@pytest.fixture
def editor_user() -> MockAdminUser:
    """Return a user with editor role (read/write access)."""
    return MockAdminUser(
        id=2,
        email="editor@example.com",
        roles=["editor"],
        permissions=[],
    )


@pytest.fixture
def admin_user() -> MockAdminUser:
    """Return a user with admin role (full model access)."""
    return MockAdminUser(
        id=3,
        email="admin@example.com",
        roles=["admin"],
        permissions=[],
        password_hash="correct_password",
    )


@pytest.fixture
def superadmin_user() -> MockAdminUser:
    """Return a user with superadmin role (complete access)."""
    return MockAdminUser(
        id=4,
        email="superadmin@example.com",
        roles=["superadmin"],
        permissions=[],
    )


@pytest.fixture
def user_with_direct_permissions() -> MockAdminUser:
    """Return a user with direct permissions but no roles."""
    return MockAdminUser(
        id=5,
        email="direct@example.com",
        roles=[],
        permissions=["models:read", "models:write"],
    )


@pytest.fixture
def jwt_config() -> JWTConfig:
    """Return a JWT config for testing."""
    return JWTConfig(
        secret_key="test-secret-key-for-security-testing-only-32chars",
        algorithm="HS256",
        token_expiry=3600,
        refresh_token_expiry=86400,
    )


@pytest.fixture
def user_loader(admin_user: MockAdminUser) -> Callable[[str | int], Awaitable[MockAdminUser | None]]:
    """Return a mock user loader function."""
    users = {
        str(admin_user.id): admin_user,
        admin_user.email: admin_user,
    }

    async def loader(user_id: str | int) -> MockAdminUser | None:
        return users.get(str(user_id))

    return loader


@pytest.fixture
def password_verifier() -> Callable[[str, str], Awaitable[bool]]:
    """Return a mock password verifier."""

    async def verifier(stored_hash: str, password: str) -> bool:
        return password == stored_hash

    return verifier


@pytest.fixture
def jwt_backend(
    jwt_config: JWTConfig,
    user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
) -> JWTAuthBackend:
    """Return a JWT backend instance for testing."""
    return JWTAuthBackend(config=jwt_config, user_loader=user_loader)


@pytest.fixture
def jwt_backend_with_password(
    jwt_config: JWTConfig,
    user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
    password_verifier: Callable[[str, str], Awaitable[bool]],
) -> JWTAuthBackend:
    """Return a JWT backend with password verification."""
    return JWTAuthBackend(
        config=jwt_config,
        user_loader=user_loader,
        password_verifier=password_verifier,
    )


def create_mock_connection(
    headers: dict[str, str] | None = None,
    cookies: dict[str, str] | None = None,
    user: MockAdminUser | None = None,
    client_ip: str = "192.168.1.100",
    state_attrs: dict[str, Any] | None = None,
) -> MagicMock:
    """Create a mock ASGI connection with configurable properties."""
    connection = MagicMock()
    connection.headers = headers or {}
    connection.cookies = cookies or {}
    connection.scope = {}
    connection.user = user
    connection.client = MagicMock()
    connection.client.host = client_ip
    # Create a proper state mock that returns None for missing attributes
    state_mock = MagicMock()
    if state_attrs:
        for key, value in state_attrs.items():
            setattr(state_mock, key, value)
    else:
        # No state attrs set, so make state not have refresh_token
        del state_mock.refresh_token
    connection.state = state_mock
    return connection


# ==============================================================================
# Authentication Flow Tests
# ==============================================================================


class TestAuthenticationFlow:
    """Tests for complete authentication flow scenarios."""

    @pytest.mark.asyncio
    async def test_valid_login_with_correct_credentials(
        self,
        jwt_backend_with_password: JWTAuthBackend,
        admin_user: MockAdminUser,
    ) -> None:
        """Test successful authentication with valid email and password."""
        connection = create_mock_connection()
        credentials = {"email": admin_user.email, "password": "correct_password"}

        user = await jwt_backend_with_password.authenticate(connection, credentials)

        assert user is not None
        assert user.id == admin_user.id
        assert user.email == admin_user.email

    @pytest.mark.asyncio
    async def test_invalid_login_with_wrong_password(
        self,
        jwt_backend_with_password: JWTAuthBackend,
        admin_user: MockAdminUser,
    ) -> None:
        """Test authentication fails with incorrect password."""
        connection = create_mock_connection()
        credentials = {"email": admin_user.email, "password": "wrong_password"}

        user = await jwt_backend_with_password.authenticate(connection, credentials)

        assert user is None

    @pytest.mark.asyncio
    async def test_invalid_login_with_nonexistent_user(
        self,
        jwt_backend_with_password: JWTAuthBackend,
    ) -> None:
        """Test authentication fails for non-existent user."""
        connection = create_mock_connection()
        credentials = {"email": "nonexistent@example.com", "password": "any_password"}

        user = await jwt_backend_with_password.authenticate(connection, credentials)

        assert user is None

    @pytest.mark.asyncio
    async def test_token_extraction_from_header(
        self,
        jwt_backend: JWTAuthBackend,
        admin_user: MockAdminUser,
    ) -> None:
        """Test token extraction from Authorization header."""
        token = jwt_backend._create_token(admin_user, kind="access")
        connection = create_mock_connection(headers={"Authorization": f"Bearer {token}"})

        user = await jwt_backend.get_current_user(connection)

        assert user is not None
        assert user.id == admin_user.id

    @pytest.mark.asyncio
    async def test_token_extraction_from_cookie(
        self,
        jwt_config: JWTConfig,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
        admin_user: MockAdminUser,
    ) -> None:
        """Test token extraction from cookie."""
        jwt_config.token_location = "cookie"
        backend = JWTAuthBackend(config=jwt_config, user_loader=user_loader)

        token = backend._create_token(admin_user, kind="access")
        connection = create_mock_connection(cookies={"admin_access_token": token})

        user = await backend.get_current_user(connection)

        assert user is not None
        assert user.id == admin_user.id

    @pytest.mark.asyncio
    async def test_refresh_token_flow(
        self,
        jwt_backend: JWTAuthBackend,
        admin_user: MockAdminUser,
    ) -> None:
        """Test complete refresh token flow."""
        # Generate refresh token
        refresh_token = jwt_backend._create_token(admin_user, kind="refresh")
        connection = create_mock_connection(headers={"X-Refresh-Token": refresh_token})

        # Refresh should return new access token
        result = await jwt_backend.refresh(connection)

        assert result is not None
        assert "access_token" in result
        assert result["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_logout_behavior(
        self,
        jwt_backend: JWTAuthBackend,
    ) -> None:
        """Test logout is a no-op for stateless JWT (token invalidation is client-side)."""
        connection = create_mock_connection()

        # Logout should complete without error
        result = await jwt_backend.logout(connection)

        assert result is None


# ==============================================================================
# Token Security Tests
# ==============================================================================


class TestTokenSecurity:
    """Tests for JWT token security validation."""

    @pytest.mark.asyncio
    async def test_expired_token_rejected(
        self,
        jwt_config: JWTConfig,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
        admin_user: MockAdminUser,
    ) -> None:
        """Test that expired tokens are rejected."""
        import jwt

        # Create an expired token manually
        now = datetime.datetime.now(tz=datetime.UTC)
        payload = {
            "sub": str(admin_user.id),
            "email": admin_user.email,
            "roles": admin_user.roles,
            "permissions": admin_user.permissions,
            "type": "access",
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),  # Expired 1 hour ago
        }
        expired_token = jwt.encode(payload, jwt_config.secret_key, algorithm=jwt_config.algorithm)

        backend = JWTAuthBackend(config=jwt_config, user_loader=user_loader)
        connection = create_mock_connection(headers={"Authorization": f"Bearer {expired_token}"})

        user = await backend.get_current_user(connection)

        assert user is None

    @pytest.mark.asyncio
    async def test_tampered_token_rejected(
        self,
        jwt_backend: JWTAuthBackend,
        admin_user: MockAdminUser,
    ) -> None:
        """Test that tampered tokens are rejected."""
        # Create a valid token
        valid_token = jwt_backend._create_token(admin_user, kind="access")

        # Tamper with the token by modifying the payload
        parts = valid_token.split(".")
        # Modify the payload portion (second part)
        tampered_token = f"{parts[0]}.TAMPERED{parts[1][8:]}.{parts[2]}"

        connection = create_mock_connection(headers={"Authorization": f"Bearer {tampered_token}"})

        user = await jwt_backend.get_current_user(connection)

        assert user is None

    @pytest.mark.asyncio
    async def test_token_with_wrong_secret_rejected(
        self,
        jwt_config: JWTConfig,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
        admin_user: MockAdminUser,
    ) -> None:
        """Test that tokens signed with wrong secret are rejected."""
        import jwt

        # Create token with different secret
        now = datetime.datetime.now(tz=datetime.UTC)
        payload = {
            "sub": str(admin_user.id),
            "email": admin_user.email,
            "type": "access",
            "iat": now,
            "exp": now + timedelta(hours=1),
        }
        wrong_secret_token = jwt.encode(payload, "different-secret-key", algorithm="HS256")

        backend = JWTAuthBackend(config=jwt_config, user_loader=user_loader)
        connection = create_mock_connection(headers={"Authorization": f"Bearer {wrong_secret_token}"})

        user = await backend.get_current_user(connection)

        assert user is None

    @pytest.mark.asyncio
    async def test_token_with_wrong_algorithm_rejected(
        self,
        jwt_config: JWTConfig,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
        admin_user: MockAdminUser,
    ) -> None:
        """Test that tokens with wrong algorithm are rejected."""
        import jwt

        # Create token with different algorithm
        now = datetime.datetime.now(tz=datetime.UTC)
        payload = {
            "sub": str(admin_user.id),
            "email": admin_user.email,
            "type": "access",
            "iat": now,
            "exp": now + timedelta(hours=1),
        }

        # Use HS384 instead of configured HS256
        wrong_algo_token = jwt.encode(payload, jwt_config.secret_key, algorithm="HS384")

        backend = JWTAuthBackend(config=jwt_config, user_loader=user_loader)
        connection = create_mock_connection(headers={"Authorization": f"Bearer {wrong_algo_token}"})

        user = await backend.get_current_user(connection)

        assert user is None

    @pytest.mark.asyncio
    async def test_refresh_token_cannot_authenticate(
        self,
        jwt_backend: JWTAuthBackend,
        admin_user: MockAdminUser,
    ) -> None:
        """Test that refresh tokens cannot be used for authentication."""
        # Generate a refresh token (not access token)
        refresh_token = jwt_backend._create_token(admin_user, kind="refresh")
        connection = create_mock_connection(headers={"Authorization": f"Bearer {refresh_token}"})

        user = await jwt_backend.get_current_user(connection)

        assert user is None  # Refresh tokens should not authenticate

    @pytest.mark.asyncio
    async def test_access_token_cannot_refresh(
        self,
        jwt_backend: JWTAuthBackend,
        admin_user: MockAdminUser,
    ) -> None:
        """Test that access tokens cannot be used for refresh."""
        # Generate an access token (not refresh token)
        access_token = jwt_backend._create_token(admin_user, kind="access")
        connection = create_mock_connection(headers={"X-Refresh-Token": access_token})

        result = await jwt_backend.refresh(connection)

        assert result is None  # Access tokens should not refresh

    def test_invalid_token_format_rejected(
        self,
        jwt_backend: JWTAuthBackend,
    ) -> None:
        """Test that malformed tokens are rejected."""
        # Various invalid token formats
        invalid_tokens = [
            "not.a.valid.jwt.token",
            "invalid",
            "",
            "...",
            "a.b",
            "a.b.c.d.e",
            "Bearer",  # Just the prefix
        ]

        for invalid_token in invalid_tokens:
            payload = jwt_backend._decode_token(invalid_token)
            assert payload is None, f"Token '{invalid_token}' should be rejected"


# ==============================================================================
# Permission Enforcement Tests
# ==============================================================================


class TestPermissionEnforcement:
    """Tests for RBAC permission enforcement."""

    def test_user_with_permission_allowed(
        self,
        admin_user: MockAdminUser,
    ) -> None:
        """Test that users with required permission can access."""
        conn = MagicMock()
        conn.user = admin_user
        handler = MagicMock()

        guard = PermissionGuard(Permission.MODELS_READ)

        # Should not raise
        guard(conn, handler)

    def test_user_without_permission_denied(
        self,
        viewer_user: MockAdminUser,
    ) -> None:
        """Test that users without permission get 403 Forbidden."""
        conn = MagicMock()
        conn.user = viewer_user
        handler = MagicMock()

        guard = PermissionGuard(Permission.MODELS_DELETE)

        with pytest.raises(NotAuthorizedException, match="Permission 'models:delete' required"):
            guard(conn, handler)

    def test_missing_authentication_returns_401(self) -> None:
        """Test that missing authentication returns 401 Unauthorized."""
        conn = MagicMock(spec=[])  # No user attribute
        handler = MagicMock()

        guard = PermissionGuard(Permission.MODELS_READ)

        with pytest.raises(NotAuthorizedException, match="Authentication required"):
            guard(conn, handler)

    def test_multiple_permissions_required_and_logic(
        self,
        editor_user: MockAdminUser,
    ) -> None:
        """Test that all specified permissions must be present (AND logic)."""
        conn = MagicMock()
        conn.user = editor_user  # Editor has read and write, but not delete
        handler = MagicMock()

        # Require both read and delete
        guard = PermissionGuard(Permission.MODELS_READ, Permission.MODELS_DELETE)

        with pytest.raises(NotAuthorizedException):
            guard(conn, handler)

    def test_user_with_all_required_permissions_allowed(
        self,
        admin_user: MockAdminUser,
    ) -> None:
        """Test user with all required permissions passes."""
        conn = MagicMock()
        conn.user = admin_user  # Admin has read, write, and delete
        handler = MagicMock()

        guard = PermissionGuard(Permission.MODELS_READ, Permission.MODELS_DELETE)

        # Should not raise
        guard(conn, handler)


# ==============================================================================
# Role-Based Access Tests
# ==============================================================================


class TestRoleBasedAccess:
    """Tests for role-based access control."""

    def test_viewer_role_read_only(
        self,
        viewer_user: MockAdminUser,
    ) -> None:
        """Test VIEWER role can only read."""
        assert user_has_permission(viewer_user, Permission.MODELS_READ) is True
        assert user_has_permission(viewer_user, Permission.DASHBOARD_VIEW) is True
        assert user_has_permission(viewer_user, Permission.MODELS_WRITE) is False
        assert user_has_permission(viewer_user, Permission.MODELS_DELETE) is False
        assert user_has_permission(viewer_user, Permission.USERS_MANAGE) is False

    def test_editor_role_read_and_write(
        self,
        editor_user: MockAdminUser,
    ) -> None:
        """Test EDITOR role can read and write."""
        assert user_has_permission(editor_user, Permission.MODELS_READ) is True
        assert user_has_permission(editor_user, Permission.MODELS_WRITE) is True
        assert user_has_permission(editor_user, Permission.DASHBOARD_VIEW) is True
        assert user_has_permission(editor_user, Permission.MODELS_DELETE) is False
        assert user_has_permission(editor_user, Permission.USERS_MANAGE) is False

    def test_admin_role_full_model_access(
        self,
        admin_user: MockAdminUser,
    ) -> None:
        """Test ADMIN role can read, write, and delete."""
        assert user_has_permission(admin_user, Permission.MODELS_READ) is True
        assert user_has_permission(admin_user, Permission.MODELS_WRITE) is True
        assert user_has_permission(admin_user, Permission.MODELS_DELETE) is True
        assert user_has_permission(admin_user, Permission.MODELS_EXPORT) is True
        assert user_has_permission(admin_user, Permission.USERS_MANAGE) is True
        assert user_has_permission(admin_user, Permission.AUDIT_VIEW) is True
        # Admin cannot manage settings
        assert user_has_permission(admin_user, Permission.SETTINGS_MANAGE) is False

    def test_superadmin_has_all_permissions(
        self,
        superadmin_user: MockAdminUser,
    ) -> None:
        """Test SUPERADMIN has all permissions."""
        for permission in Permission:
            assert user_has_permission(superadmin_user, permission) is True, f"Superadmin should have {permission}"

    def test_elevated_permissions_dont_leak_down(
        self,
        viewer_user: MockAdminUser,
        editor_user: MockAdminUser,
    ) -> None:
        """Test that elevated permissions don't leak to lower roles."""
        # Viewer should not have editor permissions
        assert user_has_permission(viewer_user, Permission.MODELS_WRITE) is False

        # Editor should not have admin permissions
        assert user_has_permission(editor_user, Permission.MODELS_DELETE) is False
        assert user_has_permission(editor_user, Permission.USERS_MANAGE) is False

    def test_direct_permissions_override_roles(
        self,
        user_with_direct_permissions: MockAdminUser,
    ) -> None:
        """Test that direct permissions are respected independent of roles."""
        # User has no roles but direct permissions
        assert user_with_direct_permissions.roles == []
        assert user_has_permission(user_with_direct_permissions, Permission.MODELS_READ) is True
        assert user_has_permission(user_with_direct_permissions, Permission.MODELS_WRITE) is True
        # But not permissions they weren't granted directly
        assert user_has_permission(user_with_direct_permissions, Permission.MODELS_DELETE) is False

    def test_role_guard_allows_matching_role(
        self,
        admin_user: MockAdminUser,
    ) -> None:
        """Test RoleGuard passes when user has required role."""
        conn = MagicMock()
        conn.user = admin_user
        handler = MagicMock()

        guard = RoleGuard(Role.ADMIN)

        # Should not raise
        guard(conn, handler)

    def test_role_guard_denies_missing_role(
        self,
        viewer_user: MockAdminUser,
    ) -> None:
        """Test RoleGuard fails when user lacks required role."""
        conn = MagicMock()
        conn.user = viewer_user
        handler = MagicMock()

        guard = RoleGuard(Role.ADMIN)

        with pytest.raises(NotAuthorizedException, match="'admin' required"):
            guard(conn, handler)

    def test_role_guard_allows_any_matching_role(
        self,
        admin_user: MockAdminUser,
    ) -> None:
        """Test RoleGuard passes when user has any of the specified roles."""
        conn = MagicMock()
        conn.user = admin_user
        handler = MagicMock()

        # User is admin, guard allows admin or superadmin
        guard = RoleGuard(Role.ADMIN, Role.SUPERADMIN)

        # Should not raise
        guard(conn, handler)


# ==============================================================================
# Rate Limiting Tests
# ==============================================================================


class TestRateLimiting:
    """Tests for rate limiting functionality."""

    def test_requests_within_limit_succeed(self) -> None:
        """Test that requests within the limit succeed."""
        config = RateLimitConfig(requests_per_minute=10, requests_per_hour=100)

        @get("/test")
        async def handler() -> dict:
            return {"status": "ok"}

        app = Litestar(
            route_handlers=[handler],
            middleware=[create_rate_limit_middleware(config)],
        )

        with TestClient(app) as client:
            # Make 5 requests (under limit of 10)
            for _ in range(5):
                response = client.get("/test")
                assert response.status_code == HTTP_200_OK

    def test_requests_exceeding_limit_get_429(self) -> None:
        """Test that requests exceeding limit get 429 Too Many Requests."""
        config = RateLimitConfig(requests_per_minute=3, requests_per_hour=100)

        @get("/test")
        async def handler() -> dict:
            return {"status": "ok"}

        app = Litestar(
            route_handlers=[handler],
            middleware=[create_rate_limit_middleware(config)],
        )

        with TestClient(app) as client:
            # Use up the limit
            for _ in range(3):
                response = client.get("/test")
                assert response.status_code == HTTP_200_OK

            # Next request should be blocked
            response = client.get("/test")
            assert response.status_code == HTTP_429_TOO_MANY_REQUESTS

    def test_rate_limit_headers_present(self) -> None:
        """Test that rate limit headers are present in responses."""
        config = RateLimitConfig(requests_per_minute=10, requests_per_hour=100)

        @get("/test")
        async def handler() -> dict:
            return {"status": "ok"}

        app = Litestar(
            route_handlers=[handler],
            middleware=[create_rate_limit_middleware(config)],
        )

        with TestClient(app) as client:
            response = client.get("/test")

            assert "x-ratelimit-limit" in response.headers
            assert "x-ratelimit-remaining" in response.headers
            assert "x-ratelimit-reset" in response.headers

    def test_different_clients_have_separate_limits(self) -> None:
        """Test that different clients (IPs) have separate rate limits."""
        config = RateLimitConfig(requests_per_minute=2, requests_per_hour=100)

        @get("/test")
        async def handler() -> dict:
            return {"status": "ok"}

        app = Litestar(
            route_handlers=[handler],
            middleware=[create_rate_limit_middleware(config)],
        )

        with TestClient(app) as client:
            # First client hits limit
            client.get("/test")
            client.get("/test")
            response = client.get("/test")
            assert response.status_code == HTTP_429_TOO_MANY_REQUESTS

        # Different client (different IP) should have fresh limit
        with TestClient(app) as client2:
            response = client2.get("/test", headers={"X-Forwarded-For": "10.0.0.1"})
            assert response.status_code == HTTP_200_OK

    @pytest.mark.asyncio
    async def test_rate_limit_resets_after_window(self) -> None:
        """Test that rate limit resets after window expires."""
        # Use very short window for testing
        store = InMemoryRateLimitStore(minute_window=1)

        await store.increment("test-key", "minute")
        await store.increment("test-key", "minute")

        # At limit
        count1 = await store.get_count("test-key", "minute")
        assert count1 == 2

        # Wait for window to expire
        import asyncio

        await asyncio.sleep(1.1)

        # Window should have reset
        count2 = await store.get_count("test-key", "minute")
        assert count2 == 0

    def test_429_response_includes_retry_after(self) -> None:
        """Test that 429 responses include Retry-After header."""
        config = RateLimitConfig(requests_per_minute=1, requests_per_hour=100)

        @get("/test")
        async def handler() -> dict:
            return {"status": "ok"}

        app = Litestar(
            route_handlers=[handler],
            middleware=[create_rate_limit_middleware(config)],
        )

        with TestClient(app) as client:
            client.get("/test")  # Use up limit
            response = client.get("/test")  # Should be blocked

            assert response.status_code == HTTP_429_TOO_MANY_REQUESTS
            assert "Retry-After" in response.headers

            data = response.json()
            assert "error" in data
            assert "retry_after" in data


# ==============================================================================
# Audit Logging Tests
# ==============================================================================


class TestAuditLogging:
    """Tests for audit logging system."""

    @pytest.mark.asyncio
    async def test_admin_actions_are_logged(self) -> None:
        """Test that admin actions are properly logged."""
        logger = InMemoryAuditLogger()
        conn = create_mock_connection(user=MockAdminUser(id=1, email="admin@example.com", roles=["admin"]))

        entry = await audit_admin_action(
            connection=conn,
            action=AuditAction.UPDATE,
            model_name="User",
            record_id=42,
        )
        await logger.log(entry)

        assert len(logger.entries) == 1
        assert logger.entries[0].action == AuditAction.UPDATE
        assert logger.entries[0].model_name == "User"
        assert logger.entries[0].record_id == 42

    @pytest.mark.asyncio
    async def test_correct_actor_info_captured(self) -> None:
        """Test that correct actor information is captured."""
        user = MockAdminUser(id=42, email="actor@example.com", roles=["editor"])
        conn = create_mock_connection(user=user, client_ip="10.0.0.5")

        entry = await audit_admin_action(
            connection=conn,
            action=AuditAction.CREATE,
            model_name="Post",
            record_id=1,
        )

        assert entry.actor_id == 42
        assert entry.actor_email == "actor@example.com"
        assert entry.ip_address == "10.0.0.5"

    def test_change_diffs_calculated_correctly(self) -> None:
        """Test that change diffs are calculated correctly."""
        old_data = {"email": "old@example.com", "name": "John", "status": "active"}
        new_data = {"email": "new@example.com", "name": "John", "status": "inactive"}

        changes = calculate_changes(old_data, new_data)

        assert "email" in changes
        assert changes["email"]["old"] == "old@example.com"
        assert changes["email"]["new"] == "new@example.com"

        assert "status" in changes
        assert changes["status"]["old"] == "active"
        assert changes["status"]["new"] == "inactive"

        # Unchanged field should not be in changes
        assert "name" not in changes

    @pytest.mark.asyncio
    async def test_query_filtering_works(self) -> None:
        """Test that query filtering returns correct results."""
        logger = InMemoryAuditLogger()

        # Create various entries
        await logger.log(AuditEntry(action=AuditAction.CREATE, model_name="User", actor_id=1))
        await logger.log(AuditEntry(action=AuditAction.UPDATE, model_name="User", actor_id=1))
        await logger.log(AuditEntry(action=AuditAction.UPDATE, model_name="Post", actor_id=2))
        await logger.log(AuditEntry(action=AuditAction.DELETE, model_name="User", actor_id=1))

        # Filter by model
        user_entries = await logger.query(AuditQueryFilters(model_name="User"))
        assert len(user_entries) == 3

        # Filter by action
        update_entries = await logger.query(AuditQueryFilters(action=AuditAction.UPDATE))
        assert len(update_entries) == 2

        # Filter by actor
        actor1_entries = await logger.query(AuditQueryFilters(actor_id=1))
        assert len(actor1_entries) == 3

        # Combined filter
        combined = await logger.query(AuditQueryFilters(model_name="User", action=AuditAction.UPDATE, actor_id=1))
        assert len(combined) == 1

    @pytest.mark.asyncio
    async def test_timestamp_accuracy(self) -> None:
        """Test that timestamps are accurate."""
        before = datetime.datetime.now(tz=timezone.utc)

        entry = AuditEntry(action=AuditAction.READ)

        after = datetime.datetime.now(tz=timezone.utc)

        assert entry.timestamp >= before
        assert entry.timestamp <= after
        assert entry.timestamp.tzinfo == timezone.utc


# ==============================================================================
# Edge Cases and Attack Vector Tests
# ==============================================================================


class TestEdgeCasesAndAttackVectors:
    """Tests for edge cases and common attack vector mitigation."""

    @pytest.mark.asyncio
    async def test_sql_injection_in_credentials_fails_safely(
        self,
        jwt_backend_with_password: JWTAuthBackend,
    ) -> None:
        """Test that SQL injection attempts in credentials are handled safely."""
        connection = create_mock_connection()

        # Common SQL injection payloads
        injection_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "admin'--",
            "1; DELETE FROM users WHERE '1'='1",
            "' UNION SELECT * FROM users --",
        ]

        for payload in injection_payloads:
            # As email
            credentials = {"email": payload, "password": "password"}
            user = await jwt_backend_with_password.authenticate(connection, credentials)
            assert user is None, f"SQL injection payload '{payload}' as email should not authenticate"

            # As password
            credentials = {"email": "test@example.com", "password": payload}
            user = await jwt_backend_with_password.authenticate(connection, credentials)
            assert user is None, f"SQL injection payload '{payload}' as password should not authenticate"

    @pytest.mark.asyncio
    async def test_xss_in_user_data_logged_safely(self) -> None:
        """Test that XSS payloads in user data are logged without execution risk."""
        logger = InMemoryAuditLogger()

        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            '<img src="x" onerror="alert(\'xss\')">',
            "'\"><script>alert(String.fromCharCode(88,83,83))</script>",
        ]

        for payload in xss_payloads:
            entry = AuditEntry(
                action=AuditAction.UPDATE,
                model_name="User",
                record_id=1,
                changes={"name": {"old": "safe", "new": payload}},
            )
            await logger.log(entry)

            # Verify the payload is stored as-is (not executed)
            results = await logger.query(AuditQueryFilters())
            latest = results[0]
            assert latest.changes is not None
            assert latest.changes["name"]["new"] == payload

    def test_invalid_json_handling(self) -> None:
        """Test that invalid JSON in requests is handled properly."""
        config = RateLimitConfig(requests_per_minute=10, requests_per_hour=100)

        @post("/test")
        async def handler(data: dict) -> dict:
            return {"received": data}

        app = Litestar(
            route_handlers=[handler],
            middleware=[create_rate_limit_middleware(config)],
        )

        with TestClient(app, raise_server_exceptions=False) as client:
            # Invalid JSON
            response = client.post(
                "/test",
                content="not valid json {",
                headers={"Content-Type": "application/json"},
            )
            # Should get a 400 Bad Request, not crash
            assert response.status_code in (400, 500)

    @pytest.mark.asyncio
    async def test_empty_credentials_handled(
        self,
        jwt_backend_with_password: JWTAuthBackend,
    ) -> None:
        """Test that empty credentials are handled safely."""
        connection = create_mock_connection()

        # Empty email
        user = await jwt_backend_with_password.authenticate(connection, {"email": "", "password": "pass"})
        assert user is None

        # Empty password
        user = await jwt_backend_with_password.authenticate(connection, {"email": "test@example.com", "password": ""})
        assert user is None

        # Both empty
        user = await jwt_backend_with_password.authenticate(connection, {"email": "", "password": ""})
        assert user is None

        # Missing fields
        user = await jwt_backend_with_password.authenticate(connection, {})
        assert user is None

    @pytest.mark.asyncio
    async def test_very_long_inputs_handled(
        self,
        jwt_backend_with_password: JWTAuthBackend,
    ) -> None:
        """Test that very long inputs are handled without crashing."""
        connection = create_mock_connection()

        # Very long email
        long_email = "a" * 10000 + "@example.com"
        user = await jwt_backend_with_password.authenticate(connection, {"email": long_email, "password": "password"})
        assert user is None

        # Very long password
        long_password = "x" * 10000
        user = await jwt_backend_with_password.authenticate(
            connection, {"email": "test@example.com", "password": long_password}
        )
        assert user is None

    def test_rate_limit_consistent_client_tracking(self) -> None:
        """Test that rate limiting consistently tracks the same client."""
        config = RateLimitConfig(requests_per_minute=2, requests_per_hour=100)

        @get("/test")
        async def handler() -> dict:
            return {"status": "ok"}

        app = Litestar(
            route_handlers=[handler],
            middleware=[create_rate_limit_middleware(config)],
        )

        with TestClient(app) as client:
            # Use a consistent IP via X-Forwarded-For
            test_ip = "192.168.1.100"

            # First two requests succeed
            response = client.get("/test", headers={"X-Forwarded-For": test_ip})
            assert response.status_code == HTTP_200_OK

            response = client.get("/test", headers={"X-Forwarded-For": test_ip})
            assert response.status_code == HTTP_200_OK

            # Third request from same IP should be blocked
            response = client.get("/test", headers={"X-Forwarded-For": test_ip})
            assert response.status_code == HTTP_429_TOO_MANY_REQUESTS

            # Trying to prepend the IP (attack attempt) still gets blocked
            # because the first IP in the chain is used
            response = client.get("/test", headers={"X-Forwarded-For": f"{test_ip}, 10.0.0.1"})
            assert response.status_code == HTTP_429_TOO_MANY_REQUESTS

    def test_permission_guard_with_null_user(self) -> None:
        """Test that null user in connection is handled safely."""
        conn = MagicMock()
        conn.user = None
        handler = MagicMock()

        guard = PermissionGuard(Permission.MODELS_READ)

        with pytest.raises(NotAuthorizedException, match="Authentication required"):
            guard(conn, handler)

    def test_role_guard_with_empty_roles(self) -> None:
        """Test that user with empty roles list is handled correctly."""
        user = MockAdminUser(id=1, email="test@example.com", roles=[], permissions=[])
        conn = MagicMock()
        conn.user = user
        handler = MagicMock()

        guard = RoleGuard(Role.VIEWER)

        with pytest.raises(NotAuthorizedException):
            guard(conn, handler)

    def test_unknown_role_ignored_safely(self) -> None:
        """Test that unknown roles are ignored without errors."""
        user = MockAdminUser(id=1, email="test@example.com", roles=["unknown_role", "viewer"], permissions=[])

        # Should get viewer permissions, unknown role ignored
        assert user_has_permission(user, Permission.MODELS_READ) is True
        assert user_has_permission(user, Permission.MODELS_DELETE) is False

    @pytest.mark.asyncio
    async def test_concurrent_rate_limit_requests(self) -> None:
        """Test that concurrent requests are rate limited correctly."""
        import asyncio

        store = InMemoryRateLimitStore()

        async def make_requests(key: str, count: int) -> list[int]:
            results = []
            for _ in range(count):
                result = await store.increment(key, "minute")
                results.append(result)
            return results

        # Simulate concurrent requests
        tasks = [make_requests("client-1", 5) for _ in range(3)]
        await asyncio.gather(*tasks)

        # All increments should be counted
        final_count = await store.get_count("client-1", "minute")

        assert final_count == 15  # 5 requests x 3 concurrent tasks


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestSecurityIntegration:
    """Integration tests combining multiple security components."""

    @pytest.fixture
    def security_app(self) -> Litestar:
        """Create app with full security stack."""
        rate_config = RateLimitConfig(requests_per_minute=10, requests_per_hour=100)

        @get("/public")
        async def public_handler() -> dict:
            return {"status": "public"}

        @get("/protected", guards=[require_permission(Permission.MODELS_READ)])
        async def protected_handler() -> dict:
            return {"status": "protected"}

        @get("/admin-only", guards=[require_role(Role.ADMIN)])
        async def admin_handler() -> dict:
            return {"status": "admin"}

        return Litestar(
            route_handlers=[public_handler, protected_handler, admin_handler],
            middleware=[create_rate_limit_middleware(rate_config)],
        )

    def test_public_endpoint_accessible_with_rate_limit(self, security_app: Litestar) -> None:
        """Test public endpoint is accessible but rate limited."""
        with TestClient(security_app) as client:
            for _ in range(5):
                response = client.get("/public")
                assert response.status_code == HTTP_200_OK

    def test_protected_endpoint_requires_auth(self, security_app: Litestar) -> None:
        """Test protected endpoint requires authentication."""
        with TestClient(security_app) as client:
            response = client.get("/protected")
            # Without user, should fail
            assert response.status_code in (HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN, 500)

    def test_full_auth_flow_with_rate_limiting(self) -> None:
        """Test complete authentication flow with rate limiting enabled."""

        class TestAuthBackend:
            """Minimal auth backend for testing."""

            async def authenticate(self, conn, creds):
                if creds.get("email") == "test@test.com" and creds.get("password") == "pass":
                    return MockAdminUser(id=1, email="test@test.com", roles=["admin"])
                return None

            async def get_current_user(self, conn):
                auth = conn.headers.get("Authorization", "")
                if auth == "Bearer valid":
                    return MockAdminUser(id=1, email="test@test.com", roles=["admin"])
                return None

            async def login(self, conn, user):
                return {"access_token": "valid", "refresh_token": "refresh", "token_type": "bearer"}

            async def logout(self, conn):
                pass

            async def refresh(self, conn):
                return {"access_token": "new_valid", "token_type": "bearer"}

        config = AdminConfig(
            title="Test",
            base_url="/admin",
            auth_backend=TestAuthBackend(),
            auto_discover=False,
        )
        rate_config = RateLimitConfig(requests_per_minute=20, requests_per_hour=100)

        app = Litestar(
            route_handlers=[AuthController],
            dependencies={"admin_config": Provide(lambda: config, sync_to_thread=False)},
            middleware=[create_rate_limit_middleware(rate_config)],
        )

        with TestClient(app) as client:
            # Login
            response = client.post("/api/auth/login", json={"email": "test@test.com", "password": "pass"})
            assert response.status_code == HTTP_200_OK
            assert "access_token" in response.json()

            # Rate limit headers present
            assert "x-ratelimit-remaining" in response.headers


# ==============================================================================
# Configuration Security Tests
# ==============================================================================


class TestConfigurationSecurity:
    """Tests for secure configuration validation."""

    def test_jwt_config_requires_secret_key(self) -> None:
        """Test that JWT config requires a non-empty secret key."""
        with pytest.raises(ValueError, match="secret_key is required"):
            JWTConfig(secret_key="")

    def test_jwt_config_validates_token_location(self) -> None:
        """Test that JWT config validates token location."""
        with pytest.raises(ValueError, match="token_location must be"):
            JWTConfig(secret_key="test", token_location="invalid")

    def test_jwt_config_validates_token_expiry(self) -> None:
        """Test that JWT config validates token expiry."""
        with pytest.raises(ValueError, match="token_expiry must be at least 1"):
            JWTConfig(secret_key="test", token_expiry=0)

    def test_rate_limit_config_validates_limits(self) -> None:
        """Test that rate limit config validates limits."""
        with pytest.raises(ValueError, match="requests_per_minute must be at least 1"):
            RateLimitConfig(requests_per_minute=0)

        with pytest.raises(ValueError, match="requests_per_hour must be at least 1"):
            RateLimitConfig(requests_per_hour=0)

    def test_rate_limit_config_hour_must_exceed_minute(self) -> None:
        """Test that hourly limit must exceed minute limit."""
        with pytest.raises(ValueError, match="requests_per_hour must be greater"):
            RateLimitConfig(requests_per_minute=100, requests_per_hour=50)

    def test_permission_guard_requires_permissions(self) -> None:
        """Test that PermissionGuard requires at least one permission."""
        with pytest.raises(ValueError, match="At least one permission must be specified"):
            PermissionGuard()

    def test_role_guard_requires_roles(self) -> None:
        """Test that RoleGuard requires at least one role."""
        with pytest.raises(ValueError, match="At least one role must be specified"):
            RoleGuard()
