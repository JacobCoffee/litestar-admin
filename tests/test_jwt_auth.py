"""Tests for JWT authentication backend."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest

from litestar_admin.auth import JWTAuthBackend, JWTConfig

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable



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


@pytest.fixture
def mock_user() -> MockAdminUser:
    """Return a mock admin user."""
    return MockAdminUser(
        id=1,
        email="admin@example.com",
        roles=["admin"],
        permissions=["models.read", "models.write"],
    )


@pytest.fixture
def jwt_config() -> JWTConfig:
    """Return a basic JWT config for testing."""
    return JWTConfig(
        secret_key="test-secret-key-for-testing-only",
        algorithm="HS256",
        token_expiry=3600,
        refresh_token_expiry=86400,
    )


@pytest.fixture
def user_loader(mock_user: MockAdminUser) -> Callable[[str | int], Awaitable[MockAdminUser | None]]:
    """Return a mock user loader function."""

    async def loader(user_id: str | int) -> MockAdminUser | None:
        if str(user_id) in (str(mock_user.id), mock_user.email):
            return mock_user
        return None

    return loader


@pytest.fixture
def password_verifier() -> Callable[[str, str], Awaitable[bool]]:
    """Return a mock password verifier."""

    async def verifier(stored_hash: str, password: str) -> bool:
        return password == "correct_password"

    return verifier


@pytest.fixture
def jwt_backend(
    jwt_config: JWTConfig,
    user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
) -> JWTAuthBackend:
    """Return a JWT backend instance."""
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
    state_attrs: dict[str, Any] | None = None,
) -> MagicMock:
    """Create a mock ASGI connection."""
    connection = MagicMock()
    connection.headers = headers or {}
    connection.cookies = cookies or {}
    connection.scope = {}
    # Create a proper state mock that returns None for missing attributes
    state_mock = MagicMock()
    state_mock.configure_mock(**(state_attrs or {}))
    # Override getattr behavior for state to return None for unset attributes
    if state_attrs:
        for key, value in state_attrs.items():
            setattr(state_mock, key, value)
    else:
        # No state attrs set, so make state not have refresh_token
        del state_mock.refresh_token
    connection.state = state_mock
    return connection


# ==============================================================================
# JWTConfig Tests
# ==============================================================================


class TestJWTConfig:
    """Tests for JWTConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = JWTConfig(secret_key="test-secret")

        assert config.algorithm == "HS256"
        assert config.token_expiry == 3600
        assert config.refresh_token_expiry == 86400
        assert config.token_location == "header"
        assert config.token_header == "Authorization"
        assert config.token_prefix == "Bearer"
        assert config.cookie_name == "admin_access_token"
        assert config.cookie_secure is True
        assert config.cookie_httponly is True
        assert config.cookie_samesite == "lax"
        assert config.issuer is None
        assert config.audience is None

    def test_custom_values(self) -> None:
        """Test configuration with custom values."""
        config = JWTConfig(
            secret_key="my-secret",
            algorithm="HS512",
            token_expiry=7200,
            refresh_token_expiry=172800,
            token_location="cookie",
            cookie_name="my_token",
            cookie_secure=False,
            issuer="my-app",
            audience="my-audience",
        )

        assert config.algorithm == "HS512"
        assert config.token_expiry == 7200
        assert config.refresh_token_expiry == 172800
        assert config.token_location == "cookie"
        assert config.cookie_name == "my_token"
        assert config.cookie_secure is False
        assert config.issuer == "my-app"
        assert config.audience == "my-audience"

    def test_empty_secret_key_raises_error(self) -> None:
        """Test that empty secret_key raises ValueError."""
        with pytest.raises(ValueError, match="secret_key is required"):
            JWTConfig(secret_key="")

    def test_invalid_token_location_raises_error(self) -> None:
        """Test that invalid token_location raises ValueError."""
        with pytest.raises(ValueError, match="token_location must be 'header' or 'cookie'"):
            JWTConfig(secret_key="test", token_location="invalid")

    def test_invalid_token_expiry_raises_error(self) -> None:
        """Test that token_expiry less than 1 raises ValueError."""
        with pytest.raises(ValueError, match="token_expiry must be at least 1 second"):
            JWTConfig(secret_key="test", token_expiry=0)

    def test_invalid_refresh_token_expiry_raises_error(self) -> None:
        """Test that refresh_token_expiry less than 1 raises ValueError."""
        with pytest.raises(ValueError, match="refresh_token_expiry must be at least 1 second"):
            JWTConfig(secret_key="test", refresh_token_expiry=0)

    def test_invalid_cookie_samesite_raises_error(self) -> None:
        """Test that invalid cookie_samesite raises ValueError."""
        with pytest.raises(ValueError, match="cookie_samesite must be 'strict', 'lax', or 'none'"):
            JWTConfig(secret_key="test", cookie_samesite="invalid")

    def test_valid_cookie_samesite_values(self) -> None:
        """Test that valid cookie_samesite values are accepted."""
        for samesite in ["strict", "lax", "none", "Strict", "Lax", "None"]:
            config = JWTConfig(secret_key="test", cookie_samesite=samesite)
            assert config.cookie_samesite == samesite


