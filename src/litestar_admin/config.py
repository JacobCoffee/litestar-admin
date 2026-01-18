"""AdminConfig dataclass for configuring the admin panel."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

# NOTE: These imports must be at runtime (not TYPE_CHECKING) for msgspec
# type resolution to work correctly when this dataclass is used as a
# dependency parameter type in Litestar controllers.
from litestar_admin.auth import AuthBackend  # noqa: TC001
from litestar_admin.views import BaseModelView  # noqa: TC001

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
        views: List of model views to register.
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
    """

    # Basic settings
    title: str = "Admin"
    base_url: str = "/admin"
    logo_url: str | None = None
    favicon_url: str | None = None
    theme: Literal["dark", "light"] = "dark"

    # Authentication
    auth_backend: AuthBackend | None = None

    # Model views
    views: list[type[BaseModelView]] = field(default_factory=list)
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

    @property
    def api_base_url(self) -> str:
        """Return the API base URL."""
        return f"{self.base_url}/api"

    @property
    def static_base_url(self) -> str:
        """Return the static files base URL."""
        return f"{self.base_url}/static"
