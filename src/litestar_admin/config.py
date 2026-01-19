"""AdminConfig dataclass for configuring the admin panel."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

# NOTE: These imports must be at runtime (not TYPE_CHECKING) for msgspec
# type resolution to work correctly when this dataclass is used as a
# dependency parameter type in Litestar controllers.
from litestar_admin.auth import AuthBackend  # noqa: TC001
from litestar_admin.logging import LoggingConfig  # noqa: TC001
from litestar_admin.views import (  # noqa: TC001
    ActionView,
    BaseAdminView,
    BaseModelView,
    CustomView,
    EmbedView,
    LinkView,
    PageView,
)

__all__ = ["AdminConfig"]


@dataclass
class AdminConfig:
    """Configuration for the admin panel.

    Attributes:
        title: The title displayed in the admin panel header.
        base_url: The base URL path for the admin panel (default: "/admin").
        logo_url: Optional URL for a custom logo image.
        favicon_url: Optional URL for a custom favicon.
        theme: The theme to use ("dark" or "light", default: "dark").
        auth_backend: Optional authentication backend for securing the admin.
        views: List of all view types to register (accepts any BaseAdminView subclass).
        model_views: Convenience field for registering model views (merged with views).
        custom_views: Convenience field for registering custom views (merged with views).
        action_views: Convenience field for registering action views (merged with views).
        page_views: Convenience field for registering page views (merged with views).
        link_views: Convenience field for registering link views (merged with views).
        embed_views: Convenience field for registering embed views (merged with views).
        auto_discover: Whether to auto-discover SQLAlchemy models (default: True).
        debug: Whether to enable debug mode (default: False).
        rate_limit_enabled: Whether to enable rate limiting (default: True).
        rate_limit_requests: Maximum requests per window (default: 100).
        rate_limit_window_seconds: Rate limit window in seconds (default: 60).
        static_path: Path to static files directory.
        index_title: Title for the index/dashboard page.
        session_cookie_name: Name of the session cookie.
        session_cookie_httponly: Whether session cookie is HTTP only.
        session_cookie_secure: Whether session cookie requires HTTPS.
        session_cookie_samesite: SameSite policy for session cookie.
        logging_config: Optional logging configuration for structlog integration.
        storage: Optional storage configuration for file uploads.

    Example::

        from litestar_admin import AdminConfig, AdminPlugin
        from litestar_admin.views import (
            ActionView,
            CustomView,
            EmbedView,
            LinkView,
            ModelView,
            PageView,
        )

        # Option 1: Use the unified 'views' field for all view types
        config = AdminConfig(
            title="My Admin",
            views=[UserAdmin, ProductAdmin, ClearCacheAction, DocsLink],
        )

        # Option 2: Use categorized fields for better organization
        config = AdminConfig(
            title="My Admin",
            model_views=[UserAdmin, ProductAdmin],
            action_views=[ClearCacheAction, SendNotificationsAction],
            page_views=[AboutPage, HelpPage],
            link_views=[DocsLink, APIDocsLink],
            embed_views=[GrafanaEmbed, MetricsWidget],
        )

        # Option 3: Mix both approaches
        config = AdminConfig(
            title="My Admin",
            views=[UserAdmin, ProductAdmin],  # Mixed views
            action_views=[ClearCacheAction],  # Categorized by type
        )
    """

    # Basic settings
    title: str = "Admin"
    base_url: str = "/admin"
    logo_url: str | None = None
    favicon_url: str | None = None
    theme: Literal["dark", "light"] = "dark"

    # Authentication
    auth_backend: AuthBackend | None = None

    # OAuth providers (for displaying OAuth login buttons alongside password login)
    # Each entry should be a dict with: name, display_name, login_url
    oauth_providers: list[dict[str, str]] = field(default_factory=list)

    # All views (accepts any BaseAdminView subclass)
    views: list[type[BaseAdminView]] = field(default_factory=list)

    # Categorized view registration (convenience fields, merged with views)
    model_views: list[type[BaseModelView]] = field(default_factory=list)
    custom_views: list[type[CustomView]] = field(default_factory=list)
    action_views: list[type[ActionView]] = field(default_factory=list)
    page_views: list[type[PageView]] = field(default_factory=list)
    link_views: list[type[LinkView]] = field(default_factory=list)
    embed_views: list[type[EmbedView]] = field(default_factory=list)

    # Auto-discovery
    auto_discover: bool = True

    # Development
    debug: bool = False

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # Static files
    static_path: str | None = None

    # UI customization
    index_title: str = "Dashboard"

    # Session settings
    session_cookie_name: str = "admin_session"
    session_cookie_httponly: bool = True
    session_cookie_secure: bool = True
    session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    # Logging configuration
    logging_config: LoggingConfig | None = None

    # File storage configuration (StorageConfig from litestar_admin.contrib.storages)
    # Use Any type to avoid import errors when litestar-storages is not installed
    storage: Any | None = None

    # Password policy settings
    password_min_length: int = 8
    password_reset_enabled: bool = False
    password_reset_token_expiry: int = 3600  # seconds (1 hour)

    # Additional settings
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if not self.base_url.startswith("/"):
            msg = "base_url must start with '/'"
            raise ValueError(msg)

        if self.base_url.endswith("/") and self.base_url != "/":
            self.base_url = self.base_url.rstrip("/")

        if self.rate_limit_requests < 1:
            msg = "rate_limit_requests must be at least 1"
            raise ValueError(msg)

        if self.rate_limit_window_seconds < 1:
            msg = "rate_limit_window_seconds must be at least 1"
            raise ValueError(msg)

    def get_all_views(self) -> list[type[BaseAdminView]]:
        """Get all registered views from all fields combined.

        Combines views from the main `views` field with all categorized view
        fields (model_views, custom_views, action_views, page_views, link_views,
        embed_views). Duplicates are preserved to allow detection during validation.

        Returns:
            Combined list of all view classes in registration order.

        Example::

            config = AdminConfig(
                views=[UserAdmin],
                model_views=[ProductAdmin],
                action_views=[ClearCacheAction],
            )
            all_views = config.get_all_views()
            # Returns [UserAdmin, ProductAdmin, ClearCacheAction]
        """
        return [
            *self.views,
            *self.model_views,
            *self.custom_views,
            *self.action_views,
            *self.page_views,
            *self.link_views,
            *self.embed_views,
        ]

    @property
    def api_base_url(self) -> str:
        """Return the API base URL."""
        return f"{self.base_url}/api"

    @property
    def static_base_url(self) -> str:
        """Return the static files base URL."""
        return f"{self.base_url}/static"
