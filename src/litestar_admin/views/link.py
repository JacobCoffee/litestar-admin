"""LinkView for external navigation links in the admin sidebar."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Literal

from litestar_admin.views.admin_view import BaseAdminView

if TYPE_CHECKING:
    from litestar.connection import ASGIConnection

__all__ = ["LinkView"]


class LinkView(BaseAdminView):
    """View class for external navigation links in the admin sidebar.

    LinkView provides a simple way to add external links to the admin navigation
    without any associated API routes. Use this for documentation links, related
    admin panels, external services, or API documentation.

    Attributes:
        url: The destination URL for the link. Can be absolute or relative.
        target: The link target attribute ("_blank" for new tab, "_self" for same tab).
        view_type: Always "link" for LinkView instances.

    Example::

        from litestar_admin.views import LinkView


        class DocsLink(LinkView):
            name = "Documentation"
            icon = "book"
            url = "https://docs.example.com"
            target = "_blank"


        class APIDocsLink(LinkView):
            name = "API Docs"
            icon = "code"
            category = "Developer"
            url = "/api/docs"
            target = "_self"


        # Dynamic URL example
        class DynamicDocsLink(LinkView):
            name = "API Reference"
            icon = "external-link"

            def get_url(self) -> str:
                # Dynamic URL based on configuration or context
                return f"{settings.API_BASE_URL}/docs"

    Note:
        LinkView does not register any API routes. It only provides navigation
        metadata for the frontend sidebar.
    """

    # Link-specific attributes
    url: ClassVar[str] = ""
    target: ClassVar[Literal["_blank", "_self"]] = "_blank"

    # Override view_type for links
    view_type: ClassVar[Literal["link"]] = "link"  # type: ignore[assignment]

    @classmethod
    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Initialize subclass with proper identity generation.

        Ensures each LinkView subclass gets its own identity derived from
        its name, rather than inheriting 'link' from the parent class.

        Args:
            **kwargs: Additional keyword arguments passed to parent.
        """
        # Reset identity before calling super().__init_subclass__
        # This ensures the base class logic generates identity from name
        if "identity" not in cls.__dict__:
            cls.identity = ""

        super().__init_subclass__(**kwargs)

        # Set sensible plural for link views
        if "name_plural" not in cls.__dict__ and cls.__name__ != "LinkView":
            cls.name_plural = cls.name  # Links don't need pluralization

    @classmethod
    def get_api_routes(cls) -> list[dict[str, Any]]:
        """Return empty route list since links don't have API endpoints.

        LinkView is navigation-only and does not register any API routes.
        The frontend handles link navigation directly.

        Returns:
            Empty list (no routes for link views).
        """
        return []

    def get_url(self) -> str:
        """Return the destination URL for this link.

        Override this method to provide dynamic URLs based on configuration,
        environment, or other runtime factors.

        Returns:
            The URL string for the link destination.

        Example::

            class EnvironmentDocs(LinkView):
                name = "Environment Docs"

                def get_url(self) -> str:
                    if settings.ENV == "production":
                        return "https://docs.prod.example.com"
                    return "https://docs.dev.example.com"
        """
        return self.url

    @classmethod
    def get_navigation_info(cls) -> dict[str, Any]:
        """Return navigation metadata including link-specific information.

        Extends the base navigation info with URL and target attributes
        needed for rendering external links in the sidebar.

        Returns:
            Dictionary with navigation information including:
                - name: Display name
                - name_plural: Plural display name
                - identity: URL-safe identifier
                - icon: Icon name
                - category: Category name (optional)
                - order: Sort order
                - view_type: "link"
                - is_visible: Whether to show in navigation
                - url: Link destination URL
                - target: Link target ("_blank" or "_self")
        """
        info = super().get_navigation_info()
        info.update(
            {
                "url": cls.url,
                "target": cls.target,
            }
        )
        return info

    @classmethod
    async def is_accessible(cls, connection: ASGIConnection) -> bool:  # noqa: ARG003
        """Check if the current user can see this link in navigation.

        Override this method to conditionally show/hide links based on
        user permissions or other criteria.

        Args:
            connection: The current ASGI connection.

        Returns:
            True if the link should be visible, False otherwise.

        Example::

            @classmethod
            async def is_accessible(cls, connection: ASGIConnection) -> bool:
                # Only show admin docs to staff users
                user = connection.user
                return user.is_authenticated and user.is_staff
        """
        return cls.can_access
