"""BaseModelView class with configuration options."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from litestar.connection import ASGIConnection

__all__ = ["BaseModelView"]


class BaseModelView:
    """Base class for model admin views.

    This class provides the foundation for all model views in the admin panel.
    Subclasses configure how models are displayed and edited in the admin interface.

    Class Attributes:
        model: The SQLAlchemy model class this view manages.
        name: Display name for the model (defaults to model class name).
        name_plural: Plural display name (defaults to name + 's').
        icon: Icon name for the sidebar (FontAwesome or similar).
        category: Category name for grouping in sidebar.
        column_list: List of columns to display in the list view.
        column_exclude_list: Columns to exclude from list view.
        column_searchable_list: Columns that are searchable.
        column_sortable_list: Columns that are sortable.
        column_default_sort: Default sort column and order.
        form_columns: Columns to include in create/edit forms.
        form_excluded_columns: Columns to exclude from forms.
        can_create: Whether new records can be created.
        can_edit: Whether records can be edited.
        can_delete: Whether records can be deleted.
        can_view_details: Whether record details can be viewed.
        can_export: Whether records can be exported.
        page_size: Default number of records per page.
        page_size_options: Available page size options.

    Example:
        ```python
        from litestar_admin import BaseModelView
        from myapp.models import User

        class UserAdmin(BaseModelView):
            model = User
            column_list = ["id", "email", "name", "created_at"]
            column_searchable_list = ["email", "name"]
            can_delete = False
        ```
    """

    # Model configuration
    model: ClassVar[type[Any]]
    name: ClassVar[str] = ""
    name_plural: ClassVar[str] = ""
    icon: ClassVar[str] = "table"
    category: ClassVar[str | None] = None

    # Column configuration
    column_list: ClassVar[list[str]] = []
    column_exclude_list: ClassVar[list[str]] = []
    column_searchable_list: ClassVar[list[str]] = []
    column_sortable_list: ClassVar[list[str]] = []
    column_default_sort: ClassVar[tuple[str, str] | None] = None  # (column, "asc"|"desc")

    # Form configuration
    form_columns: ClassVar[list[str]] = []
    form_excluded_columns: ClassVar[list[str]] = []

    # Permissions
    can_create: ClassVar[bool] = True
    can_edit: ClassVar[bool] = True
    can_delete: ClassVar[bool] = True
    can_view_details: ClassVar[bool] = True
    can_export: ClassVar[bool] = True

    # Pagination
    page_size: ClassVar[int] = 25
    page_size_options: ClassVar[list[int]] = [10, 25, 50, 100]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Initialize subclass with defaults."""
        super().__init_subclass__(**kwargs)

        # Set name from model if not specified
        if not cls.name and hasattr(cls, "model"):
            cls.name = cls.model.__name__

        # Set plural name
        if not cls.name_plural and cls.name:
            cls.name_plural = f"{cls.name}s"

    @classmethod
    def get_list_columns(cls) -> list[str]:
        """Get columns to display in list view.

        Returns:
            List of column names.
        """
        if cls.column_list:
            return [c for c in cls.column_list if c not in cls.column_exclude_list]

        # Auto-detect columns from model
        if hasattr(cls.model, "__table__"):
            all_columns = [c.name for c in cls.model.__table__.columns]
            return [c for c in all_columns if c not in cls.column_exclude_list]

        return []

    @classmethod
    def get_form_columns(cls, *, is_create: bool = False) -> list[str]:
        """Get columns to include in create/edit forms.

        Args:
            is_create: Whether this is for a create form.

        Returns:
            List of column names for the form.
        """
        if cls.form_columns:
            return [c for c in cls.form_columns if c not in cls.form_excluded_columns]

        # Auto-detect columns from model, excluding primary keys for create
        if hasattr(cls.model, "__table__"):
            columns = []
            for c in cls.model.__table__.columns:
                if c.name in cls.form_excluded_columns:
                    continue
                # Skip auto-increment primary keys on create
                if is_create and c.primary_key and c.autoincrement:
                    continue
                columns.append(c.name)
            return columns

        return []

    @classmethod
    def get_column_info(cls, column_name: str) -> dict[str, Any]:
        """Get metadata for a column.

        Args:
            column_name: The column name.

        Returns:
            Dictionary with column metadata.
        """
        info: dict[str, Any] = {
            "name": column_name,
            "sortable": column_name in cls.column_sortable_list,
            "searchable": column_name in cls.column_searchable_list,
        }

        # Get type info from model if available
        if hasattr(cls.model, "__table__"):
            for c in cls.model.__table__.columns:
                if c.name == column_name:
                    info["type"] = str(c.type)
                    info["nullable"] = c.nullable
                    info["primary_key"] = c.primary_key
                    break

        return info

    @classmethod
    async def is_accessible(cls, connection: ASGIConnection) -> bool:  # noqa: ARG003
        """Check if the view is accessible for the current request.

        Override this method to implement custom access control.

        Args:
            connection: The current ASGI connection.

        Returns:
            True if accessible, False otherwise.
        """
        return True

    @classmethod
    async def can_create_record(cls, connection: ASGIConnection) -> bool:
        """Check if a record can be created.

        Args:
            connection: The current ASGI connection.

        Returns:
            True if creation is allowed.
        """
        return cls.can_create and await cls.is_accessible(connection)

    @classmethod
    async def can_edit_record(
        cls,
        connection: ASGIConnection,
        record: Any,  # noqa: ARG003
    ) -> bool:
        """Check if a specific record can be edited.

        Args:
            connection: The current ASGI connection.
            record: The record to check.

        Returns:
            True if editing is allowed.
        """
        return cls.can_edit and await cls.is_accessible(connection)

    @classmethod
    async def can_delete_record(
        cls,
        connection: ASGIConnection,
        record: Any,  # noqa: ARG003
    ) -> bool:
        """Check if a specific record can be deleted.

        Args:
            connection: The current ASGI connection.
            record: The record to check.

        Returns:
            True if deletion is allowed.
        """
        return cls.can_delete and await cls.is_accessible(connection)

    @classmethod
    async def on_model_change(
        cls,
        data: dict[str, Any],
        record: Any | None,  # noqa: ARG003
        *,
        is_create: bool,  # noqa: ARG003
    ) -> dict[str, Any]:
        """Hook called before creating or updating a record.

        Override to modify data before save or perform validation.

        Args:
            data: The data being saved.
            record: The existing record (None for create).
            is_create: Whether this is a create operation.

        Returns:
            The (possibly modified) data to save.
        """
        return data

    @classmethod
    async def after_model_change(
        cls,
        record: Any,
        *,
        is_create: bool,
    ) -> None:
        """Hook called after creating or updating a record.

        Override to perform post-save actions.

        Args:
            record: The saved record.
            is_create: Whether this was a create operation.
        """

    @classmethod
    async def after_model_delete(cls, record: Any) -> None:
        """Hook called after deleting a record.

        Override to perform post-delete actions.

        Args:
            record: The deleted record.
        """