# ==============================================================================
# JWTAuthBackend Tests
# ==============================================================================


class TestJWTAuthBackend:
    """Tests for JWTAuthBackend class."""

    def test_initialization(
        self,
        jwt_config: JWTConfig,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
    ) -> None:
        """Test backend initialization."""
        backend = JWTAuthBackend(config=jwt_config, user_loader=user_loader)

        assert backend.config is jwt_config
        assert backend.user_loader is user_loader
        assert backend.password_verifier is None

    def test_initialization_with_password_verifier(
        self,
        jwt_config: JWTConfig,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
        password_verifier: Callable[[str, str], Awaitable[bool]],
    ) -> None:
        """Test backend initialization with password verifier."""
        backend = JWTAuthBackend(
            config=jwt_config,
            user_loader=user_loader,
            password_verifier=password_verifier,
        )

        assert backend.password_verifier is password_verifier


class TestJWTAuthBackendAuthenticate:
    """Tests for JWTAuthBackend.authenticate method."""

    @pytest.mark.asyncio
    async def test_authenticate_success_without_password_verifier(
        self,
        jwt_backend: JWTAuthBackend,
        mock_user: MockAdminUser,
    ) -> None:
        """Test successful authentication without password verification."""
        connection = create_mock_connection()
        credentials = {"email": "admin@example.com", "password": "any_password"}

        user = await jwt_backend.authenticate(connection, credentials)

        assert user is not None
        assert user.id == mock_user.id
        assert user.email == mock_user.email

    @pytest.mark.asyncio
    async def test_authenticate_success_with_password_verifier(
        self,
        jwt_backend_with_password: JWTAuthBackend,
        mock_user: MockAdminUser,
    ) -> None:
        """Test successful authentication with correct password."""
        connection = create_mock_connection()
        credentials = {"email": "admin@example.com", "password": "correct_password"}

        user = await jwt_backend_with_password.authenticate(connection, credentials)

        assert user is not None
        assert user.id == mock_user.id

    @pytest.mark.asyncio
    async def test_authenticate_fails_with_wrong_password(
        self,
        jwt_backend_with_password: JWTAuthBackend,
    ) -> None:
        """Test authentication fails with wrong password."""
        connection = create_mock_connection()
        credentials = {"email": "admin@example.com", "password": "wrong_password"}

        user = await jwt_backend_with_password.authenticate(connection, credentials)

        assert user is None

    @pytest.mark.asyncio
    async def test_authenticate_fails_with_missing_email(
        self,
        jwt_backend: JWTAuthBackend,
    ) -> None:
        """Test authentication fails when email is missing."""
        connection = create_mock_connection()
        credentials = {"password": "password"}

        user = await jwt_backend.authenticate(connection, credentials)

        assert user is None

    @pytest.mark.asyncio
    async def test_authenticate_fails_with_missing_password(
        self,
        jwt_backend: JWTAuthBackend,
    ) -> None:
        """Test authentication fails when password is missing."""
        connection = create_mock_connection()
        credentials = {"email": "admin@example.com"}

        user = await jwt_backend.authenticate(connection, credentials)

        assert user is None

    @pytest.mark.asyncio
    async def test_authenticate_fails_with_unknown_user(
        self,
        jwt_backend: JWTAuthBackend,
    ) -> None:
        """Test authentication fails for unknown user."""
        connection = create_mock_connection()
        credentials = {"email": "unknown@example.com", "password": "password"}

        user = await jwt_backend.authenticate(connection, credentials)

        assert user is None


