"""BaseModelView class with configuration options."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from litestar_admin.relationships import RelationshipDetector, get_relationship_detector
from litestar_admin.views.admin_view import BaseAdminView

if TYPE_CHECKING:
    from litestar.connection import ASGIConnection

    from litestar_admin.fields.file import FileField
    from litestar_admin.relationships import RelationshipInfo

__all__ = ["BaseModelView"]


class BaseModelView(BaseAdminView):
    """Base class for model admin views.

    This class provides the foundation for all model views in the admin panel.
    Subclasses configure how models are displayed and edited in the admin interface.

    Attributes:
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

    Example::

        from litestar_admin import BaseModelView
        from myapp.models import User


        class UserAdmin(BaseModelView):
            model = User
            column_list = ["id", "email", "name", "created_at"]
            column_searchable_list = ["email", "name"]
            can_delete = False
    """

    # Model configuration
    model: ClassVar[type[Any]]
    name: ClassVar[str] = ""
    name_plural: ClassVar[str] = ""
    icon: ClassVar[str] = "table"
    category: ClassVar[str | None] = None
    view_type: ClassVar[str] = "model"  # Override from BaseAdminView

    # Column configuration
    column_list: ClassVar[list[str]] = []
    column_exclude_list: ClassVar[list[str]] = []
    column_searchable_list: ClassVar[list[str]] = []
    column_sortable_list: ClassVar[list[str]] = []
    column_default_sort: ClassVar[tuple[str, str] | None] = None  # (column, "asc"|"desc")

    # Form configuration
    form_columns: ClassVar[list[str]] = []
    form_excluded_columns: ClassVar[list[str]] = []
    form_extra_fields: ClassVar[dict[str, dict[str, Any]]] = {}
    file_fields: ClassVar[list[FileField]] = []
    """List of file upload fields for this model.

    Define FileField or ImageField instances for columns that should
    accept file uploads in create/edit forms.

    Example::

        from litestar_admin import ModelView
        from litestar_admin.fields import FileField, ImageField
        from myapp.models import Product


        class ProductAdmin(ModelView, model=Product):
            file_fields = [
                FileField(
                    name="manual",
                    allowed_extensions=["pdf"],
                    max_size=20 * 1024 * 1024,
                ),
                ImageField(
                    name="photo",
                    generate_thumbnail=True,
                ),
            ]
    """

    # Permissions
    can_create: ClassVar[bool] = True
    can_edit: ClassVar[bool] = True
    can_delete: ClassVar[bool] = True
    can_view_details: ClassVar[bool] = True
    can_export: ClassVar[bool] = True

    # Pagination
    page_size: ClassVar[int] = 25
    page_size_options: ClassVar[list[int]] = [10, 25, 50, 100]

    # Relationship configuration
    _relationship_detector: ClassVar[RelationshipDetector | None] = None
    relationship_search_fields: ClassVar[dict[str, list[str]]] = {}
    """Custom search fields per relationship for autocomplete.

    Map relationship field names to lists of column names to search.
    If not specified, defaults to searching the display column and primary key.

    Example::

        class PostAdmin(ModelView, model=Post):
            relationship_search_fields = {
                "author": ["email", "name", "username"],
                "category": ["name", "slug"],
            }
    """

    relationship_display_fields: ClassVar[dict[str, list[str]]] = {}
    """Additional fields to include in relationship autocomplete responses.

    Map relationship field names to lists of column names for extra data.
    This data is included in the 'data' field of RelationshipOption.

    Example::

        class PostAdmin(ModelView, model=Post):
            relationship_display_fields = {
                "author": ["email", "avatar_url"],
                "category": ["description"],
            }
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Initialize subclass with defaults."""
        super().__init_subclass__(**kwargs)

        # Set name from model if not specified
        if not cls.name and hasattr(cls, "model"):
            cls.name = cls.model.__name__

        # Set identity from name (needed because BaseAdminView skips this for model views)
        if cls.name and not cls.identity:
            cls.identity = cls.name.lower().replace(" ", "-")

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
    def get_form_extra_fields(cls, *, is_create: bool = False) -> dict[str, dict[str, Any]]:  # noqa: ARG003
        """Get extra virtual fields to include in forms.

        Virtual fields are form-only fields that don't map directly to database
        columns. Use this for fields like 'password' that get processed via
        on_model_change hook before saving.

        Args:
            is_create: Whether this is for a create form.

        Returns:
            Dictionary of field names to JSON schema property definitions.
        """
        return cls.form_extra_fields.copy()

    @classmethod
    def get_file_fields(cls) -> list[FileField]:
        """Get all file fields defined for this model view.

        Returns:
            List of FileField or ImageField instances.
        """
        return cls.file_fields.copy()

    @classmethod
    def get_file_field(cls, field_name: str) -> FileField | None:
        """Get a file field by name.

        Args:
            field_name: The name of the file field.

        Returns:
            The FileField or ImageField instance, or None if not found.
        """
        for field in cls.file_fields:
            if field.name == field_name:
                return field
        return None

    @classmethod
    def get_file_field_names(cls) -> list[str]:
        """Get the names of all file fields.

        Returns:
            List of file field names.
        """
        return [field.name for field in cls.file_fields]

    @classmethod
    def is_file_field(cls, field_name: str) -> bool:
        """Check if a field is a file upload field.

        Args:
            field_name: The field name to check.

        Returns:
            True if the field is a file field, False otherwise.
        """
        return field_name in cls.get_file_field_names()

    @classmethod
    def get_file_fields_info(cls) -> list[dict[str, Any]]:
        """Get file field configuration for API responses.

        Returns:
            List of dictionaries with file field configurations.
        """
        return [field.to_dict() for field in cls.file_fields]

    @classmethod
    def get_column_info(cls, column_name: str) -> dict[str, Any]:
        """Get metadata for a column, including relationship information.

        Args:
            column_name: The column name.

        Returns:
            Dictionary with column metadata including:
            - name: The column name
            - sortable: Whether the column is sortable
            - searchable: Whether the column is searchable
            - type: The SQLAlchemy type (for regular columns)
            - nullable: Whether the column is nullable
            - primary_key: Whether this is a primary key
            - is_relationship: Whether this is a relationship field
            - relationship_type: The type of relationship (if is_relationship)
            - related_model_name: Name of the related model (if is_relationship)
        """
        info: dict[str, Any] = {
            "name": column_name,
            "sortable": column_name in cls.column_sortable_list,
            "searchable": column_name in cls.column_searchable_list,
            "is_relationship": False,
            "is_file_field": False,
        }

        # Check if this is a file field
        file_field = cls.get_file_field(column_name)
        if file_field is not None:
            info["is_file_field"] = True
            info["file_field_config"] = file_field.to_dict()
            return info

        # Check if this is a relationship field
        rel_info = cls.get_relationship_info(column_name)
        if rel_info is not None:
            info["is_relationship"] = True
            info["relationship_type"] = rel_info.relationship_type.value
            info["related_model_name"] = rel_info.related_model_name
            info["nullable"] = rel_info.nullable
            info["uselist"] = rel_info.uselist
            info["foreign_key_column"] = rel_info.foreign_key_column
            info["back_populates"] = rel_info.back_populates
            return info

        # Get type info from model if available (regular columns)
        if hasattr(cls.model, "__table__"):
            for c in cls.model.__table__.columns:
                if c.name == column_name:
                    info["type"] = str(c.type)
                    info["nullable"] = c.nullable
                    info["primary_key"] = c.primary_key
                    break

        return info

    @classmethod
    def get_relationship_detector(cls) -> RelationshipDetector:
        """Get the relationship detector instance.

        Returns:
            The RelationshipDetector instance for this view.
        """
        if cls._relationship_detector is None:
            cls._relationship_detector = get_relationship_detector()
        return cls._relationship_detector

    @classmethod
    def relationship_fields(cls) -> list[RelationshipInfo]:
        """Get all detected relationships for this model.

        This property returns a list of RelationshipInfo objects describing
        all relationships defined on the model.

        Returns:
            List of RelationshipInfo objects for all relationships.

        Example::

            class UserAdmin(ModelView, model=User):
                pass

            # Get all relationships
            for rel in UserAdmin.relationship_fields():
                print(f"{rel.name}: {rel.relationship_type.value}")
        """
        if not hasattr(cls, "model"):
            return []
        detector = cls.get_relationship_detector()
        return detector.detect_relationships(cls.model)

    @classmethod
    def get_relationship_info(cls, field_name: str) -> RelationshipInfo | None:
        """Get relationship info for a specific field.

        Args:
            field_name: The name of the relationship field to look up.

        Returns:
            RelationshipInfo if the field is a relationship, None otherwise.

        Example::

            class PostAdmin(ModelView, model=Post):
                pass

            # Get info about the 'author' relationship
            rel_info = PostAdmin.get_relationship_info("author")
            if rel_info:
                print(f"Related to: {rel_info.related_model_name}")
                print(f"FK column: {rel_info.foreign_key_column}")
        """
        if not hasattr(cls, "model"):
            return None
        detector = cls.get_relationship_detector()
        return detector.get_relationship_info(cls.model, field_name)

    @classmethod
    def get_relationship_names(cls) -> list[str]:
        """Get the names of all relationship fields on this model.

        Returns:
            List of relationship attribute names.
        """
        if not hasattr(cls, "model"):
            return []
        detector = cls.get_relationship_detector()
        return detector.get_relationship_names(cls.model)

    @classmethod
    def is_relationship_field(cls, field_name: str) -> bool:
        """Check if a field is a relationship.

        Args:
            field_name: The field name to check.

        Returns:
            True if the field is a relationship, False otherwise.
        """
        if not hasattr(cls, "model"):
            return False
        detector = cls.get_relationship_detector()
        return detector.is_relationship(cls.model, field_name)

    @classmethod
    def get_display_column_for_related_model(cls, relationship_name: str) -> str | None:
        """Get the best display column for a related model.

        This is useful for showing related records in dropdowns or display fields.

        Args:
            relationship_name: The name of the relationship.

        Returns:
            The display column name for the related model, or None if not found.
        """
        rel_info = cls.get_relationship_info(relationship_name)
        if rel_info is None:
            return None
        detector = cls.get_relationship_detector()
        return detector.get_display_column(rel_info.related_model)

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

    @classmethod
    def get_api_routes(cls) -> list[dict[str, Any]]:
        """Return API route definitions for this model view.

        Model views return standard CRUD routes. The actual controller
        registration is handled by the registry and plugin.

        Returns:
            List of route definitions for CRUD operations.
        """
        # The routes are dynamically generated by the AdminController
        # based on the model configuration. This method exists to satisfy
        # the BaseAdminView abstract interface.
        base_path = f"/api/models/{cls.identity}"
        return [
            {
                "path": base_path,
                "methods": ["GET"],
                "operation": "list",
                "name": f"{cls.identity}-list",
            },
            {
                "path": f"{base_path}/{{pk:str}}",
                "methods": ["GET"],
                "operation": "get",
                "name": f"{cls.identity}-get",
            },
            {
                "path": base_path,
                "methods": ["POST"],
                "operation": "create",
                "name": f"{cls.identity}-create",
            },
            {
                "path": f"{base_path}/{{pk:str}}",
                "methods": ["PUT", "PATCH"],
                "operation": "update",
                "name": f"{cls.identity}-update",
            },
            {
                "path": f"{base_path}/{{pk:str}}",
                "methods": ["DELETE"],
                "operation": "delete",
                "name": f"{cls.identity}-delete",
            },
        ]
