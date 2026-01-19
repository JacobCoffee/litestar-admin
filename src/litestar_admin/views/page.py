"""PageView class for static and dynamic admin pages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Literal

from litestar_admin.views.admin_view import BaseAdminView

if TYPE_CHECKING:
    from litestar.connection import ASGIConnection

__all__ = ["PageView"]


class PageView(BaseAdminView):
    """Base class for custom content pages in the admin panel.

    PageView is designed for non-model content pages such as:
    - About/help pages with markdown content
    - Analytics dashboards with dynamic data
    - Settings pages with custom forms
    - Documentation pages
    - Custom reports and visualizations

    Attributes:
        content: Static content string (markdown, HTML, or plain text).
        content_type: Type of content ("markdown", "html", "text", "dynamic", "template").
        template: Template name for template-based rendering.
        template_context: Static context to pass to templates.
        layout: Page layout type ("default", "full-width", "sidebar").
        refresh_interval: Auto-refresh interval in seconds (0 = no refresh).

    Example::

        from litestar_admin import PageView


        class AboutPage(PageView):
            name = "About"
            icon = "info-circle"
            content_type = "markdown"
            content = '''
            # About This Admin

            This is the admin panel for MyApp.

            ## Features
            - User management
            - Content editing
            - Analytics dashboard
            '''


        class AnalyticsPage(PageView):
            name = "Analytics"
            icon = "chart-bar"
            content_type = "dynamic"
            refresh_interval = 60  # Refresh every minute

            async def get_content(self) -> dict[str, Any]:
                return {
                    "type": "dashboard",
                    "widgets": [
                        {"type": "stat", "title": "Users", "value": 1234},
                        {"type": "chart", "title": "Signups", "data": [...]},
                    ],
                }
    """

    # Override view_type for page views
    view_type: ClassVar[Literal["model", "custom", "action", "page", "link", "embed"]] = "page"
    icon: ClassVar[str] = "file-alt"  # Default page icon

    # Content configuration
    content: ClassVar[str] = ""
    content_type: ClassVar[Literal["markdown", "html", "text", "dynamic", "template"]] = "markdown"

    # Template configuration
    template: ClassVar[str | None] = None
    template_context: ClassVar[dict[str, Any]] = {}

    # Layout configuration
    layout: ClassVar[Literal["default", "full-width", "sidebar"]] = "default"

    # Refresh configuration for dynamic pages
    refresh_interval: ClassVar[int] = 0  # seconds, 0 = no auto-refresh

    @classmethod
    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Initialize subclass with proper identity generation.

        Ensures each PageView subclass gets its own identity derived from
        its name, rather than inheriting 'page' from the parent class.

        Args:
            **kwargs: Additional keyword arguments passed to parent.
        """
        # Reset identity before calling super().__init_subclass__
        # This ensures the base class logic generates identity from name
        if "identity" not in cls.__dict__:
            cls.identity = ""

        super().__init_subclass__(**kwargs)

        # Set sensible plural for page views
        if "name_plural" not in cls.__dict__ and cls.__name__ != "PageView":
            cls.name_plural = cls.name  # Pages don't need pluralization

    async def get_content(self) -> dict[str, Any]:
        """Get dynamic content for the page.

        Override this method to provide dynamic content. The returned
        dictionary is passed to the frontend for rendering.

        For dashboard-type pages, return widget configurations.
        For data pages, return the data to display.

        Returns:
            Dictionary with content data for the frontend.

        Example::

            async def get_content(self) -> dict[str, Any]:
                users_count = await User.count()
                return {
                    "type": "dashboard",
                    "widgets": [
                        {
                            "type": "stat",
                            "title": "Total Users",
                            "value": users_count,
                            "icon": "users",
                        },
                    ],
                }
        """
        return {}

    async def get_template_context(self, connection: ASGIConnection) -> dict[str, Any]:  # noqa: ARG002
        """Get context for template rendering.

        Override this method to provide dynamic template context.
        The base implementation returns the static template_context.

        Args:
            connection: The current ASGI connection.

        Returns:
            Dictionary of template context variables.

        Example::

            async def get_template_context(self, connection: ASGIConnection) -> dict[str, Any]:
                context = await super().get_template_context(connection)
                context["current_user"] = connection.user
                context["settings"] = await Settings.get_current()
                return context
        """
        return self.template_context.copy()

    @classmethod
    def get_page_metadata(cls) -> dict[str, Any]:
        """Get metadata for page rendering.

        Returns:
            Dictionary with page configuration for the frontend.
        """
        metadata: dict[str, Any] = {
            "name": cls.name,
            "identity": cls.identity,
            "icon": cls.icon,
            "content_type": cls.content_type,
            "layout": cls.layout,
            "refresh_interval": cls.refresh_interval,
        }

        # Include static content for non-dynamic pages
        if cls.content_type in ("markdown", "html", "text"):
            metadata["content"] = cls.content

        # Include template info for template-based pages
        if cls.content_type == "template" and cls.template:
            metadata["template"] = cls.template

        return metadata

    @classmethod
    def get_navigation_info(cls) -> dict[str, Any]:
        """Return navigation metadata for the sidebar.

        Extends the base navigation info with page-specific metadata.

        Returns:
            Dictionary with navigation information.
        """
        info = super().get_navigation_info()
        info["content_type"] = cls.content_type
        info["layout"] = cls.layout
        return info

    @classmethod
    def get_api_routes(cls) -> list[dict[str, Any]]:
        """Return API route definitions for this page view.

        Page views expose endpoints for metadata and dynamic content.
        Static content pages only need the metadata endpoint.
        Dynamic content pages also get a content endpoint.

        Returns:
            List of route definitions for page operations.
        """
        base_path = f"/api/pages/{cls.identity}"
        routes: list[dict[str, Any]] = [
            {
                "path": base_path,
                "methods": ["GET"],
                "operation": "metadata",
                "name": f"{cls.identity}-metadata",
            },
        ]

        # Dynamic pages get an additional content endpoint
        if cls.content_type == "dynamic":
            routes.append(
                {
                    "path": f"{base_path}/content",
                    "methods": ["GET"],
                    "operation": "content",
                    "name": f"{cls.identity}-content",
                }
            )

        # Template pages get a render endpoint
        if cls.content_type == "template":
            routes.append(
                {
                    "path": f"{base_path}/render",
                    "methods": ["GET"],
                    "operation": "render",
                    "name": f"{cls.identity}-render",
                }
            )

        return routes
