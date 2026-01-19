"""ViewRegistry for managing all types of admin views."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from litestar_admin.views import BaseAdminView, BaseModelView

__all__ = ["ViewRegistry", "ModelRegistry"]


class ViewRegistry:
    """Registry for storing and managing all admin view types.

    The registry maintains a mapping of view identities to their corresponding
    view classes, supporting both model-based views (ModelView) and non-model
    views (CustomView, ActionView, PageView, LinkView, EmbedView).

    Example::

        from litestar_admin import ViewRegistry, ModelView, ActionView

        registry = ViewRegistry()


        class UserAdmin(ModelView, model=User):
            column_list = ["id", "email"]


        class ClearCacheAction(ActionView):
            name = "Clear Cache"


        registry.register(UserAdmin)
        registry.register(ClearCacheAction)

        # Filter by type
        models = registry.list_model_views()
        actions = registry.list_action_views()

        # Get navigation grouped by category
        nav = registry.get_navigation()
    """

    __slots__ = ("_views_by_identity", "_views_by_model")

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._views_by_identity: dict[str, type[BaseAdminView]] = {}
        # Keep model mapping for backward compatibility with get_view(model) API
        self._views_by_model: dict[type[Any], type[BaseModelView]] = {}

    def register(self, view_class: type[BaseAdminView]) -> None:
        """Register an admin view class.

        Accepts any BaseAdminView subclass, including ModelView, CustomView,
        ActionView, PageView, LinkView, and EmbedView.

        Args:
            view_class: The admin view class to register.

        Raises:
            ValueError: If the view identity is already registered, or if a
                model-based view has a model that's already registered.
        """
        identity = view_class.identity

        if identity in self._views_by_identity:
            msg = f"View identity '{identity}' is already registered"
            raise ValueError(msg)

        # Store by identity (all view types)
        self._views_by_identity[identity] = view_class

        # For model views, also store by model for backward compatibility
        if hasattr(view_class, "model") and view_class.model is not None:
            from litestar_admin.views import BaseModelView

            if not isinstance(view_class, type) or not issubclass(view_class, BaseModelView):
                return

            model = view_class.model
            if model in self._views_by_model:
                msg = f"Model {model.__name__} is already registered"
                raise ValueError(msg)

            self._views_by_model[model] = view_class

    def unregister(self, model_or_identity: type[Any] | str) -> None:
        """Unregister an admin view.

        Args:
            model_or_identity: The model class (for model views) or view identity to unregister.

        Raises:
            KeyError: If the model or identity is not registered.
        """
        if isinstance(model_or_identity, str):
            # Unregister by identity (try lowercase for backward compatibility)
            identity = model_or_identity.lower()
            if identity not in self._views_by_identity:
                msg = f"View '{model_or_identity}' is not registered"
                raise KeyError(msg)
            view_class = self._views_by_identity.pop(identity)

            # Also remove from model mapping if it's a model view
            if hasattr(view_class, "model") and view_class.model in self._views_by_model:
                del self._views_by_model[view_class.model]
        else:
            # Unregister by model (backward compatibility for model views)
            if model_or_identity not in self._views_by_model:
                msg = f"Model {model_or_identity.__name__} is not registered"
                raise KeyError(msg)
            view_class = self._views_by_model.pop(model_or_identity)
            del self._views_by_identity[view_class.identity]

    def get_view(self, model: type[Any]) -> type[BaseModelView]:
        """Get the view class for a model.

        Backward-compatible method for retrieving model views by model class.

        Args:
            model: The model class to look up.

        Returns:
            The registered view class for the model.

        Raises:
            KeyError: If the model is not registered.
        """
        if model not in self._views_by_model:
            msg = f"Model {model.__name__} is not registered"
            raise KeyError(msg)
        return self._views_by_model[model]

    def get_view_by_name(self, name: str) -> type[BaseAdminView]:
        """Get the view class by identity (URL-safe name).

        Works with all view types, not just model views.
        For backward compatibility, lookups are case-insensitive.

        Args:
            name: The view identity to look up (case-insensitive).

        Returns:
            The registered view class with the given identity.

        Raises:
            KeyError: If the identity is not registered.
        """
        # Try lowercase for backward compatibility
        identity = name.lower()
        if identity not in self._views_by_identity:
            msg = f"View '{name}' is not registered"
            raise KeyError(msg)
        return self._views_by_identity[identity]

    def has_view(self, identity: str) -> bool:
        """Check if a view identity is registered.

        For backward compatibility, checks are case-insensitive.

        Args:
            identity: The view identity to check (case-insensitive).

        Returns:
            True if the identity is registered, False otherwise.
        """
        return identity.lower() in self._views_by_identity

    def has_model(self, model: type[Any]) -> bool:
        """Check if a model is registered.

        Backward-compatible method for checking model view registration.

        Args:
            model: The model class to check.

        Returns:
            True if the model is registered, False otherwise.
        """
        return model in self._views_by_model

    def has_model_by_name(self, name: str) -> bool:
        """Check if a view identity is registered.

        Backward-compatible alias for has_view(). Checks are case-insensitive.

        Args:
            name: The view identity to check (case-insensitive).

        Returns:
            True if the identity is registered, False otherwise.
        """
        return name.lower() in self._views_by_identity

    def list_views(self) -> list[type[BaseAdminView]]:
        """List all registered views.

        Returns:
            List of all registered view classes.
        """
        return list(self._views_by_identity.values())

    def list_model_views(self) -> list[type[BaseModelView]]:
        """List only model-based views.

        Returns:
            List of ModelView/BaseModelView classes.
        """
        return [view for view in self._views_by_identity.values() if view.view_type == "model"]

    def list_custom_views(self) -> list[type[BaseAdminView]]:
        """List only custom (non-model) data views.

        Returns:
            List of CustomView classes.
        """
        return [view for view in self._views_by_identity.values() if view.view_type == "custom"]

    def list_action_views(self) -> list[type[BaseAdminView]]:
        """List only action views.

        Returns:
            List of ActionView classes.
        """
        return [view for view in self._views_by_identity.values() if view.view_type == "action"]

    def list_page_views(self) -> list[type[BaseAdminView]]:
        """List only page views.

        Returns:
            List of PageView classes.
        """
        return [view for view in self._views_by_identity.values() if view.view_type == "page"]

    def list_link_views(self) -> list[type[BaseAdminView]]:
        """List only link views.

        Returns:
            List of LinkView classes.
        """
        return [view for view in self._views_by_identity.values() if view.view_type == "link"]

    def list_embed_views(self) -> list[type[BaseAdminView]]:
        """List only embed views.

        Returns:
            List of EmbedView classes.
        """
        return [view for view in self._views_by_identity.values() if view.view_type == "embed"]

    def list_models(self) -> list[dict[str, Any]]:
        """List all registered model views with metadata.

        Backward-compatible method that returns only model views.

        Returns:
            List of dictionaries containing model view metadata.
        """
        return [
            {
                "name": view_class.name,
                "model": view_class.model.__name__,
                "icon": view_class.icon,
                "category": view_class.category,
                "can_create": view_class.can_create,
                "can_edit": view_class.can_edit,
                "can_delete": view_class.can_delete,
                "can_view_details": view_class.can_view_details,
            }
            for view_class in self._views_by_identity.values()
            if view_class.view_type == "model"
        ]

    def get_navigation(self) -> dict[str, list[dict[str, Any]]]:
        """Get navigation structure grouped by category.

        Returns navigation items grouped by their category, with uncategorized
        views in the "default" category. Only includes views where is_visible=True.

        Returns:
            Dictionary mapping category names to lists of navigation items.
            Each navigation item is a dictionary with view metadata from
            get_navigation_info().

        Example::

            {
                "default": [
                    {"name": "Users", "identity": "user", "icon": "users", ...},
                    {"name": "Posts", "identity": "post", "icon": "file", ...},
                ],
                "Maintenance": [
                    {"name": "Clear Cache", "identity": "clear-cache", "icon": "trash", ...},
                ],
                "External": [
                    {"name": "Documentation", "identity": "docs", "icon": "book", "url": "...", ...},
                ],
            }
        """
        navigation: dict[str, list[dict[str, Any]]] = {}

        for view_class in self._views_by_identity.values():
            # Skip invisible views
            if not view_class.is_visible:
                continue

            nav_info = view_class.get_navigation_info()
            category = nav_info.get("category") or "default"

            if category not in navigation:
                navigation[category] = []

            navigation[category].append(nav_info)

        # Sort items within each category by order attribute
        for items in navigation.values():
            items.sort(key=lambda x: (x.get("order", 0), x.get("name", "")))

        return navigation

    def __len__(self) -> int:
        """Return the number of registered views."""
        return len(self._views_by_identity)

    def __iter__(self) -> Iterator[type[BaseAdminView]]:
        """Iterate over registered view classes."""
        return iter(self._views_by_identity.values())


# Backward compatibility alias
ModelRegistry = ViewRegistry
