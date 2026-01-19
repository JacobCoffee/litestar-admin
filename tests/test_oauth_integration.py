"""Tests for OAuth authentication integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from litestar_admin.contrib.oauth import (
    OAuthAuthBackend,
    OAuthConfig,
    OAuthProviderConfig,
    OAuthProviderType,
    OAuthTokens,
    OAuthUserInfo,
)

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
def github_provider_config() -> OAuthProviderConfig:
    """Return a GitHub provider configuration."""
    return OAuthProviderConfig(
        name="github",
        client_id="test-github-client-id",
        client_secret="test-github-client-secret",
        provider_type=OAuthProviderType.GITHUB,
    )


@pytest.fixture
def google_provider_config() -> OAuthProviderConfig:
    """Return a Google provider configuration."""
    return OAuthProviderConfig(
        name="google",
        client_id="test-google-client-id",
        client_secret="test-google-client-secret",
        provider_type=OAuthProviderType.GOOGLE,
        scopes=["openid", "email", "profile"],
    )


@pytest.fixture
def generic_provider_config() -> OAuthProviderConfig:
    """Return a generic OAuth provider configuration."""
    return OAuthProviderConfig(
        name="keycloak",
        client_id="test-keycloak-client-id",
        client_secret="test-keycloak-client-secret",
        provider_type=OAuthProviderType.GENERIC,
        authorize_url="https://keycloak.example.com/auth/authorize",
        token_url="https://keycloak.example.com/auth/token",
        userinfo_url="https://keycloak.example.com/auth/userinfo",
    )


@pytest.fixture
def oauth_config(github_provider_config: OAuthProviderConfig) -> OAuthConfig:
    """Return a basic OAuth config with GitHub provider."""
    return OAuthConfig(
        providers=[github_provider_config],
        redirect_base_url="https://example.com",
    )


@pytest.fixture
def multi_provider_config(
    github_provider_config: OAuthProviderConfig,
    google_provider_config: OAuthProviderConfig,
) -> OAuthConfig:
    """Return an OAuth config with multiple providers."""
    return OAuthConfig(
        providers=[github_provider_config, google_provider_config],
        redirect_base_url="https://example.com",
        allowed_domains=["example.com"],
        default_roles=["user"],
    )


@pytest.fixture
def user_loader(mock_user: MockAdminUser) -> Callable[[str | int], Awaitable[MockAdminUser | None]]:
    """Return a mock user loader function."""

    async def loader(user_id: str | int) -> MockAdminUser | None:
        if str(user_id) == str(mock_user.id):
            return mock_user
        return None

    return loader


@pytest.fixture
def user_loader_by_email(mock_user: MockAdminUser) -> Callable[[str], Awaitable[MockAdminUser | None]]:
    """Return a mock user loader by email function."""

    async def loader(email: str) -> MockAdminUser | None:
        if email == mock_user.email:
            return mock_user
        return None

    return loader


@pytest.fixture
def user_creator(mock_user: MockAdminUser) -> Callable[[OAuthUserInfo], Awaitable[MockAdminUser]]:
    """Return a mock user creator function."""

    async def creator(user_info: OAuthUserInfo) -> MockAdminUser:
        return MockAdminUser(
            id=2,
            email=user_info.email,
            roles=["user"],
            permissions=[],
        )

    return creator


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
    state_mock = MagicMock()
    if state_attrs:
        for key, value in state_attrs.items():
            setattr(state_mock, key, value)
    else:
        del state_mock.refresh_token
    connection.state = state_mock
    return connection


# ==============================================================================
# OAuthProviderConfig Tests
# ==============================================================================


class TestOAuthProviderConfig:
    """Tests for OAuthProviderConfig dataclass."""

    def test_basic_provider_config(self) -> None:
        """Test basic provider configuration."""
        config = OAuthProviderConfig(
            name="github",
            client_id="test-id",
            client_secret="test-secret",
            provider_type=OAuthProviderType.GITHUB,
        )

        assert config.name == "github"
        assert config.client_id == "test-id"
        assert config.client_secret == "test-secret"
        assert config.provider_type == OAuthProviderType.GITHUB
        assert config.scopes is None

    def test_provider_config_with_scopes(self) -> None:
        """Test provider configuration with custom scopes."""
        config = OAuthProviderConfig(
            name="google",
            client_id="test-id",
            client_secret="test-secret",
            provider_type=OAuthProviderType.GOOGLE,
            scopes=["openid", "email"],
        )

        assert config.scopes == ["openid", "email"]

    def test_generic_provider_requires_urls(self) -> None:
        """Test that generic providers require URL configuration."""
        with pytest.raises(ValueError, match="authorize_url is required"):
            OAuthProviderConfig(
                name="custom",
                client_id="test-id",
                client_secret="test-secret",
                provider_type=OAuthProviderType.GENERIC,
            )

    def test_generic_provider_requires_token_url(self) -> None:
        """Test that generic providers require token_url."""
        with pytest.raises(ValueError, match="token_url is required"):
            OAuthProviderConfig(
                name="custom",
                client_id="test-id",
                client_secret="test-secret",
                provider_type=OAuthProviderType.GENERIC,
                authorize_url="https://example.com/auth",
            )

    def test_generic_provider_requires_userinfo_url(self) -> None:
        """Test that generic providers require userinfo_url."""
        with pytest.raises(ValueError, match="userinfo_url is required"):
            OAuthProviderConfig(
                name="custom",
                client_id="test-id",
                client_secret="test-secret",
                provider_type=OAuthProviderType.GENERIC,
                authorize_url="https://example.com/auth",
                token_url="https://example.com/token",
            )

    def test_generic_provider_with_all_urls(self) -> None:
        """Test generic provider with all required URLs."""
        config = OAuthProviderConfig(
            name="custom",
            client_id="test-id",
            client_secret="test-secret",
            provider_type=OAuthProviderType.GENERIC,
            authorize_url="https://example.com/auth",
            token_url="https://example.com/token",
            userinfo_url="https://example.com/userinfo",
        )

        assert config.authorize_url == "https://example.com/auth"
        assert config.token_url == "https://example.com/token"
        assert config.userinfo_url == "https://example.com/userinfo"

    def test_empty_name_raises_error(self) -> None:
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match="Provider name is required"):
            OAuthProviderConfig(
                name="",
                client_id="test-id",
                client_secret="test-secret",
            )

    def test_empty_client_id_raises_error(self) -> None:
        """Test that empty client_id raises ValueError."""
        with pytest.raises(ValueError, match="client_id is required"):
            OAuthProviderConfig(
                name="github",
                client_id="",
                client_secret="test-secret",
            )

    def test_empty_client_secret_raises_error(self) -> None:
        """Test that empty client_secret raises ValueError."""
        with pytest.raises(ValueError, match="client_secret is required"):
            OAuthProviderConfig(
                name="github",
                client_id="test-id",
                client_secret="",
            )


# ==============================================================================
# OAuthConfig Tests
# ==============================================================================


class TestOAuthConfig:
    """Tests for OAuthConfig dataclass."""

    def test_basic_config(self, github_provider_config: OAuthProviderConfig) -> None:
        """Test basic OAuth configuration."""
        config = OAuthConfig(
            providers=[github_provider_config],
            redirect_base_url="https://example.com",
        )

        assert len(config.providers) == 1
        assert config.redirect_base_url == "https://example.com"
        assert config.session_expiry == 86400
        assert config.auto_create_user is True

    def test_config_normalizes_base_url(self, github_provider_config: OAuthProviderConfig) -> None:
        """Test that trailing slashes are removed from base URL."""
        config = OAuthConfig(
            providers=[github_provider_config],
            redirect_base_url="https://example.com/",
        )

        assert config.redirect_base_url == "https://example.com"

    def test_empty_providers_raises_error(self) -> None:
        """Test that empty providers list raises ValueError."""
        with pytest.raises(ValueError, match="At least one OAuth provider must be configured"):
            OAuthConfig(
                providers=[],
                redirect_base_url="https://example.com",
            )

    def test_empty_redirect_base_url_raises_error(self, github_provider_config: OAuthProviderConfig) -> None:
        """Test that empty redirect_base_url raises ValueError."""
        with pytest.raises(ValueError, match="redirect_base_url is required"):
            OAuthConfig(
                providers=[github_provider_config],
                redirect_base_url="",
            )

    def test_duplicate_provider_names_raises_error(self) -> None:
        """Test that duplicate provider names raise ValueError."""
        with pytest.raises(ValueError, match="All OAuth providers must have unique names"):
            OAuthConfig(
                providers=[
                    OAuthProviderConfig(
                        name="github",
                        client_id="id1",
                        client_secret="secret1",
                        provider_type=OAuthProviderType.GITHUB,
                    ),
                    OAuthProviderConfig(
                        name="github",
                        client_id="id2",
                        client_secret="secret2",
                        provider_type=OAuthProviderType.GITHUB,
                    ),
                ],
                redirect_base_url="https://example.com",
            )

    def test_invalid_session_expiry_raises_error(self, github_provider_config: OAuthProviderConfig) -> None:
        """Test that session_expiry less than 1 raises ValueError."""
        with pytest.raises(ValueError, match="session_expiry must be at least 1 second"):
            OAuthConfig(
                providers=[github_provider_config],
                redirect_base_url="https://example.com",
                session_expiry=0,
            )

    def test_get_provider(self, multi_provider_config: OAuthConfig) -> None:
        """Test getting a provider by name."""
        github = multi_provider_config.get_provider("github")
        google = multi_provider_config.get_provider("google")
        unknown = multi_provider_config.get_provider("unknown")

        assert github is not None
        assert github.name == "github"
        assert google is not None
        assert google.name == "google"
        assert unknown is None

    def test_get_callback_url(self, oauth_config: OAuthConfig) -> None:
        """Test generating callback URLs."""
        callback_url = oauth_config.get_callback_url("github")

        assert callback_url == "https://example.com/admin/auth/oauth/github/callback"

    def test_get_login_url(self, oauth_config: OAuthConfig) -> None:
        """Test generating login URLs."""
        login_url = oauth_config.get_login_url("github")

        assert login_url == "https://example.com/admin/auth/oauth/github/login"

    def test_to_provider_kwargs(self, oauth_config: OAuthConfig) -> None:
        """Test converting provider config to kwargs."""
        provider = oauth_config.providers[0]
        kwargs = oauth_config.to_provider_kwargs(provider)

        assert kwargs["client_id"] == "test-github-client-id"
        assert kwargs["client_secret"] == "test-github-client-secret"
        assert "redirect_uri" in kwargs

    def test_to_provider_kwargs_with_scopes(self, google_provider_config: OAuthProviderConfig) -> None:
        """Test converting provider config with scopes."""
        config = OAuthConfig(
            providers=[google_provider_config],
            redirect_base_url="https://example.com",
        )
        kwargs = config.to_provider_kwargs(google_provider_config)

        assert kwargs["scopes"] == ["openid", "email", "profile"]

    def test_to_provider_kwargs_generic(self, generic_provider_config: OAuthProviderConfig) -> None:
        """Test converting generic provider config."""
        config = OAuthConfig(
            providers=[generic_provider_config],
            redirect_base_url="https://example.com",
        )
        kwargs = config.to_provider_kwargs(generic_provider_config)

        assert kwargs["authorize_url"] == "https://keycloak.example.com/auth/authorize"
        assert kwargs["token_url"] == "https://keycloak.example.com/auth/token"
        assert kwargs["userinfo_url"] == "https://keycloak.example.com/auth/userinfo"


# ==============================================================================
# OAuthUserInfo Tests
# ==============================================================================


class TestOAuthUserInfo:
    """Tests for OAuthUserInfo dataclass."""

    def test_basic_user_info(self) -> None:
        """Test basic user info creation."""
        user_info = OAuthUserInfo(
            id="12345",
            email="user@example.com",
            name="Test User",
            provider="github",
        )

        assert user_info.id == "12345"
        assert user_info.email == "user@example.com"
        assert user_info.name == "Test User"
        assert user_info.provider == "github"
        assert user_info.picture is None
        assert user_info.raw_data is None

    def test_user_info_with_all_fields(self) -> None:
        """Test user info with all fields populated."""
        raw_data = {"login": "testuser", "company": "Test Corp"}
        user_info = OAuthUserInfo(
            id="12345",
            email="user@example.com",
            name="Test User",
            picture="https://example.com/avatar.jpg",
            provider="github",
            raw_data=raw_data,
        )

        assert user_info.picture == "https://example.com/avatar.jpg"
        assert user_info.raw_data == raw_data


# ==============================================================================
# OAuthTokens Tests
# ==============================================================================


class TestOAuthTokens:
    """Tests for OAuthTokens dataclass."""

    def test_basic_tokens(self) -> None:
        """Test basic token creation."""
        tokens = OAuthTokens(access_token="test-access-token")

        assert tokens.access_token == "test-access-token"
        assert tokens.token_type == "Bearer"
        assert tokens.refresh_token is None
        assert tokens.expires_in is None

    def test_tokens_with_all_fields(self) -> None:
        """Test tokens with all fields populated."""
        tokens = OAuthTokens(
            access_token="test-access-token",
            token_type="Bearer",
            refresh_token="test-refresh-token",
            expires_in=3600,
            scope="read:user",
            id_token="test-id-token",
        )

        assert tokens.refresh_token == "test-refresh-token"
        assert tokens.expires_in == 3600
        assert tokens.scope == "read:user"
        assert tokens.id_token == "test-id-token"


# ==============================================================================
# OAuthAuthBackend Tests
# ==============================================================================


class TestOAuthAuthBackend:
    """Tests for OAuthAuthBackend class."""

    def test_initialization(
        self,
        oauth_config: OAuthConfig,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
        user_loader_by_email: Callable[[str], Awaitable[MockAdminUser | None]],
    ) -> None:
        """Test backend initialization."""
        backend = OAuthAuthBackend(
            config=oauth_config,
            user_loader=user_loader,
            user_loader_by_email=user_loader_by_email,
        )

        assert backend.config is oauth_config
        assert backend.user_loader is user_loader
        assert backend.user_loader_by_email is user_loader_by_email
        assert backend.user_creator is None

    def test_initialization_with_user_creator(
        self,
        oauth_config: OAuthConfig,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
        user_loader_by_email: Callable[[str], Awaitable[MockAdminUser | None]],
        user_creator: Callable[[OAuthUserInfo], Awaitable[MockAdminUser]],
    ) -> None:
        """Test backend initialization with user creator."""
        backend = OAuthAuthBackend(
            config=oauth_config,
            user_loader=user_loader,
            user_loader_by_email=user_loader_by_email,
            user_creator=user_creator,
        )

        assert backend.user_creator is user_creator

    def test_available_providers(
        self,
        multi_provider_config: OAuthConfig,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
        user_loader_by_email: Callable[[str], Awaitable[MockAdminUser | None]],
    ) -> None:
        """Test listing available providers."""
        backend = OAuthAuthBackend(
            config=multi_provider_config,
            user_loader=user_loader,
            user_loader_by_email=user_loader_by_email,
        )

        assert backend.available_providers == ["github", "google"]


class TestOAuthAuthBackendLogin:
    """Tests for OAuthAuthBackend.login method."""

    @pytest.mark.asyncio
    async def test_login_returns_tokens(
        self,
        oauth_config: OAuthConfig,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
        user_loader_by_email: Callable[[str], Awaitable[MockAdminUser | None]],
        mock_user: MockAdminUser,
    ) -> None:
        """Test login returns access and refresh tokens."""
        backend = OAuthAuthBackend(
            config=oauth_config,
            user_loader=user_loader,
            user_loader_by_email=user_loader_by_email,
            jwt_secret_key="test-secret",
        )
        connection = create_mock_connection()

        result = await backend.login(connection, mock_user)

        assert "access_token" in result
        assert "refresh_token" in result
        assert result["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_tokens_are_different(
        self,
        oauth_config: OAuthConfig,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
        user_loader_by_email: Callable[[str], Awaitable[MockAdminUser | None]],
        mock_user: MockAdminUser,
    ) -> None:
        """Test that access and refresh tokens are different."""
        backend = OAuthAuthBackend(
            config=oauth_config,
            user_loader=user_loader,
            user_loader_by_email=user_loader_by_email,
            jwt_secret_key="test-secret",
        )
        connection = create_mock_connection()

        result = await backend.login(connection, mock_user)

        assert result["access_token"] != result["refresh_token"]


class TestOAuthAuthBackendGetCurrentUser:
    """Tests for OAuthAuthBackend.get_current_user method."""

    @pytest.mark.asyncio
    async def test_get_current_user_from_header(
        self,
        oauth_config: OAuthConfig,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
        user_loader_by_email: Callable[[str], Awaitable[MockAdminUser | None]],
        mock_user: MockAdminUser,
    ) -> None:
        """Test getting current user from Authorization header."""
        backend = OAuthAuthBackend(
            config=oauth_config,
            user_loader=user_loader,
            user_loader_by_email=user_loader_by_email,
            jwt_secret_key="test-secret",
        )

        # Generate a valid token
        token = backend._create_token(mock_user, kind="access")
        connection = create_mock_connection(headers={"Authorization": f"Bearer {token}"})

        user = await backend.get_current_user(connection)

        assert user is not None
        assert user.id == mock_user.id

    @pytest.mark.asyncio
    async def test_get_current_user_from_cookie(
        self,
        oauth_config: OAuthConfig,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
        user_loader_by_email: Callable[[str], Awaitable[MockAdminUser | None]],
        mock_user: MockAdminUser,
    ) -> None:
        """Test getting current user from session cookie."""
        backend = OAuthAuthBackend(
            config=oauth_config,
            user_loader=user_loader,
            user_loader_by_email=user_loader_by_email,
            jwt_secret_key="test-secret",
        )

        token = backend._create_token(mock_user, kind="access")
        connection = create_mock_connection(cookies={oauth_config.session_cookie_name: token})

        user = await backend.get_current_user(connection)

        assert user is not None
        assert user.id == mock_user.id

    @pytest.mark.asyncio
    async def test_get_current_user_returns_none_for_no_token(
        self,
        oauth_config: OAuthConfig,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
        user_loader_by_email: Callable[[str], Awaitable[MockAdminUser | None]],
    ) -> None:
        """Test get_current_user returns None when no token present."""
        backend = OAuthAuthBackend(
            config=oauth_config,
            user_loader=user_loader,
            user_loader_by_email=user_loader_by_email,
            jwt_secret_key="test-secret",
        )
        connection = create_mock_connection()

        user = await backend.get_current_user(connection)

        assert user is None

    @pytest.mark.asyncio
    async def test_get_current_user_returns_none_for_invalid_token(
        self,
        oauth_config: OAuthConfig,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
        user_loader_by_email: Callable[[str], Awaitable[MockAdminUser | None]],
    ) -> None:
        """Test get_current_user returns None for invalid token."""
        backend = OAuthAuthBackend(
            config=oauth_config,
            user_loader=user_loader,
            user_loader_by_email=user_loader_by_email,
            jwt_secret_key="test-secret",
        )
        connection = create_mock_connection(headers={"Authorization": "Bearer invalid.token.here"})

        user = await backend.get_current_user(connection)

        assert user is None


class TestOAuthAuthBackendRefresh:
    """Tests for OAuthAuthBackend.refresh method."""

    @pytest.mark.asyncio
    async def test_refresh_returns_new_access_token(
        self,
        oauth_config: OAuthConfig,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
        user_loader_by_email: Callable[[str], Awaitable[MockAdminUser | None]],
        mock_user: MockAdminUser,
    ) -> None:
        """Test refresh returns new access token."""
        backend = OAuthAuthBackend(
            config=oauth_config,
            user_loader=user_loader,
            user_loader_by_email=user_loader_by_email,
            jwt_secret_key="test-secret",
        )
        refresh_token = backend._create_token(mock_user, kind="refresh")
        connection = create_mock_connection(headers={"X-Refresh-Token": refresh_token})

        result = await backend.refresh(connection)

        assert result is not None
        assert "access_token" in result
        assert result["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_refresh_returns_none_for_no_token(
        self,
        oauth_config: OAuthConfig,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
        user_loader_by_email: Callable[[str], Awaitable[MockAdminUser | None]],
    ) -> None:
        """Test refresh returns None when no token present."""
        backend = OAuthAuthBackend(
            config=oauth_config,
            user_loader=user_loader,
            user_loader_by_email=user_loader_by_email,
            jwt_secret_key="test-secret",
        )
        connection = create_mock_connection()

        result = await backend.refresh(connection)

        assert result is None

    @pytest.mark.asyncio
    async def test_refresh_returns_none_for_access_token(
        self,
        oauth_config: OAuthConfig,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
        user_loader_by_email: Callable[[str], Awaitable[MockAdminUser | None]],
        mock_user: MockAdminUser,
    ) -> None:
        """Test refresh returns None when given access token instead of refresh."""
        backend = OAuthAuthBackend(
            config=oauth_config,
            user_loader=user_loader,
            user_loader_by_email=user_loader_by_email,
            jwt_secret_key="test-secret",
        )
        access_token = backend._create_token(mock_user, kind="access")
        connection = create_mock_connection(headers={"X-Refresh-Token": access_token})

        result = await backend.refresh(connection)

        assert result is None


class TestOAuthAuthBackendAuthenticate:
    """Tests for OAuthAuthBackend.authenticate method."""

    @pytest.mark.asyncio
    async def test_authenticate_returns_none_without_provider(
        self,
        oauth_config: OAuthConfig,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
        user_loader_by_email: Callable[[str], Awaitable[MockAdminUser | None]],
    ) -> None:
        """Test authenticate returns None when provider is missing."""
        backend = OAuthAuthBackend(
            config=oauth_config,
            user_loader=user_loader,
            user_loader_by_email=user_loader_by_email,
        )
        connection = create_mock_connection()

        result = await backend.authenticate(connection, {"code": "auth-code"})

        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_returns_none_without_code(
        self,
        oauth_config: OAuthConfig,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
        user_loader_by_email: Callable[[str], Awaitable[MockAdminUser | None]],
    ) -> None:
        """Test authenticate returns None when code is missing."""
        backend = OAuthAuthBackend(
            config=oauth_config,
            user_loader=user_loader,
            user_loader_by_email=user_loader_by_email,
        )
        connection = create_mock_connection()

        result = await backend.authenticate(connection, {"provider": "github"})

        assert result is None


class TestOAuthAuthBackendEmailValidation:
    """Tests for email domain validation."""

    def test_validate_email_domain_no_restrictions(
        self,
        oauth_config: OAuthConfig,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
        user_loader_by_email: Callable[[str], Awaitable[MockAdminUser | None]],
    ) -> None:
        """Test email validation with no domain restrictions."""
        backend = OAuthAuthBackend(
            config=oauth_config,
            user_loader=user_loader,
            user_loader_by_email=user_loader_by_email,
        )

        assert backend._validate_email_domain("user@any.com") is True
        assert backend._validate_email_domain("user@example.com") is True

    def test_validate_email_domain_with_restrictions(
        self,
        multi_provider_config: OAuthConfig,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
        user_loader_by_email: Callable[[str], Awaitable[MockAdminUser | None]],
    ) -> None:
        """Test email validation with domain restrictions."""
        backend = OAuthAuthBackend(
            config=multi_provider_config,
            user_loader=user_loader,
            user_loader_by_email=user_loader_by_email,
        )

        assert backend._validate_email_domain("user@example.com") is True
        assert backend._validate_email_domain("user@other.com") is False

    def test_validate_email_domain_case_insensitive(
        self,
        multi_provider_config: OAuthConfig,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
        user_loader_by_email: Callable[[str], Awaitable[MockAdminUser | None]],
    ) -> None:
        """Test email validation is case insensitive."""
        backend = OAuthAuthBackend(
            config=multi_provider_config,
            user_loader=user_loader,
            user_loader_by_email=user_loader_by_email,
        )

        assert backend._validate_email_domain("user@EXAMPLE.COM") is True
        assert backend._validate_email_domain("user@Example.Com") is True

    def test_validate_email_domain_invalid_email(
        self,
        multi_provider_config: OAuthConfig,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
        user_loader_by_email: Callable[[str], Awaitable[MockAdminUser | None]],
    ) -> None:
        """Test email validation with invalid email format."""
        backend = OAuthAuthBackend(
            config=multi_provider_config,
            user_loader=user_loader,
            user_loader_by_email=user_loader_by_email,
        )

        assert backend._validate_email_domain("") is False
        assert backend._validate_email_domain("invalid-email") is False


class TestOAuthAuthBackendUserInfoExtraction:
    """Tests for user info extraction from OAuth responses."""

    def test_extract_user_info_from_dict(
        self,
        oauth_config: OAuthConfig,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
        user_loader_by_email: Callable[[str], Awaitable[MockAdminUser | None]],
    ) -> None:
        """Test extracting user info from a dictionary response."""
        backend = OAuthAuthBackend(
            config=oauth_config,
            user_loader=user_loader,
            user_loader_by_email=user_loader_by_email,
        )

        raw_data = {
            "id": "12345",
            "email": "user@example.com",
            "name": "Test User",
            "avatar_url": "https://example.com/avatar.jpg",
        }

        user_info = backend._extract_user_info(raw_data, "github")

        assert user_info.id == "12345"
        assert user_info.email == "user@example.com"
        assert user_info.name == "Test User"
        assert user_info.picture == "https://example.com/avatar.jpg"
        assert user_info.provider == "github"

    def test_extract_user_info_from_object(
        self,
        oauth_config: OAuthConfig,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
        user_loader_by_email: Callable[[str], Awaitable[MockAdminUser | None]],
    ) -> None:
        """Test extracting user info from an object response."""
        backend = OAuthAuthBackend(
            config=oauth_config,
            user_loader=user_loader,
            user_loader_by_email=user_loader_by_email,
        )

        # Mock litestar-oauth UserInfo-like object
        mock_user_info = MagicMock()
        mock_user_info.id = "67890"
        mock_user_info.email = "test@example.com"
        mock_user_info.name = "Test Name"
        mock_user_info.picture = "https://example.com/pic.jpg"
        mock_user_info.raw_data = {"extra": "data"}

        user_info = backend._extract_user_info(mock_user_info, "google")

        assert user_info.id == "67890"
        assert user_info.email == "test@example.com"
        assert user_info.name == "Test Name"
        assert user_info.picture == "https://example.com/pic.jpg"
        assert user_info.provider == "google"


class TestOAuthAuthBackendAuthorizationUrl:
    """Tests for authorization URL generation."""

    def test_get_authorization_url(
        self,
        oauth_config: OAuthConfig,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
        user_loader_by_email: Callable[[str], Awaitable[MockAdminUser | None]],
    ) -> None:
        """Test generating authorization URL with mocked provider."""
        backend = OAuthAuthBackend(
            config=oauth_config,
            user_loader=user_loader,
            user_loader_by_email=user_loader_by_email,
        )

        # Mock the provider
        mock_provider = MagicMock()
        mock_provider.get_authorization_url.return_value = "https://github.com/login/oauth/authorize?client_id=test"
        backend._providers["github"] = mock_provider

        auth_url, state = backend.get_authorization_url("github")

        assert auth_url.startswith("https://github.com/login/oauth/authorize")
        assert state is not None
        assert len(state) > 0
        assert state in backend._state_store

    def test_get_authorization_url_unknown_provider_raises_error(
        self,
        oauth_config: OAuthConfig,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
        user_loader_by_email: Callable[[str], Awaitable[MockAdminUser | None]],
    ) -> None:
        """Test that unknown provider raises ValueError."""
        backend = OAuthAuthBackend(
            config=oauth_config,
            user_loader=user_loader,
            user_loader_by_email=user_loader_by_email,
        )

        with pytest.raises(ValueError, match="OAuth provider 'unknown' is not configured"):
            backend.get_authorization_url("unknown")


class TestOAuthAuthBackendHandleCallback:
    """Tests for OAuth callback handling."""

    @pytest.mark.asyncio
    async def test_handle_callback_success(
        self,
        oauth_config: OAuthConfig,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
        user_loader_by_email: Callable[[str], Awaitable[MockAdminUser | None]],
        mock_user: MockAdminUser,
    ) -> None:
        """Test successful callback handling."""
        backend = OAuthAuthBackend(
            config=oauth_config,
            user_loader=user_loader,
            user_loader_by_email=user_loader_by_email,
        )

        # Mock the provider
        mock_provider = MagicMock()
        mock_tokens = MagicMock()
        mock_tokens.access_token = "test-access-token"
        mock_tokens.token_type = "Bearer"
        mock_tokens.refresh_token = None
        mock_tokens.expires_in = 3600
        mock_provider.exchange_code = AsyncMock(return_value=mock_tokens)

        mock_user_info = MagicMock()
        mock_user_info.id = str(mock_user.id)
        mock_user_info.email = mock_user.email
        mock_user_info.name = "Test User"
        mock_user_info.picture = None
        mock_user_info.raw_data = {}
        mock_provider.get_user_info = AsyncMock(return_value=mock_user_info)

        backend._providers["github"] = mock_provider

        # Add state to the store
        state = "test-state-token"
        backend._state_store[state] = "github"

        user, tokens = await backend.handle_callback("github", "auth-code", state)

        assert user is not None
        assert user.id == mock_user.id
        assert tokens is not None
        assert tokens.access_token == "test-access-token"
        # State should be consumed
        assert state not in backend._state_store

    @pytest.mark.asyncio
    async def test_handle_callback_invalid_state(
        self,
        oauth_config: OAuthConfig,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
        user_loader_by_email: Callable[[str], Awaitable[MockAdminUser | None]],
    ) -> None:
        """Test callback handling with invalid state."""
        backend = OAuthAuthBackend(
            config=oauth_config,
            user_loader=user_loader,
            user_loader_by_email=user_loader_by_email,
        )

        user, tokens = await backend.handle_callback("github", "auth-code", "invalid-state")

        assert user is None
        assert tokens is None

    @pytest.mark.asyncio
    async def test_handle_callback_wrong_provider_for_state(
        self,
        oauth_config: OAuthConfig,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
        user_loader_by_email: Callable[[str], Awaitable[MockAdminUser | None]],
    ) -> None:
        """Test callback handling with state from different provider."""
        backend = OAuthAuthBackend(
            config=oauth_config,
            user_loader=user_loader,
            user_loader_by_email=user_loader_by_email,
        )

        # Add state for github
        state = "test-state-token"
        backend._state_store[state] = "github"

        # Try to use it with google
        user, tokens = await backend.handle_callback("google", "auth-code", state)

        assert user is None
        assert tokens is None

    @pytest.mark.asyncio
    async def test_handle_callback_creates_user(
        self,
        oauth_config: OAuthConfig,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
        user_creator: Callable[[OAuthUserInfo], Awaitable[MockAdminUser]],
    ) -> None:
        """Test callback creates user when not found."""

        # User loader that always returns None (user not found)
        async def no_user_loader(email: str) -> MockAdminUser | None:
            return None

        backend = OAuthAuthBackend(
            config=oauth_config,
            user_loader=user_loader,
            user_loader_by_email=no_user_loader,
            user_creator=user_creator,
        )

        # Mock the provider
        mock_provider = MagicMock()
        mock_tokens = MagicMock()
        mock_tokens.access_token = "test-access-token"
        mock_provider.exchange_code = AsyncMock(return_value=mock_tokens)

        mock_user_info = MagicMock()
        mock_user_info.id = "new-user"
        mock_user_info.email = "new@example.com"
        mock_user_info.name = "New User"
        mock_user_info.picture = None
        mock_user_info.raw_data = {}
        mock_provider.get_user_info = AsyncMock(return_value=mock_user_info)

        backend._providers["github"] = mock_provider

        user, _tokens = await backend.handle_callback("github", "auth-code")

        assert user is not None
        assert user.email == "new@example.com"
        assert user.id == 2  # From user_creator fixture

    @pytest.mark.asyncio
    async def test_handle_callback_blocked_domain(
        self,
        multi_provider_config: OAuthConfig,
        user_loader: Callable[[str | int], Awaitable[MockAdminUser | None]],
        user_loader_by_email: Callable[[str], Awaitable[MockAdminUser | None]],
    ) -> None:
        """Test callback blocks users from non-allowed domains."""
        backend = OAuthAuthBackend(
            config=multi_provider_config,
            user_loader=user_loader,
            user_loader_by_email=user_loader_by_email,
        )

        # Mock the provider
        mock_provider = MagicMock()
        mock_tokens = MagicMock()
        mock_tokens.access_token = "test-access-token"
        mock_provider.exchange_code = AsyncMock(return_value=mock_tokens)

        mock_user_info = MagicMock()
        mock_user_info.id = "blocked-user"
        mock_user_info.email = "user@blocked.com"  # Not in allowed_domains
        mock_user_info.name = "Blocked User"
        mock_user_info.picture = None
        mock_user_info.raw_data = {}
        mock_provider.get_user_info = AsyncMock(return_value=mock_user_info)

        backend._providers["github"] = mock_provider

        user, tokens = await backend.handle_callback("github", "auth-code")

        assert user is None
        assert tokens is None
