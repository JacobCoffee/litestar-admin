"""Auto-discovery utilities for SQLAlchemy models."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from litestar_admin.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Iterable

    from litestar import Litestar
    from sqlalchemy.orm import Mapper

    from litestar_admin.views import BaseModelView

__all__ = [
    "discover_models",
    "create_default_view",
    "get_declarative_bases",
    "is_advanced_alchemy_model",
]

logger = get_logger("litestar_admin.discovery")


def get_declarative_bases(app: Litestar) -> list[type]:
    """Extract DeclarativeBase classes from the application state.

    This function looks for DeclarativeBase subclasses in common locations:
    1. App state (app.state.db_base, app.state.base, etc.)
    2. Advanced-Alchemy plugin configuration
    3. SQLAlchemy plugin configuration

    Args:
        app: The Litestar application instance.

    Returns:
        List of DeclarativeBase classes found in the application.
    """
    bases: list[type] = []

    # Check app.state for common base patterns
    state = getattr(app, "state", None)
    if state is not None:
        for attr_name in ("db_base", "base", "Base", "database_base", "DeclarativeBase"):
            base = getattr(state, attr_name, None)
            if base is not None and _is_declarative_base(base):
                bases.append(base)

    # Check for Advanced-Alchemy plugin
    for plugin in app.plugins:
        plugin_class_name = type(plugin).__name__

        # Advanced-Alchemy stores config with engine/session info
        if plugin_class_name == "SQLAlchemyPlugin":
            config = getattr(plugin, "_config", None) or getattr(plugin, "config", None)
            if config is not None:
                # Get engine_config which may have the metadata
                engine_config = getattr(config, "engine_config", None)
                if engine_config is not None:
                    metadata = getattr(engine_config, "metadata", None)
                    if metadata is not None:
                        # Try to find the base from registry
                        registry = getattr(metadata, "registry", None)
                        if registry is not None:
                            # Find the declarative base from the registry
                            base = _find_base_from_registry(registry)
                            if base is not None and base not in bases:
                                bases.append(base)

    # Fallback: Scan all DeclarativeBase subclasses in Python
    if not bases:
        bases = _find_all_declarative_bases()

    return bases


def _is_declarative_base(obj: Any) -> bool:
    """Check if an object is a DeclarativeBase subclass.

    Args:
        obj: Object to check.

    Returns:
        True if obj is a DeclarativeBase subclass.
    """
    from sqlalchemy.orm import DeclarativeBase

    try:
        return isinstance(obj, type) and issubclass(obj, DeclarativeBase)
    except TypeError:
        return False


def _find_base_from_registry(registry: Any) -> type | None:
    """Find the DeclarativeBase from a SQLAlchemy registry.

    Args:
        registry: SQLAlchemy registry instance.

    Returns:
        The DeclarativeBase class if found.
    """
    from sqlalchemy.orm import DeclarativeBase

    # The registry has mappers that point to classes
    for mapper in getattr(registry, "mappers", []):
        cls = mapper.class_
        # Walk up the MRO to find DeclarativeBase subclass
        for base in type(cls).__mro__:
            if base is not DeclarativeBase and _is_declarative_base(base):
                return base
    return None


def _find_all_declarative_bases() -> list[type]:
    """Find all DeclarativeBase subclasses by traversing subclasses.

    This is a fallback method that finds all DeclarativeBase subclasses
    in the current Python runtime.

    Returns:
        List of DeclarativeBase subclasses.
    """
    from sqlalchemy.orm import DeclarativeBase

    bases: list[type] = []

    def _collect_bases(cls: type) -> None:
        """Recursively collect direct DeclarativeBase subclasses."""
        for subclass in cls.__subclasses__():
            # Only include direct subclasses that are meant to be bases
            # (not the actual model classes)
            if subclass.__name__ != "Base" and not hasattr(subclass, "__tablename__"):
                # This is likely a user-defined base
                if _has_models(subclass):
                    bases.append(subclass)
            elif subclass.__name__ == "Base":
                bases.append(subclass)

    _collect_bases(DeclarativeBase)
    return bases


def _has_models(base: type) -> bool:
    """Check if a base class has any model subclasses with tables.

    Args:
        base: The base class to check.

    Returns:
        True if the base has model subclasses.
    """
    registry = getattr(base, "_sa_registry", None) or getattr(base, "registry", None)
    if registry is not None:
        mappers = getattr(registry, "mappers", [])
        return len(list(mappers)) > 0
    return False


def discover_models(
    bases: Iterable[type],
    *,
    exclude_models: set[type] | None = None,
) -> list[type]:
    """Discover all SQLAlchemy model classes from DeclarativeBase subclasses.

    Args:
        bases: Iterable of DeclarativeBase classes to scan.
        exclude_models: Set of model classes to exclude from discovery.

    Returns:
        List of discovered model classes.
    """
    from sqlalchemy.orm import DeclarativeBase

    exclude_models = exclude_models or set()
    discovered: list[type] = []

    for base in bases:
        # Get the SQLAlchemy registry from the base
        registry = getattr(base, "_sa_registry", None) or getattr(base, "registry", None)

        if registry is None:
            logger.debug("No registry found for base %s", base.__name__)
            continue

        # Get all mappers from the registry
        mappers: Iterable[Mapper[Any]] = getattr(registry, "mappers", [])

        for mapper in mappers:
            model_class = mapper.class_

            # Skip if already excluded
            if model_class in exclude_models:
                logger.debug("Skipping excluded model: %s", model_class.__name__)
                continue

            # Skip if it's the base class itself
            if model_class is base or model_class is DeclarativeBase:
                continue

            # Skip abstract models (no __tablename__)
            if not hasattr(model_class, "__tablename__"):
                logger.debug("Skipping abstract model: %s", model_class.__name__)
                continue

            # Skip if __abstract__ is True
            if getattr(model_class, "__abstract__", False):
                logger.debug("Skipping abstract model: %s", model_class.__name__)
                continue

            if model_class not in discovered:
                discovered.append(model_class)
                logger.debug("Discovered model: %s", model_class.__name__)

    return discovered


def is_advanced_alchemy_model(model: type) -> bool:
    """Check if a model uses Advanced-Alchemy's CommonTableAttributes.

    Advanced-Alchemy models typically have these columns:
    - id (UUID primary key)
    - created_at (DateTime)
    - updated_at (DateTime)

    Args:
        model: The model class to check.

    Returns:
        True if the model appears to use Advanced-Alchemy patterns.
    """
    # Check for common Advanced-Alchemy mixins/base classes
    advanced_alchemy_markers = (
        "CommonTableAttributes",
        "UUIDPrimaryKey",
        "BigIntPrimaryKey",
        "AuditColumns",
        "SlugKey",
    )

    for base in model.__mro__:
        if base.__name__ in advanced_alchemy_markers:
            return True

    # Also check for typical AA column patterns
    if hasattr(model, "__table__"):
        table = cast("Any", model.__table__)
        columns = {c.name for c in table.columns}
        aa_columns = {"id", "created_at", "updated_at"}
        if aa_columns.issubset(columns):
            # Check if id is UUID type
            for col in table.columns:
                if col.name == "id":
                    col_type = str(col.type).upper()
                    if "UUID" in col_type or "GUID" in col_type:
                        return True

    return False


def _get_icon_for_model(model_name: str) -> str:
    """Get an appropriate icon name based on model name patterns.

    Args:
        model_name: The model class name.

    Returns:
        Icon name string.
    """
    model_name_lower = model_name.lower()

    icon_patterns = {
        "user": "user",
        "post": "file-text",
        "article": "file-text",
        "comment": "message-square",
        "tag": "tag",
        "category": "tag",
        "order": "shopping-cart",
        "product": "package",
    }

    for pattern, icon in icon_patterns.items():
        if pattern in model_name_lower:
            return icon

    return "database"


def _build_column_config(model: type) -> dict[str, Any]:
    """Build column configuration from model's table definition.

    Args:
        model: The SQLAlchemy model class.

    Returns:
        Dictionary with column configuration attributes.
    """
    if not hasattr(model, "__table__"):
        return {}

    table = cast("Any", model.__table__)
    columns = table.columns
    column_list: list[str] = []
    column_searchable_list: list[str] = []
    column_sortable_list: list[str] = []
    form_excluded_columns: list[str] = []

    for col in columns:
        col_name = col.name
        col_type = str(col.type).upper()

        column_list.append(col_name)
        column_sortable_list.append(col_name)

        # Make string columns searchable
        if any(t in col_type for t in ("VARCHAR", "TEXT", "STRING")):
            column_searchable_list.append(col_name)

        # Exclude auto-generated columns from forms
        if col.primary_key and col.autoincrement:
            form_excluded_columns.append(col_name)

        # Exclude timestamp columns that are auto-managed
        if col_name in ("created_at", "updated_at") and col.default is not None:
            form_excluded_columns.append(col_name)

    config: dict[str, Any] = {
        "column_list": column_list,
        "column_searchable_list": column_searchable_list,
        "column_sortable_list": column_sortable_list,
        "form_excluded_columns": form_excluded_columns,
    }

    # Set default sort
    if "id" in column_list:
        config["column_default_sort"] = ("id", "desc")
    elif column_list:
        config["column_default_sort"] = (column_list[0], "asc")

    return config


def create_default_view(
    model: type,
    *,
    auto_columns: bool = True,
) -> type[BaseModelView]:
    """Create a default view class for a model.

    This creates a dynamically generated view class with sensible defaults
    based on the model's columns and configuration.

    Args:
        model: The SQLAlchemy model class.
        auto_columns: Whether to auto-detect column configurations.

    Returns:
        A new view class for the model.
    """
    from litestar_admin.views import BaseModelView

    # Prepare class attributes
    class_attrs: dict[str, Any] = {
        "model": model,
        "name": model.__name__,
        "name_plural": f"{model.__name__}s",
    }

    # Auto-detect column configurations
    if auto_columns:
        class_attrs.update(_build_column_config(model))

    # Handle Advanced-Alchemy specific patterns
    if is_advanced_alchemy_model(model):
        class_attrs["icon"] = _get_icon_for_model(model.__name__)

    # Create the dynamic class
    view_class = type(
        f"{model.__name__}Admin",
        (BaseModelView,),
        class_attrs,
    )

    logger.info("Created default view for model: %s", model.__name__)
    return view_class
