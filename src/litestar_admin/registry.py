"""ModelRegistry for managing registered model views."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from litestar_admin.views import BaseModelView

__all__ = ["ModelRegistry"]


class ModelRegistry:
    """Registry for storing and managing model views.

    The registry maintains a mapping of model classes and names to their
    corresponding view classes, enabling lookup and management of admin views.

    Example:
        ```python
        from litestar_admin import ModelRegistry, ModelView

        registry = ModelRegistry()

        class UserAdmin(ModelView, model=User):
            column_list = ["id", "email"]

        registry.register(UserAdmin)
        view = registry.get_view(User)
        ```
    """

    __slots__ = ("_views_by_model", "_views_by_name")

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._views_by_model: dict[type[Any], type[BaseModelView]] = {}
        self._views_by_name: dict[str, type[BaseModelView]] = {}

    def register(self, view_class: type[BaseModelView]) -> None:
        """Register a model view class.

        Args:
            view_class: The model view class to register.

        Raises:
            ValueError: If the model is already registered.
        """
        model = view_class.model
        name = view_class.name

        if model in self._views_by_model:
            msg = f"Model {model.__name__} is already registered"
            raise ValueError(msg)

        if name in self._views_by_name:
            msg = f"View name '{name}' is already registered"
            raise ValueError(msg)

        self._views_by_model[model] = view_class
        self._views_by_name[name] = view_class

    def unregister(self, model_or_name: type[Any] | str) -> None:
        """Unregister a model view.

        Args:
            model_or_name: The model class or view name to unregister.

        Raises:
            KeyError: If the model or name is not registered.
        """
        if isinstance(model_or_name, str):
            if model_or_name not in self._views_by_name:
                msg = f"View '{model_or_name}' is not registered"
                raise KeyError(msg)
            view_class = self._views_by_name.pop(model_or_name)
            del self._views_by_model[view_class.model]
        else:
            if model_or_name not in self._views_by_model:
                msg = f"Model {model_or_name.__name__} is not registered"
                raise KeyError(msg)
            view_class = self._views_by_model.pop(model_or_name)
            del self._views_by_name[view_class.name]

    def get_view(self, model: type[Any]) -> type[BaseModelView]:
        """Get the view class for a model.

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

    def get_view_by_name(self, name: str) -> type[BaseModelView]:
        """Get the view class by name.

        Args:
            name: The view name to look up.

        Returns:
            The registered view class with the given name.

        Raises:
            KeyError: If the name is not registered.
        """
        if name not in self._views_by_name:
            msg = f"View '{name}' is not registered"
            raise KeyError(msg)
        return self._views_by_name[name]

    def has_model(self, model: type[Any]) -> bool:
        """Check if a model is registered.

        Args:
            model: The model class to check.

        Returns:
            True if the model is registered, False otherwise.
        """
        return model in self._views_by_model

    def has_model_by_name(self, name: str) -> bool:
        """Check if a view name is registered.

        Args:
            name: The view name to check.

        Returns:
            True if the name is registered, False otherwise.
        """
        return name in self._views_by_name

    def list_models(self) -> list[dict[str, Any]]:
        """List all registered models with metadata.

        Returns:
            List of dictionaries containing model metadata.
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
            for view_class in self._views_by_name.values()
        ]

    def __len__(self) -> int:
        """Return the number of registered views."""
        return len(self._views_by_model)

    def __iter__(self) -> Iterator[type[BaseModelView]]:
        """Iterate over registered view classes."""
        return iter(self._views_by_name.values())