class TestJWTAuthBackendLogin:
    """Tests for JWTAuthBackend.login method."""

    @pytest.mark.asyncio
    async def test_login_returns_tokens(
        self,
        jwt_backend: JWTAuthBackend,
        mock_user: MockAdminUser,
    ) -> None:
        """Test login returns access and refresh tokens."""
        connection = create_mock_connection()

        result = await jwt_backend.login(connection, mock_user)

        assert "access_token" in result
        assert "refresh_token" in result
        assert result["token_type"] == "bearer"
        assert result["expires_in"] == "3600"

    @pytest.mark.asyncio
    async def test_login_tokens_are_different(
        self,
        jwt_backend: JWTAuthBackend,
        mock_user: MockAdminUser,
    ) -> None:
        """Test that access and refresh tokens are different."""
        connection = create_mock_connection()

        result = await jwt_backend.login(connection, mock_user)

        assert result["access_token"] != result["refresh_token"]

    @pytest.mark.asyncio
    async def test_login_tokens_contain_user_info(
        self,
        jwt_backend: JWTAuthBackend,
        mock_user: MockAdminUser,
    ) -> None:
        """Test that tokens contain correct user information."""
        import jwt

        connection = create_mock_connection()

        result = await jwt_backend.login(connection, mock_user)

        # Decode access token
        payload = jwt.decode(
            result["access_token"],
            jwt_backend.config.secret_key,
            algorithms=[jwt_backend.config.algorithm],
        )

        assert payload["sub"] == str(mock_user.id)
        assert payload["email"] == mock_user.email
        assert payload["roles"] == mock_user.roles
        assert payload["type"] == "access"


class TestJWTAuthBackendGetCurrentUser:
    """Tests for JWTAuthBackend.get_current_user method."""

    @pytest.mark.asyncio
    async def test_get_current_user_from_header(
        self,
        jwt_backend: JWTAuthBackend,
        mock_user: MockAdminUser,
    ) -> None:
        """Test getting current user from Authorization header."""
        # Generate a valid token
        token = jwt_backend._create_token(mock_user, kind="access")
        connection = create_mock_connection(headers={"Authorization": f"Bearer {token}"})

        user = await jwt_backend.get_current_user(connection)

        assert user is not None
        assert user.id == mock_user.id

    @pytest.mark.asyncio
    async def test_get_current_user_from_cookie(
        self,
        jwt_config: JWTConfig,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
        mock_user: MockAdminUser,
    ) -> None:
        """Test getting current user from cookie."""
        jwt_config.token_location = "cookie"
        backend = JWTAuthBackend(config=jwt_config, user_loader=user_loader)

        token = backend._create_token(mock_user, kind="access")
        connection = create_mock_connection(cookies={"admin_access_token": token})

        user = await backend.get_current_user(connection)

        assert user is not None
        assert user.id == mock_user.id

    @pytest.mark.asyncio
    async def test_get_current_user_returns_none_for_no_token(
        self,
        jwt_backend: JWTAuthBackend,
    ) -> None:
        """Test get_current_user returns None when no token present."""
        connection = create_mock_connection()

        user = await jwt_backend.get_current_user(connection)

        assert user is None

    @pytest.mark.asyncio
    async def test_get_current_user_returns_none_for_invalid_token(
        self,
        jwt_backend: JWTAuthBackend,
    ) -> None:
        """Test get_current_user returns None for invalid token."""
        connection = create_mock_connection(headers={"Authorization": "Bearer invalid.token.here"})

        user = await jwt_backend.get_current_user(connection)

        assert user is None

    @pytest.mark.asyncio
    async def test_get_current_user_returns_none_for_expired_token(
        self,
        jwt_config: JWTConfig,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
        mock_user: MockAdminUser,
    ) -> None:
        """Test get_current_user returns None for expired token."""
        import jwt

        # Create an expired token manually
        now = datetime.datetime.now(tz=datetime.UTC)
        payload = {
            "sub": str(mock_user.id),
            "email": mock_user.email,
            "roles": mock_user.roles,
            "permissions": mock_user.permissions,
            "type": "access",
            "iat": now - datetime.timedelta(hours=2),
            "exp": now - datetime.timedelta(hours=1),
        }
        expired_token = jwt.encode(payload, jwt_config.secret_key, algorithm=jwt_config.algorithm)

        backend = JWTAuthBackend(config=jwt_config, user_loader=user_loader)
        connection = create_mock_connection(headers={"Authorization": f"Bearer {expired_token}"})

        user = await backend.get_current_user(connection)

        assert user is None

    @pytest.mark.asyncio
    async def test_get_current_user_rejects_refresh_token(
        self,
        jwt_backend: JWTAuthBackend,
        mock_user: MockAdminUser,
    ) -> None:
        """Test that refresh tokens cannot be used for authentication."""
        # Generate a refresh token
        refresh_token = jwt_backend._create_token(mock_user, kind="refresh")
        connection = create_mock_connection(headers={"Authorization": f"Bearer {refresh_token}"})

        user = await jwt_backend.get_current_user(connection)

        assert user is None


