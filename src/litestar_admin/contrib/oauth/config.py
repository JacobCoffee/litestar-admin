"""OAuth configuration for litestar-admin.

This module provides configuration classes for OAuth authentication
integration with litestar-oauth library.

Example:
    Basic usage with GitHub provider:

    >>> from litestar_admin.contrib.oauth import OAuthConfig, OAuthProviderConfig
    >>>
    >>> config = OAuthConfig(
    ...     providers=[
    ...         OAuthProviderConfig(
    ...             name="github",
    ...             client_id="your-client-id",
    ...             client_secret="your-client-secret",
    ...         )
    ...     ],
    ...     redirect_base_url="https://example.com",
    ... )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "OAuthConfig",
    "OAuthProviderConfig",
    "OAuthProviderType",
]


class OAuthProviderType(str, Enum):
    """Supported OAuth provider types.

    These correspond to the built-in providers in litestar-oauth.

    Attributes:
        GITHUB: GitHub OAuth provider.
        GOOGLE: Google OAuth provider.
        DISCORD: Discord OAuth provider.
        GENERIC: Generic OAuth2/OIDC provider for custom providers.
    """

    GITHUB = "github"
    GOOGLE = "google"
    DISCORD = "discord"
    GENERIC = "generic"


@dataclass
class OAuthProviderConfig:
    """Configuration for a single OAuth provider.

    This dataclass holds configuration for one OAuth provider. It supports
    both built-in providers (GitHub, Google, Discord) and generic OAuth2/OIDC
    providers.

    Attributes:
        name: Unique name for this provider (used in URLs and identification).
        client_id: OAuth client ID from the provider.
        client_secret: OAuth client secret from the provider.
        provider_type: Type of OAuth provider. Defaults to GENERIC.
        scopes: List of OAuth scopes to request. If None, uses provider defaults.
        authorize_url: Authorization URL (required for GENERIC providers).
        token_url: Token endpoint URL (required for GENERIC providers).
        userinfo_url: User info endpoint URL (required for GENERIC providers).
        extra_params: Additional parameters to include in authorization request.

    Example:
        GitHub provider:

        >>> config = OAuthProviderConfig(
        ...     name="github",
        ...     client_id="your-client-id",
        ...     client_secret="your-client-secret",
        ...     provider_type=OAuthProviderType.GITHUB,
        ... )

        Generic provider (Keycloak):

        >>> config = OAuthProviderConfig(
        ...     name="keycloak",
        ...     client_id="your-client-id",
        ...     client_secret="your-client-secret",
        ...     provider_type=OAuthProviderType.GENERIC,
        ...     authorize_url="https://keycloak.example.com/auth/realms/myrealm/protocol/openid-connect/auth",
        ...     token_url="https://keycloak.example.com/auth/realms/myrealm/protocol/openid-connect/token",
        ...     userinfo_url="https://keycloak.example.com/auth/realms/myrealm/protocol/openid-connect/userinfo",
        ... )
    """

    name: str
    client_id: str
    client_secret: str
    provider_type: OAuthProviderType = OAuthProviderType.GENERIC
    scopes: list[str] | None = None
    authorize_url: str | None = None
    token_url: str | None = None
    userinfo_url: str | None = None
    extra_params: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if not self.name:
            msg = "Provider name is required"
            raise ValueError(msg)

        if not self.client_id:
            msg = f"client_id is required for provider '{self.name}'"
            raise ValueError(msg)

        if not self.client_secret:
            msg = f"client_secret is required for provider '{self.name}'"
            raise ValueError(msg)

        # Generic providers require URL configuration
        if self.provider_type == OAuthProviderType.GENERIC:
            if not self.authorize_url:
                msg = f"authorize_url is required for generic provider '{self.name}'"
                raise ValueError(msg)
            if not self.token_url:
                msg = f"token_url is required for generic provider '{self.name}'"
                raise ValueError(msg)
            if not self.userinfo_url:
                msg = f"userinfo_url is required for generic provider '{self.name}'"
                raise ValueError(msg)


@dataclass
class OAuthConfig:
    """Configuration for OAuth authentication in litestar-admin.

    This dataclass holds all configuration options for OAuth authentication,
    including multiple provider configurations and shared settings.

    Attributes:
        providers: List of OAuth provider configurations.
        redirect_base_url: Base URL for OAuth callbacks. Must be publicly accessible.
        callback_path: Path template for OAuth callbacks. Defaults to "/admin/auth/oauth/{provider}/callback".
        login_path: Path template for OAuth login. Defaults to "/admin/auth/oauth/{provider}/login".
        session_cookie_name: Name of the session cookie. Defaults to "admin_oauth_session".
        session_expiry: Session expiry time in seconds. Defaults to 86400 (24 hours).
        auto_create_user: Whether to automatically create users on first OAuth login. Defaults to True.
        allowed_domains: Optional list of allowed email domains. None allows all domains.
        default_roles: Default roles assigned to new OAuth users. Defaults to empty list.
        default_permissions: Default permissions assigned to new OAuth users. Defaults to empty list.

    Example:
        >>> config = OAuthConfig(
        ...     providers=[
        ...         OAuthProviderConfig(
        ...             name="github",
        ...             client_id="your-client-id",
        ...             client_secret="your-client-secret",
        ...             provider_type=OAuthProviderType.GITHUB,
        ...         ),
        ...         OAuthProviderConfig(
        ...             name="google",
        ...             client_id="your-client-id",
        ...             client_secret="your-client-secret",
        ...             provider_type=OAuthProviderType.GOOGLE,
        ...         ),
        ...     ],
        ...     redirect_base_url="https://example.com",
        ...     allowed_domains=["example.com"],
        ...     default_roles=["user"],
        ... )
    """

    providers: Sequence[OAuthProviderConfig]
    redirect_base_url: str
    callback_path: str = "/admin/auth/oauth/{provider}/callback"
    login_path: str = "/admin/auth/oauth/{provider}/login"
    session_cookie_name: str = "admin_oauth_session"
    session_expiry: int = 86400  # 24 hours in seconds
    auto_create_user: bool = True
    allowed_domains: list[str] | None = None
    default_roles: list[str] = field(default_factory=list)
    default_permissions: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if not self.providers:
            msg = "At least one OAuth provider must be configured"
            raise ValueError(msg)

        if not self.redirect_base_url:
            msg = "redirect_base_url is required"
            raise ValueError(msg)

        # Normalize base URL (remove trailing slash)
        if self.redirect_base_url.endswith("/"):
            object.__setattr__(self, "redirect_base_url", self.redirect_base_url.rstrip("/"))

        if self.session_expiry < 1:
            msg = "session_expiry must be at least 1 second"
            raise ValueError(msg)

        # Validate all providers have unique names
        provider_names = [p.name for p in self.providers]
        if len(provider_names) != len(set(provider_names)):
            msg = "All OAuth providers must have unique names"
            raise ValueError(msg)

    def get_provider(self, name: str) -> OAuthProviderConfig | None:
        """Get a provider configuration by name.

        Args:
            name: The provider name to look up.

        Returns:
            The provider configuration, or None if not found.
        """
        for provider in self.providers:
            if provider.name == name:
                return provider
        return None

    def get_callback_url(self, provider_name: str) -> str:
        """Get the full callback URL for a provider.

        Args:
            provider_name: The name of the OAuth provider.

        Returns:
            The full callback URL including base URL and path.
        """
        path = self.callback_path.format(provider=provider_name)
        return f"{self.redirect_base_url}{path}"

    def get_login_url(self, provider_name: str) -> str:
        """Get the full login URL for a provider.

        Args:
            provider_name: The name of the OAuth provider.

        Returns:
            The full login URL including base URL and path.
        """
        path = self.login_path.format(provider=provider_name)
        return f"{self.redirect_base_url}{path}"

    def to_provider_kwargs(self, provider_config: OAuthProviderConfig) -> dict[str, Any]:
        """Convert a provider config to kwargs for litestar-oauth provider.

        Args:
            provider_config: The provider configuration to convert.

        Returns:
            Dictionary of kwargs for the litestar-oauth provider constructor.
        """
        kwargs: dict[str, Any] = {
            "client_id": provider_config.client_id,
            "client_secret": provider_config.client_secret,
            "redirect_uri": self.get_callback_url(provider_config.name),
        }

        if provider_config.scopes:
            kwargs["scopes"] = provider_config.scopes

        # For generic providers, include URL configuration
        if provider_config.provider_type == OAuthProviderType.GENERIC:
            kwargs["authorize_url"] = provider_config.authorize_url
            kwargs["token_url"] = provider_config.token_url
            kwargs["userinfo_url"] = provider_config.userinfo_url

        if provider_config.extra_params:
            kwargs["extra_params"] = provider_config.extra_params

        return kwargs
