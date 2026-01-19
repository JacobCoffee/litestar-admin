"""Abstract base class for all admin views."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar, Literal

if TYPE_CHECKING:
    from litestar.connection import ASGIConnection

__all__ = ["BaseAdminView"]


class BaseAdminView(ABC):
    """Abstract base class for all admin views (both model and non-model based).

    This is the root class in the admin view hierarchy. All view types
    (ModelView, CustomView, ActionView, PageView, LinkView, EmbedView)
    inherit from this class.

    Attributes:
        name: Display name for the view.
        name_plural: Plural display name.
        identity: URL-safe unique identifier for routing.
        icon: Icon name for the sidebar (e.g., FontAwesome icon).
        category: Category name for grouping views in sidebar.
        order: Sort order within category (lower numbers appear first).
        is_visible: Whether this view appears in navigation.
        view_type: Discriminator for view type (model, custom, action, page, link, embed).
        can_access: Whether access is allowed by default.
        required_permission: Optional permission string required for access.
        required_role: Optional role string required for access.

    Example::

        from litestar_admin import BaseAdminView


        class MyCustomView(BaseAdminView):
            name = "Dashboard"
            icon = "dashboard"
            view_type = "page"

            @classmethod
            def get_api_routes(cls) -> list[dict[str, Any]]:
                return [
                    {
                        "path": "/dashboard",
                        "methods": ["GET"],
                        "handler": get_dashboard_data,
                    }
                ]
    """

    # View identification
    name: ClassVar[str] = ""
    name_plural: ClassVar[str] = ""
    identity: ClassVar[str] = ""  # URL-safe unique identifier

    # Navigation & display
    icon: ClassVar[str] = "file"  # Default icon
    category: ClassVar[str | None] = None
    order: ClassVar[int] = 0  # Sort order within category
    is_visible: ClassVar[bool] = True  # Show in navigation

    # View type discriminator
    view_type: ClassVar[Literal["model", "custom", "action", "page", "link", "embed"]] = "custom"

    # Access control
    can_access: ClassVar[bool] = True
    required_permission: ClassVar[str | None] = None
    required_role: ClassVar[str | None] = None

    @classmethod
    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Initialize subclass with sensible defaults.

        Args:
            **kwargs: Additional keyword arguments.
        """
        super().__init_subclass__(**kwargs)

        # Set name from class name if not specified
        if not cls.name and cls.__name__ not in ("BaseAdminView", "BaseModelView", "ModelView"):
            cls.name = cls.__name__.replace("View", "").replace("Admin", "")

        # Set identity from name
        if not cls.identity:
            cls.identity = cls.name.lower().replace(" ", "-")

        # Set plural name
        if not cls.name_plural:
            cls.name_plural = f"{cls.name}s"

    @classmethod
    @abstractmethod
    def get_api_routes(cls) -> list[dict[str, Any]]:
        """Return API route definitions for this view.

        Model views return CRUD routes, action views return action endpoint,
        page views return data endpoint, etc.

        Returns:
            List of route definition dictionaries with keys:
                - path: The route path
                - methods: List of HTTP methods
                - handler: The handler function/controller
                - name: Optional route name
                - guards: Optional list of guards

        Example::

            @classmethod
            def get_api_routes(cls) -> list[dict[str, Any]]:
                return [
                    {
                        "path": f"/api/{cls.identity}",
                        "methods": ["GET", "POST"],
                        "handler": MyController,
                    }
                ]
        """
        ...

    @classmethod
    async def is_accessible(cls, connection: ASGIConnection) -> bool:  # noqa: ARG003
        """Check if the current user can access this view.

        Override this method to implement custom access control logic.
        The default implementation checks the can_access class variable.

        Args:
            connection: The current ASGI connection.

        Returns:
            True if accessible, False otherwise.

        Example::

            @classmethod
            async def is_accessible(cls, connection: ASGIConnection) -> bool:
                user = connection.user
                return user.is_authenticated and user.has_permission("admin.view")
        """
        return cls.can_access

    @classmethod
    def get_navigation_info(cls) -> dict[str, Any]:
        """Return navigation metadata for the sidebar.

        Returns:
            Dictionary with navigation information:
                - name: Display name
                - name_plural: Plural display name
                - identity: URL-safe identifier
                - icon: Icon name
                - category: Category name (optional)
                - order: Sort order
                - view_type: View type discriminator
                - is_visible: Whether to show in navigation
        """
        return {
            "name": cls.name,
            "name_plural": cls.name_plural,
            "identity": cls.identity,
            "icon": cls.icon,
            "category": cls.category,
            "order": cls.order,
            "view_type": cls.view_type,
            "is_visible": cls.is_visible,
        }