class TestJWTAuthBackendLogout:
    """Tests for JWTAuthBackend.logout method."""

    @pytest.mark.asyncio
    async def test_logout_is_noop(
        self,
        jwt_backend: JWTAuthBackend,
    ) -> None:
        """Test logout is a no-op for stateless JWT."""
        connection = create_mock_connection()

        # Should not raise
        result = await jwt_backend.logout(connection)

        assert result is None


class TestJWTAuthBackendRefresh:
    """Tests for JWTAuthBackend.refresh method."""

    @pytest.mark.asyncio
    async def test_refresh_returns_new_access_token(
        self,
        jwt_backend: JWTAuthBackend,
        mock_user: MockAdminUser,
    ) -> None:
        """Test refresh returns new access token."""
        refresh_token = jwt_backend._create_token(mock_user, kind="refresh")
        connection = create_mock_connection(headers={"X-Refresh-Token": refresh_token})

        result = await jwt_backend.refresh(connection)

        assert result is not None
        assert "access_token" in result
        assert result["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_refresh_returns_none_for_no_token(
        self,
        jwt_backend: JWTAuthBackend,
    ) -> None:
        """Test refresh returns None when no token present."""
        connection = create_mock_connection()

        result = await jwt_backend.refresh(connection)

        assert result is None

    @pytest.mark.asyncio
    async def test_refresh_returns_none_for_access_token(
        self,
        jwt_backend: JWTAuthBackend,
        mock_user: MockAdminUser,
    ) -> None:
        """Test refresh returns None when given access token instead of refresh."""
        access_token = jwt_backend._create_token(mock_user, kind="access")
        connection = create_mock_connection(headers={"X-Refresh-Token": access_token})

        result = await jwt_backend.refresh(connection)

        assert result is None


