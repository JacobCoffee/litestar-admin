"""Unit tests for AuthController."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from litestar import Litestar
from litestar.di import Provide
from litestar.testing import AsyncTestClient

from litestar_admin import AdminConfig
from litestar_admin.controllers import AuthController

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from litestar.connection import ASGIConnection


# ==============================================================================
# Test Fixtures
# ==============================================================================


@dataclass
class MockAdminUser:
    """Mock admin user for testing."""

    id: int
    email: str
    roles: list[str]
    permissions: list[str]
    password_hash: str = "hashed_password"


class MockAuthBackend:
    """Mock authentication backend for testing."""

    def __init__(self) -> None:
        """Initialize mock backend with test user."""
        self.users = {
            "admin@example.com": MockAdminUser(
                id=1,
                email="admin@example.com",
                roles=["admin"],
                permissions=["read", "write", "delete"],
                password_hash="correct_password",
            ),
            "user@example.com": MockAdminUser(
                id=2,
                email="user@example.com",
                roles=["user"],
                permissions=["read"],
                password_hash="user_password",
            ),
        }
        self._current_user: MockAdminUser | None = None
        self._refresh_tokens: dict[str, str] = {}

    async def authenticate(
        self,
        connection: ASGIConnection,
        credentials: dict[str, str],
    ) -> MockAdminUser | None:
        """Authenticate user with credentials."""
        email = credentials.get("email")
        password = credentials.get("password")

        if not email or not password:
            return None

        user = self.users.get(email)
        if user is None:
            return None

        # Simple password check for testing
        if password != user.password_hash:
            return None

        return user

    async def get_current_user(
        self,
        connection: ASGIConnection,
    ) -> MockAdminUser | None:
        """Get current authenticated user."""
        # Check for auth header
        auth_header = connection.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            if token == "valid_access_token":
                return self.users.get("admin@example.com")
            if token == "user_access_token":
                return self.users.get("user@example.com")
        return None

    async def login(
        self,
        connection: ASGIConnection,
        user: MockAdminUser,
    ) -> dict[str, str]:
        """Create session for user."""
        access_token = f"access_{user.email}"
        refresh_token = f"refresh_{user.email}"
        self._refresh_tokens[refresh_token] = user.email
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": "3600",
        }

    async def logout(
        self,
        connection: ASGIConnection,
    ) -> None:
        """Logout current user."""
        self._current_user = None

    async def refresh(
        self,
        connection: ASGIConnection,
    ) -> dict[str, str] | None:
        """Refresh access token."""
        refresh_token = getattr(connection.state, "refresh_token", None)
        if not refresh_token:
            return None

        email = self._refresh_tokens.get(refresh_token)
        if not email:
            return None

        user = self.users.get(email)
        if not user:
            return None

        return {
            "access_token": f"new_access_{email}",
            "token_type": "bearer",
            "expires_in": "3600",
        }


@pytest.fixture
def mock_auth_backend() -> MockAuthBackend:
    """Create a mock auth backend."""
    return MockAuthBackend()


@pytest.fixture
def auth_config(mock_auth_backend: MockAuthBackend) -> AdminConfig:
    """Create admin config with mock auth backend."""
    return AdminConfig(
        title="Auth Test Admin",
        base_url="/admin",
        auth_backend=mock_auth_backend,
        auto_discover=False,
        debug=True,
    )


@pytest.fixture
def no_auth_config() -> AdminConfig:
    """Create admin config without auth backend."""
    return AdminConfig(
        title="No Auth Admin",
        base_url="/admin",
        auth_backend=None,
        auto_discover=False,
        debug=True,
    )


@pytest.fixture
async def auth_app(auth_config: AdminConfig) -> Litestar:
    """Create a Litestar app with AuthController."""
    return Litestar(
        route_handlers=[AuthController],
        dependencies={
            "admin_config": Provide(lambda: auth_config, sync_to_thread=False),
        },
        debug=True,
    )


@pytest.fixture
async def no_auth_app(no_auth_config: AdminConfig) -> Litestar:
    """Create a Litestar app without auth backend."""
    return Litestar(
        route_handlers=[AuthController],
        dependencies={
            "admin_config": Provide(lambda: no_auth_config, sync_to_thread=False),
        },
        debug=True,
    )


@pytest.fixture
async def client(auth_app: Litestar) -> AsyncIterator[AsyncTestClient[Litestar]]:
    """Create an async test client with auth."""
    async with AsyncTestClient(auth_app) as test_client:
        yield test_client


@pytest.fixture
async def no_auth_client(no_auth_app: Litestar) -> AsyncIterator[AsyncTestClient[Litestar]]:
    """Create an async test client without auth."""
    async with AsyncTestClient(no_auth_app) as test_client:
        yield test_client


# ==============================================================================
# Login Endpoint Tests
# ==============================================================================


class TestLoginEndpoint:
    """Tests for POST /api/auth/login endpoint."""

    async def test_login_success(self, client: AsyncTestClient) -> None:
        """Test successful login with valid credentials."""
        response = await client.post(
            "/api/auth/login",
            json={"email": "admin@example.com", "password": "correct_password"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["access_token"] == "access_admin@example.com"
        assert data["refresh_token"] == "refresh_admin@example.com"

    async def test_login_invalid_password(self, client: AsyncTestClient) -> None:
        """Test login with invalid password."""
        response = await client.post(
            "/api/auth/login",
            json={"email": "admin@example.com", "password": "wrong_password"},
        )

        assert response.status_code == 401

    async def test_login_invalid_email(self, client: AsyncTestClient) -> None:
        """Test login with non-existent email."""
        response = await client.post(
            "/api/auth/login",
            json={"email": "nonexistent@example.com", "password": "any_password"},
        )

        assert response.status_code == 401

    async def test_login_no_auth_backend(self, no_auth_client: AsyncTestClient) -> None:
        """Test login when no auth backend is configured."""
        response = await no_auth_client.post(
            "/api/auth/login",
            json={"email": "admin@example.com", "password": "password"},
        )

        assert response.status_code == 401


# ==============================================================================
# Logout Endpoint Tests
# ==============================================================================


class TestLogoutEndpoint:
    """Tests for POST /api/auth/logout endpoint."""

    async def test_logout_success(self, client: AsyncTestClient) -> None:
        """Test successful logout."""
        response = await client.post("/api/auth/logout")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["message"] == "Logged out successfully"

    async def test_logout_no_auth_backend(self, no_auth_client: AsyncTestClient) -> None:
        """Test logout when no auth backend is configured."""
        response = await no_auth_client.post("/api/auth/logout")

        assert response.status_code == 401


# ==============================================================================
# Refresh Endpoint Tests
# ==============================================================================


class TestRefreshEndpoint:
    """Tests for POST /api/auth/refresh endpoint."""

    async def test_refresh_success(self, client: AsyncTestClient, mock_auth_backend: MockAuthBackend) -> None:
        """Test successful token refresh."""
        # First login to get a refresh token
        login_response = await client.post(
            "/api/auth/login",
            json={"email": "admin@example.com", "password": "correct_password"},
        )
        refresh_token = login_response.json()["refresh_token"]

        # Now refresh
        response = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["access_token"] == "new_access_admin@example.com"

    async def test_refresh_invalid_token(self, client: AsyncTestClient) -> None:
        """Test refresh with invalid token."""
        response = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid_token"},
        )

        assert response.status_code == 401

    async def test_refresh_no_auth_backend(self, no_auth_client: AsyncTestClient) -> None:
        """Test refresh when no auth backend is configured."""
        response = await no_auth_client.post(
            "/api/auth/refresh",
            json={"refresh_token": "any_token"},
        )

        assert response.status_code == 401


# ==============================================================================
# Me Endpoint Tests
# ==============================================================================


class TestMeEndpoint:
    """Tests for GET /api/auth/me endpoint."""

    async def test_me_authenticated(self, client: AsyncTestClient) -> None:
        """Test getting current user when authenticated."""
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer valid_access_token"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == 1
        assert data["email"] == "admin@example.com"
        assert data["roles"] == ["admin"]
        assert data["permissions"] == ["read", "write", "delete"]

    async def test_me_different_user(self, client: AsyncTestClient) -> None:
        """Test getting current user for different user."""
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer user_access_token"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == 2
        assert data["email"] == "user@example.com"
        assert data["roles"] == ["user"]
        assert data["permissions"] == ["read"]

    async def test_me_not_authenticated(self, client: AsyncTestClient) -> None:
        """Test getting current user when not authenticated."""
        response = await client.get("/api/auth/me")

        assert response.status_code == 403

    async def test_me_invalid_token(self, client: AsyncTestClient) -> None:
        """Test getting current user with invalid token."""
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == 403

    async def test_me_no_auth_backend(self, no_auth_client: AsyncTestClient) -> None:
        """Test me endpoint when no auth backend is configured."""
        response = await no_auth_client.get("/api/auth/me")

        assert response.status_code == 401


# ==============================================================================
# DTO Tests
# ==============================================================================


class TestDTOs:
    """Tests for auth DTOs."""

    def test_login_request_fields(self) -> None:
        """Test LoginRequest dataclass fields."""
        from litestar_admin.controllers.auth import LoginRequest

        request = LoginRequest(email="test@example.com", password="secret")
        assert request.email == "test@example.com"
        assert request.password == "secret"

    def test_token_response_defaults(self) -> None:
        """Test TokenResponse dataclass defaults."""
        from litestar_admin.controllers.auth import TokenResponse

        response = TokenResponse(access_token="access", refresh_token="refresh")
        assert response.access_token == "access"
        assert response.refresh_token == "refresh"
        assert response.token_type == "bearer"
        assert response.expires_in is None

    def test_user_response_fields(self) -> None:
        """Test UserResponse dataclass fields."""
        from litestar_admin.controllers.auth import UserResponse

        response = UserResponse(
            id=1,
            email="test@example.com",
            roles=["admin", "user"],
            permissions=["read", "write"],
        )
        assert response.id == 1
        assert response.email == "test@example.com"
        assert response.roles == ["admin", "user"]
        assert response.permissions == ["read", "write"]

    def test_logout_response_defaults(self) -> None:
        """Test LogoutResponse dataclass defaults."""
        from litestar_admin.controllers.auth import LogoutResponse

        response = LogoutResponse(success=True)
        assert response.success is True
        assert response.message == "Logged out successfully"

    def test_refresh_request_fields(self) -> None:
        """Test RefreshRequest dataclass fields."""
        from litestar_admin.controllers.auth import RefreshRequest

        request = RefreshRequest(refresh_token="token123")
        assert request.refresh_token == "token123"


# ==============================================================================
# Controller Configuration Tests
# ==============================================================================


class TestControllerConfiguration:
    """Tests for AuthController configuration."""

    def test_controller_path(self) -> None:
        """Test controller path is correct."""
        assert AuthController.path == "/api/auth"

    def test_controller_tags(self) -> None:
        """Test controller tags for OpenAPI."""
        assert AuthController.tags == ["Authentication"]
