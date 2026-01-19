"""EmbedView class for embedding external content and custom components."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Literal

from litestar_admin.views.admin_view import BaseAdminView

if TYPE_CHECKING:
    from litestar.connection import ASGIConnection

__all__ = ["EmbedView"]


class EmbedView(BaseAdminView):
    """View for embedding external dashboards, iframes, or custom React components.

    EmbedView enables integration of external tools and custom components
    into the admin panel. Use cases include:

    - Embedding external dashboards (Grafana, Metabase, Kibana)
    - Custom React components for specialized functionality
    - Interactive widgets and visualizations
    - Third-party tools in sandboxed iframes

    Attributes:
        embed_type: Type of embed - "iframe" for external URLs, "component"
            for registered React components.
        embed_url: URL to embed when embed_type is "iframe".
        component_name: Name of the registered React component when
            embed_type is "component".
        width: CSS width value (default "100%").
        height: CSS height value (default "100%").
        min_height: CSS min-height value (default "400px").
        layout: Layout mode - "full" for full-page, "sidebar" for sidebar panel,
            "card" for card within dashboard.
        sandbox: Iframe sandbox attributes (only for iframe embed_type).
        allow: Iframe allow attributes for permissions (only for iframe embed_type).
        loading: Iframe loading strategy - "eager" or "lazy".
        referrer_policy: Iframe referrer policy.
        props: Static props to pass to embedded component.
        refresh_interval: Auto-refresh interval in seconds (0 = disabled).
        show_toolbar: Whether to show a toolbar with refresh/fullscreen buttons.

    Example::

        from litestar_admin import EmbedView


        class GrafanaEmbed(EmbedView):
            name = "Metrics"
            icon = "chart-line"
            category = "Monitoring"
            embed_type = "iframe"
            embed_url = "https://grafana.example.com/d/abc123"
            height = "800px"
            sandbox = "allow-scripts allow-same-origin"


        class ActivityWidget(EmbedView):
            name = "Activity Feed"
            icon = "activity"
            embed_type = "component"
            component_name = "ActivityFeed"
            layout = "sidebar"

            async def get_props(self, connection: ASGIConnection) -> dict[str, Any]:
                user = connection.user
                return {
                    "userId": user.id if user else None,
                    "limit": 20,
                    "showTimestamps": True,
                }
    """

    # View type discriminator
    view_type: ClassVar[Literal["model", "custom", "action", "page", "link", "embed"]] = "embed"

    # Embed configuration
    embed_type: ClassVar[Literal["iframe", "component"]] = "iframe"
    embed_url: ClassVar[str] = ""
    component_name: ClassVar[str] = ""

    # Dimension configuration
    width: ClassVar[str] = "100%"
    height: ClassVar[str] = "100%"
    min_height: ClassVar[str] = "400px"
    layout: ClassVar[Literal["full", "sidebar", "card"]] = "full"

    # Iframe-specific security and behavior
    sandbox: ClassVar[str] = "allow-scripts allow-same-origin allow-forms allow-popups"
    allow: ClassVar[str] = ""  # e.g., "fullscreen; clipboard-write"
    loading: ClassVar[Literal["eager", "lazy"]] = "lazy"
    referrer_policy: ClassVar[str] = "strict-origin-when-cross-origin"

    # Component props (static)
    props: ClassVar[dict[str, Any]] = {}

    # Behavior configuration
    refresh_interval: ClassVar[int] = 0  # Seconds, 0 = disabled
    show_toolbar: ClassVar[bool] = True

    @classmethod
    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Initialize subclass with validation.

        Args:
            **kwargs: Additional keyword arguments.

        Raises:
            ValueError: If embed_type is "iframe" but no embed_url is set,
                or if embed_type is "component" but no component_name is set.
        """
        # Reset identity before calling parent __init_subclass__ so it gets
        # recalculated from the class name for each concrete subclass
        if "identity" not in cls.__dict__:
            cls.identity = ""

        super().__init_subclass__(**kwargs)

        # Validate configuration for non-abstract classes
        if cls.__name__ not in ("EmbedView",):
            if cls.embed_type == "iframe" and not cls.embed_url:
                msg = f"{cls.__name__}: embed_type='iframe' requires embed_url to be set"
                raise ValueError(msg)
            if cls.embed_type == "component" and not cls.component_name:
                msg = f"{cls.__name__}: embed_type='component' requires component_name to be set"
                raise ValueError(msg)

    async def get_props(self, connection: ASGIConnection) -> dict[str, Any]:  # noqa: ARG002
        """Get dynamic props to pass to the embedded component.

        Override this method to provide dynamic props based on the current
        request context, user, or other runtime information.

        Args:
            connection: The current ASGI connection.

        Returns:
            Dictionary of props to pass to the component.

        Example::

            async def get_props(self, connection: ASGIConnection) -> dict[str, Any]:
                return {
                    "userId": connection.user.id,
                    "theme": connection.user.preferences.get("theme", "dark"),
                    "locale": connection.headers.get("Accept-Language", "en"),
                }
        """
        return self.props.copy()

    async def get_embed_url(self, connection: ASGIConnection) -> str:  # noqa: ARG002
        """Get the URL to embed dynamically.

        Override this method to construct dynamic URLs based on the current
        request context, such as adding authentication tokens or user-specific
        parameters.

        Args:
            connection: The current ASGI connection.

        Returns:
            The URL to embed in the iframe.

        Example::

            async def get_embed_url(self, connection: ASGIConnection) -> str:
                base_url = self.embed_url
                user_id = connection.user.id
                return f"{base_url}?user={user_id}&theme=dark"
        """
        return self.embed_url

    @classmethod
    def get_api_routes(cls) -> list[dict[str, Any]]:
        """Return API route definitions for this embed view.

        Embed views expose endpoints for:
        - Getting embed configuration and props
        - Optionally, a data endpoint for component-specific data

        Returns:
            List of route definitions for embed operations.
        """
        base_path = f"/api/embeds/{cls.identity}"
        return [
            {
                "path": base_path,
                "methods": ["GET"],
                "operation": "config",
                "name": f"{cls.identity}-embed-config",
            },
            {
                "path": f"{base_path}/props",
                "methods": ["GET"],
                "operation": "props",
                "name": f"{cls.identity}-embed-props",
            },
        ]

    @classmethod
    def get_navigation_info(cls) -> dict[str, Any]:
        """Return navigation metadata including embed-specific information.

        Returns:
            Dictionary with navigation and embed configuration.
        """
        info = super().get_navigation_info()
        info.update(
            {
                "embed_type": cls.embed_type,
                "layout": cls.layout,
            }
        )
        return info

    def get_embed_config(self) -> dict[str, Any]:
        """Get the complete embed configuration for frontend rendering.

        Returns:
            Dictionary with all embed configuration needed by the frontend.
        """
        config: dict[str, Any] = {
            "type": self.embed_type,
            "width": self.width,
            "height": self.height,
            "min_height": self.min_height,
            "layout": self.layout,
            "refresh_interval": self.refresh_interval,
            "show_toolbar": self.show_toolbar,
        }

        if self.embed_type == "iframe":
            config.update(
                {
                    "url": self.embed_url,
                    "sandbox": self.sandbox,
                    "allow": self.allow,
                    "loading": self.loading,
                    "referrer_policy": self.referrer_policy,
                }
            )
        else:  # component
            config.update(
                {
                    "component_name": self.component_name,
                    "props": self.props,
                }
            )

        return config

    async def get_full_config(self, connection: ASGIConnection) -> dict[str, Any]:
        """Get complete configuration including dynamic values.

        This method resolves all dynamic values (props, URL) and returns
        the complete configuration ready for frontend consumption.

        Args:
            connection: The current ASGI connection.

        Returns:
            Complete embed configuration with resolved dynamic values.
        """
        config = self.get_embed_config()

        if self.embed_type == "iframe":
            config["url"] = await self.get_embed_url(connection)
        else:
            config["props"] = await self.get_props(connection)

        return config