class TestJWTAuthBackendTokenCreation:
    """Tests for JWTAuthBackend token creation and decoding."""

    def test_create_access_token(
        self,
        jwt_backend: JWTAuthBackend,
        mock_user: MockAdminUser,
    ) -> None:
        """Test creating an access token."""
        import jwt

        token = jwt_backend._create_token(mock_user, kind="access")

        payload = jwt.decode(
            token,
            jwt_backend.config.secret_key,
            algorithms=[jwt_backend.config.algorithm],
        )

        assert payload["type"] == "access"
        assert payload["sub"] == str(mock_user.id)

    def test_create_refresh_token(
        self,
        jwt_backend: JWTAuthBackend,
        mock_user: MockAdminUser,
    ) -> None:
        """Test creating a refresh token."""
        import jwt

        token = jwt_backend._create_token(mock_user, kind="refresh")

        payload = jwt.decode(
            token,
            jwt_backend.config.secret_key,
            algorithms=[jwt_backend.config.algorithm],
        )

        assert payload["type"] == "refresh"

    def test_create_token_with_issuer_and_audience(
        self,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
        mock_user: MockAdminUser,
    ) -> None:
        """Test token creation includes issuer and audience when configured."""
        import jwt

        config = JWTConfig(
            secret_key="test-secret",
            issuer="my-app",
            audience="my-audience",
        )
        backend = JWTAuthBackend(config=config, user_loader=user_loader)

        token = backend._create_token(mock_user, kind="access")

        payload = jwt.decode(
            token,
            config.secret_key,
            algorithms=[config.algorithm],
            audience="my-audience",
        )

        assert payload["iss"] == "my-app"
        assert payload["aud"] == "my-audience"

    def test_decode_valid_token(
        self,
        jwt_backend: JWTAuthBackend,
        mock_user: MockAdminUser,
    ) -> None:
        """Test decoding a valid token."""
        token = jwt_backend._create_token(mock_user, kind="access")

        payload = jwt_backend._decode_token(token)

        assert payload is not None
        assert payload["sub"] == str(mock_user.id)

    def test_decode_invalid_token(
        self,
        jwt_backend: JWTAuthBackend,
    ) -> None:
        """Test decoding an invalid token returns None."""
        payload = jwt_backend._decode_token("invalid.token.here")

        assert payload is None

    def test_decode_token_with_wrong_secret(
        self,
        jwt_backend: JWTAuthBackend,
        mock_user: MockAdminUser,
    ) -> None:
        """Test decoding a token signed with different secret returns None."""
        import jwt

        # Create token with different secret
        token = jwt.encode(
            {"sub": str(mock_user.id), "type": "access"},
            "different-secret",
            algorithm="HS256",
        )

        payload = jwt_backend._decode_token(token)

        assert payload is None


class TestJWTAuthBackendTokenExtraction:
    """Tests for JWTAuthBackend token extraction methods."""

    def test_extract_token_from_header(
        self,
        jwt_backend: JWTAuthBackend,
    ) -> None:
        """Test extracting token from Authorization header."""
        connection = create_mock_connection(headers={"Authorization": "Bearer my-token"})

        token = jwt_backend._extract_token(connection)

        assert token == "my-token"

    def test_extract_token_from_cookie(
        self,
        jwt_config: JWTConfig,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
    ) -> None:
        """Test extracting token from cookie."""
        jwt_config.token_location = "cookie"
        backend = JWTAuthBackend(config=jwt_config, user_loader=user_loader)

        connection = create_mock_connection(cookies={"admin_access_token": "cookie-token"})

        token = backend._extract_token(connection)

        assert token == "cookie-token"

    def test_extract_token_fallback_to_cookie_when_header_empty(
        self,
        jwt_backend: JWTAuthBackend,
    ) -> None:
        """Test falling back to cookie when header is empty."""
        connection = create_mock_connection(cookies={"admin_access_token": "cookie-token"})

        token = jwt_backend._extract_token(connection)

        assert token == "cookie-token"

    def test_extract_token_returns_none_when_not_found(
        self,
        jwt_backend: JWTAuthBackend,
    ) -> None:
        """Test extracting token returns None when not found."""
        connection = create_mock_connection()

        token = jwt_backend._extract_token(connection)

        assert token is None

    def test_extract_refresh_token_from_header(
        self,
        jwt_backend: JWTAuthBackend,
    ) -> None:
        """Test extracting refresh token from X-Refresh-Token header."""
        connection = create_mock_connection(headers={"X-Refresh-Token": "refresh-token"})

        token = jwt_backend._extract_refresh_token(connection)

        assert token == "refresh-token"

    def test_extract_refresh_token_from_cookie(
        self,
        jwt_backend: JWTAuthBackend,
    ) -> None:
        """Test extracting refresh token from cookie."""
        connection = create_mock_connection(cookies={"admin_refresh_token": "refresh-cookie-token"})

        token = jwt_backend._extract_refresh_token(connection)

        assert token == "refresh-cookie-token"
