"""SQLAdmin bridge for converting sqladmin views to litestar-admin views.

This module provides utilities to migrate from sqladmin to litestar-admin,
allowing users to reuse existing sqladmin ModelView configurations.

Example:
    ```python
    from sqladmin import ModelView as SQLAdminModelView
    from litestar_admin.contrib.sqladmin import SQLAdminBridge, convert_sqladmin_view


    class UserAdmin(SQLAdminModelView, model=User):
        column_list = ["id", "email", "name"]
        column_searchable_list = ["email", "name"]
        can_delete = False


    # Convert single view
    LitestarUserAdmin = convert_sqladmin_view(UserAdmin)

    # Or use bridge for multiple views
    bridge = SQLAdminBridge()
    bridge.register(UserAdmin)
    bridge.register(PostAdmin)
    litestar_views = bridge.convert_all()
    ```
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from litestar_admin.views.base import BaseModelView

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["SQLAdminBridge", "convert_sqladmin_view"]


# Mapping of sqladmin attribute names to litestar-admin equivalents
SQLADMIN_ATTR_MAPPING: dict[str, str] = {
    # Column configuration
    "column_list": "column_list",
    "column_exclude_list": "column_exclude_list",
    "column_searchable_list": "column_searchable_list",
    "column_sortable_list": "column_sortable_list",
    "column_default_sort": "column_default_sort",
    # Form configuration
    "form_columns": "form_columns",
    "form_excluded_columns": "form_excluded_columns",
    # Permissions
    "can_create": "can_create",
    "can_edit": "can_edit",
    "can_delete": "can_delete",
    "can_view_details": "can_view_details",
    "can_export": "can_export",
    # Display
    "name": "name",
    "name_plural": "name_plural",
    "icon": "icon",
    "category": "category",
    # Pagination
    "page_size": "page_size",
    "page_size_options": "page_size_options",
}

# sqladmin-specific attributes that need special handling
SQLADMIN_SPECIFIC_ATTRS: frozenset[str] = frozenset(
    {
        "column_labels",  # sqladmin uses this for display labels
        "column_formatters",  # sqladmin uses this for value formatters
        "column_formatters_detail",  # sqladmin detail view formatters
        "column_type_formatters",  # sqladmin type-based formatters
        "form_args",  # sqladmin WTForms arguments
        "form_widget_args",  # sqladmin WTForms widget args
        "form_overrides",  # sqladmin form field overrides
        "form_include_pk",  # sqladmin flag to include PK in forms
        "form_ajax_refs",  # sqladmin AJAX relationship references
        "form_create_rules",  # sqladmin form layout rules
        "form_edit_rules",  # sqladmin form layout rules
        "column_details_list",  # sqladmin detail view columns
        "column_details_exclude_list",  # sqladmin detail view exclusions
        "list_query",  # sqladmin query customization (method)
        "count_query",  # sqladmin count query (method)
        "search_query",  # sqladmin search query (method)
        "edit_modal",  # sqladmin modal editing flag
        "create_modal",  # sqladmin modal creation flag
        "details_modal",  # sqladmin modal details flag
        "export_types",  # sqladmin export type list
        "export_max_rows",  # sqladmin export row limit
    }
)


def _is_empty_value(value: Any) -> bool:
    """Check if a value is considered empty/default.

    Args:
        value: The value to check.

    Returns:
        True if the value is None, empty list, or empty string.
    """
    return value is None or value in ([], "")


def _extract_sqladmin_attributes(sqladmin_view: type[Any]) -> dict[str, Any]:
    """Extract relevant attributes from an sqladmin ModelView.

    Args:
        sqladmin_view: The sqladmin ModelView class.

    Returns:
        Dictionary of attribute names to values.
    """
    attrs: dict[str, Any] = {}

    for sqladmin_attr, litestar_attr in SQLADMIN_ATTR_MAPPING.items():
        if hasattr(sqladmin_view, sqladmin_attr):
            value = getattr(sqladmin_view, sqladmin_attr)
            # Only include non-default values
            if not _is_empty_value(value):
                attrs[litestar_attr] = value

    return attrs


def _parse_sort_tuple(column: Any, direction: Any) -> tuple[str, str]:
    """Parse a sort tuple into (column, direction) format.

    Args:
        column: The column name or reference.
        direction: The direction (bool or string).

    Returns:
        Tuple of (column_name, direction_string).
    """
    if isinstance(direction, bool):
        return (str(column), "desc" if direction else "asc")
    if isinstance(direction, str):
        return (str(column), direction.lower())
    return (str(column), "asc")


def _convert_column_default_sort(sort_value: Any) -> tuple[str, str] | None:
    """Convert sqladmin column_default_sort to litestar-admin format.

    sqladmin supports multiple formats:
    - str: column name (ascending)
    - tuple: (column, desc_bool) or (column, "asc"/"desc")
    - list of tuples for multi-column sort (only first used)

    Args:
        sort_value: The sqladmin sort configuration.

    Returns:
        Tuple of (column_name, direction) or None.
    """
    if sort_value is None:
        return None

    if isinstance(sort_value, str):
        return (sort_value, "asc")

    if isinstance(sort_value, tuple) and len(sort_value) == 2:  # noqa: PLR2004
        return _parse_sort_tuple(sort_value[0], sort_value[1])

    if isinstance(sort_value, list) and len(sort_value) > 0:
        # Multi-column sort - use first column only
        return _convert_column_default_sort(sort_value[0])

    return None


def convert_sqladmin_view(
    sqladmin_view: type[Any],
    *,
    class_name: str | None = None,
    include_model: bool = True,
) -> type[BaseModelView]:
    """Convert an sqladmin ModelView to a litestar-admin BaseModelView.

    This function creates a new litestar-admin view class that mirrors
    the configuration of the provided sqladmin view.

    Args:
        sqladmin_view: The sqladmin ModelView class to convert.
        class_name: Optional name for the generated class. Defaults to
            the sqladmin view name with "Litestar" suffix.
        include_model: Whether to include the model reference in the
            converted view. Defaults to True.

    Returns:
        A new litestar-admin BaseModelView subclass.

    Raises:
        ValueError: If the sqladmin view has no model attribute.

    Example:
        ```python
        from sqladmin import ModelView


        class UserAdmin(ModelView, model=User):
            column_list = ["id", "email"]
            can_delete = False


        # Convert to litestar-admin
        LitestarUserAdmin = convert_sqladmin_view(UserAdmin)

        # Or with custom name
        MyUserAdmin = convert_sqladmin_view(UserAdmin, class_name="MyUserAdmin")
        ```
    """
    # Get the model from sqladmin view
    model = getattr(sqladmin_view, "model", None)
    if model is None and include_model:
        msg = f"sqladmin view {sqladmin_view.__name__} has no model attribute"
        raise ValueError(msg)

    # Extract attributes from sqladmin view
    attrs = _extract_sqladmin_attributes(sqladmin_view)

    # Handle column_default_sort conversion
    if "column_default_sort" in attrs:
        attrs["column_default_sort"] = _convert_column_default_sort(attrs["column_default_sort"])

    # Include model if requested
    if include_model and model is not None:
        attrs["model"] = model

    # Generate class name
    if class_name is None:
        class_name = f"Litestar{sqladmin_view.__name__}"

    # Create the new class dynamically
    return type(class_name, (BaseModelView,), attrs)


class SQLAdminBridge:
    """Bridge for converting multiple sqladmin views to litestar-admin.

    This class provides a convenient way to migrate an entire sqladmin
    configuration to litestar-admin.

    Attributes:
        sqladmin_views: List of registered sqladmin view classes.
        converted_views: Dictionary mapping sqladmin views to converted views.
        strict: Whether to raise errors for unsupported features.

    Example:
        ```python
        from sqladmin import ModelView


        class UserAdmin(ModelView, model=User):
            column_list = ["id", "email"]


        class PostAdmin(ModelView, model=Post):
            column_list = ["id", "title"]


        # Create bridge and register views
        bridge = SQLAdminBridge()
        bridge.register(UserAdmin)
        bridge.register(PostAdmin)

        # Convert all views
        litestar_views = bridge.convert_all()

        # Use with AdminPlugin
        from litestar_admin import AdminPlugin, AdminConfig, ModelRegistry

        registry = ModelRegistry()
        for view in litestar_views:
            registry.register(view)

        plugin = AdminPlugin(config=AdminConfig(registry=registry))
        ```
    """

    sqladmin_views: ClassVar[list[type[Any]]]
    converted_views: ClassVar[dict[type[Any], type[BaseModelView]]]

    def __init__(self, *, strict: bool = False) -> None:
        """Initialize the SQLAdmin bridge.

        Args:
            strict: If True, raise errors for sqladmin features that
                cannot be converted. If False, skip unsupported features
                with warnings. Defaults to False.
        """
        self.sqladmin_views: list[type[Any]] = []
        self.converted_views: dict[type[Any], type[BaseModelView]] = {}
        self.strict = strict
        self._warnings: list[str] = []

    def register(self, sqladmin_view: type[Any]) -> None:
        """Register an sqladmin view for conversion.

        Args:
            sqladmin_view: The sqladmin ModelView class to register.

        Raises:
            ValueError: If the view is already registered.
        """
        if sqladmin_view in self.sqladmin_views:
            msg = f"View {sqladmin_view.__name__} is already registered"
            raise ValueError(msg)

        self.sqladmin_views.append(sqladmin_view)

    def register_many(self, sqladmin_views: Sequence[type[Any]]) -> None:
        """Register multiple sqladmin views for conversion.

        Args:
            sqladmin_views: Sequence of sqladmin ModelView classes.
        """
        for view in sqladmin_views:
            self.register(view)

    def convert(self, sqladmin_view: type[Any]) -> type[BaseModelView]:
        """Convert a single registered sqladmin view.

        Args:
            sqladmin_view: The sqladmin ModelView class to convert.

        Returns:
            The converted litestar-admin view class.

        Raises:
            ValueError: If the view is not registered.
        """
        if sqladmin_view not in self.sqladmin_views:
            msg = f"View {sqladmin_view.__name__} is not registered"
            raise ValueError(msg)

        if sqladmin_view in self.converted_views:
            return self.converted_views[sqladmin_view]

        # Check for unsupported features
        self._check_unsupported_features(sqladmin_view)

        # Convert the view
        converted = convert_sqladmin_view(sqladmin_view)
        self.converted_views[sqladmin_view] = converted

        return converted

    def convert_all(self) -> list[type[BaseModelView]]:
        """Convert all registered sqladmin views.

        Returns:
            List of converted litestar-admin view classes.
        """
        return [self.convert(view) for view in self.sqladmin_views]

    def _check_unsupported_features(self, sqladmin_view: type[Any]) -> None:
        """Check for sqladmin features that cannot be converted.

        Args:
            sqladmin_view: The sqladmin view to check.

        Raises:
            ValueError: If strict mode is enabled and unsupported
                features are found.
        """
        unsupported: list[str] = []

        for attr in SQLADMIN_SPECIFIC_ATTRS:
            if hasattr(sqladmin_view, attr):
                value = getattr(sqladmin_view, attr)
                # Check if it's a non-default value
                if value is not None and value not in ([], {}):
                    unsupported.append(attr)

        if unsupported:
            msg = (
                f"View {sqladmin_view.__name__} uses sqladmin-specific features "
                f"that cannot be converted: {', '.join(unsupported)}"
            )
            if self.strict:
                raise ValueError(msg)
            self._warnings.append(msg)

    @property
    def warnings(self) -> list[str]:
        """Get warnings generated during conversion.

        Returns:
            List of warning messages.
        """
        return self._warnings.copy()

    def clear_warnings(self) -> None:
        """Clear all accumulated warnings."""
        self._warnings.clear()

    def get_model_mapping(self) -> dict[type[Any], type[BaseModelView]]:
        """Get mapping of SQLAlchemy models to litestar-admin views.

        This is useful for understanding which models have been
        converted and their corresponding views.

        Returns:
            Dictionary mapping model classes to view classes.
        """
        mapping: dict[type[Any], type[BaseModelView]] = {}
        for sqladmin_view, litestar_view in self.converted_views.items():
            model = getattr(sqladmin_view, "model", None)
            if model is not None:
                mapping[model] = litestar_view
        return mapping

    def __len__(self) -> int:
        """Return number of registered views."""
        return len(self.sqladmin_views)

    def __contains__(self, sqladmin_view: type[Any]) -> bool:
        """Check if a view is registered."""
        return sqladmin_view in self.sqladmin_views
