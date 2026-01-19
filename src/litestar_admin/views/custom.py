"""CustomView class for non-model data sources."""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Literal, cast

from litestar_admin.views.admin_view import BaseAdminView

if TYPE_CHECKING:
    from litestar.connection import ASGIConnection

__all__ = ["CustomView", "ColumnDefinition", "ListResult"]


@dataclass
class ColumnDefinition:
    """Definition for a column in a custom view.

    Attributes:
        name: Internal field name used in data dictionaries.
        label: Display label for the column header.
        type: Data type for rendering and validation.
        sortable: Whether the column can be sorted.
        searchable: Whether the column can be searched.
        filterable: Whether the column can be filtered.
        visible: Whether the column is visible in list view.
        format: Optional format string for display (e.g., "currency", "date").
        render_template: Optional custom template for rendering.

    Example::

        ColumnDefinition(
            name="email",
            label="Email Address",
            type="string",
            sortable=True,
            searchable=True,
        )
    """

    name: str
    label: str = ""
    type: Literal[
        "string",
        "integer",
        "float",
        "boolean",
        "datetime",
        "date",
        "time",
        "json",
        "text",
        "email",
        "url",
        "uuid",
    ] = "string"
    sortable: bool = False
    searchable: bool = False
    filterable: bool = False
    visible: bool = True
    format: str | None = None
    render_template: str | None = None

    def __post_init__(self) -> None:
        """Set label from name if not provided."""
        if not self.label:
            self.label = self.name.replace("_", " ").title()


@dataclass
class ListResult:
    """Result container for list operations.

    Attributes:
        items: List of item dictionaries.
        total: Total number of items (for pagination).
        page: Current page number (1-indexed).
        page_size: Number of items per page.
        has_next: Whether there is a next page.
        has_prev: Whether there is a previous page.

    Example::

        ListResult(
            items=[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
            total=100,
            page=1,
            page_size=25,
        )
    """

    items: list[dict[str, Any]] = field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 25
    has_next: bool = False
    has_prev: bool = False

    def __post_init__(self) -> None:
        """Calculate pagination flags."""
        if self.total > 0 and self.page_size > 0:
            total_pages = (self.total + self.page_size - 1) // self.page_size
            self.has_next = self.page < total_pages
            self.has_prev = self.page > 1


class CustomView(BaseAdminView):
    """Base class for custom (non-model) admin views.

    CustomView enables creating admin interfaces for data sources that
    don't use SQLAlchemy models, such as external APIs, in-memory data,
    file systems, or any custom data provider.

    Subclasses must implement the data retrieval methods (get_list, get_one)
    and define their columns explicitly since there's no model to introspect.

    Attributes:
        columns: List of column definitions for this view.
        pk_field: Name of the primary key field (default: "id").
        can_create: Whether new items can be created.
        can_edit: Whether items can be edited.
        can_delete: Whether items can be deleted.
        can_view_details: Whether item details can be viewed.
        can_export: Whether items can be exported.
        page_size: Default number of items per page.
        page_size_options: Available page size options.

    Example::

        class ExternalAPIView(CustomView):
            name = "External Users"
            icon = "users"
            pk_field = "id"
            columns = [
                ColumnDefinition(name="id", label="ID", type="integer"),
                ColumnDefinition(name="email", label="Email", type="email", searchable=True),
                ColumnDefinition(name="name", label="Name", type="string", sortable=True),
            ]

            async def get_list(
                self,
                page: int = 1,
                page_size: int = 25,
                filters: dict[str, Any] | None = None,
                sort_by: str | None = None,
                sort_order: str = "asc",
                search: str | None = None,
            ) -> ListResult:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        "https://api.example.com/users",
                        params={"page": page, "limit": page_size},
                    )
                    data = response.json()
                    return ListResult(
                        items=data["users"],
                        total=data["total"],
                        page=page,
                        page_size=page_size,
                    )

            async def get_one(self, item_id: str) -> dict[str, Any] | None:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"https://api.example.com/users/{item_id}")
                    if response.status_code == 404:
                        return None
                    return response.json()
    """

    # View type discriminator
    view_type: ClassVar[Literal["custom"]] = "custom"

    # Column definitions (must be explicitly defined since no model introspection)
    # Accepts list of ColumnDefinition or dicts (normalized to ColumnDefinition in __init_subclass__)
    columns: ClassVar[list[ColumnDefinition | dict[str, Any]]] = []

    # Primary key field name
    pk_field: ClassVar[str] = "id"

    # Permissions
    can_create: ClassVar[bool] = False  # Disabled by default for read-only views
    can_edit: ClassVar[bool] = False
    can_delete: ClassVar[bool] = False
    can_view_details: ClassVar[bool] = True
    can_export: ClassVar[bool] = True

    # Pagination
    page_size: ClassVar[int] = 25
    page_size_options: ClassVar[list[int]] = [10, 25, 50, 100]

    @classmethod
    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Initialize subclass with defaults.

        Args:
            **kwargs: Additional keyword arguments.
        """
        super().__init_subclass__(**kwargs)

        # Convert dict columns to ColumnDefinition if needed
        if cls.columns:
            normalized: list[ColumnDefinition] = []
            for col in cls.columns:
                if isinstance(col, dict):
                    col_dict = cast("dict[str, Any]", col)
                    normalized.append(ColumnDefinition(**col_dict))
                elif isinstance(col, ColumnDefinition):
                    normalized.append(col)
                else:
                    msg = f"Column must be a dict or ColumnDefinition, got {type(col)}"
                    raise TypeError(msg)
            # Update to normalized list (type: ignore needed as we're changing the type)
            cls.columns = normalized  # type: ignore[assignment]

    @abstractmethod
    async def get_list(
        self,
        page: int = 1,
        page_size: int = 25,
        filters: dict[str, Any] | None = None,
        sort_by: str | None = None,
        sort_order: Literal["asc", "desc"] = "asc",
        search: str | None = None,
    ) -> ListResult:
        """Retrieve a paginated list of items.

        This method must be implemented by subclasses to fetch data from
        the custom data source.

        Args:
            page: Page number (1-indexed).
            page_size: Number of items per page.
            filters: Dictionary of filter field names to values.
            sort_by: Field name to sort by.
            sort_order: Sort direction ("asc" or "desc").
            search: Search query string.

        Returns:
            ListResult containing items and pagination info.

        Example::

            async def get_list(
                self,
                page: int = 1,
                page_size: int = 25,
                **kwargs,
            ) -> ListResult:
                # Fetch from database, API, file, etc.
                items = await fetch_from_source(page, page_size)
                total = await count_items()
                return ListResult(items=items, total=total, page=page, page_size=page_size)
        """
        ...

    @abstractmethod
    async def get_one(self, item_id: str) -> dict[str, Any] | None:
        """Retrieve a single item by its identifier.

        This method must be implemented by subclasses to fetch a single
        item from the custom data source.

        Args:
            item_id: The unique identifier for the item.

        Returns:
            Item data as a dictionary, or None if not found.

        Example::

            async def get_one(self, item_id: str) -> dict[str, Any] | None:
                for item in self.data:
                    if str(item["id"]) == item_id:
                        return item
                return None
        """
        ...

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new item.

        Override this method to implement create functionality.
        By default, raises NotImplementedError.

        Args:
            data: Dictionary of field values for the new item.

        Returns:
            The created item data including any generated fields.

        Raises:
            NotImplementedError: If create is not supported.

        Example::

            async def create(self, data: dict[str, Any]) -> dict[str, Any]:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api.example.com/users",
                        json=data,
                    )
                    return response.json()
        """
        msg = f"{self.__class__.__name__} does not support create operations"
        raise NotImplementedError(msg)

    async def update(self, item_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing item.

        Override this method to implement update functionality.
        By default, raises NotImplementedError.

        Args:
            item_id: The unique identifier for the item.
            data: Dictionary of field values to update.

        Returns:
            The updated item data.

        Raises:
            NotImplementedError: If update is not supported.

        Example::

            async def update(self, item_id: str, data: dict[str, Any]) -> dict[str, Any]:
                async with httpx.AsyncClient() as client:
                    response = await client.patch(
                        f"https://api.example.com/users/{item_id}",
                        json=data,
                    )
                    return response.json()
        """
        msg = f"{self.__class__.__name__} does not support update operations"
        raise NotImplementedError(msg)

    async def delete(self, item_id: str) -> bool:
        """Delete an item.

        Override this method to implement delete functionality.
        By default, raises NotImplementedError.

        Args:
            item_id: The unique identifier for the item to delete.

        Returns:
            True if deletion was successful.

        Raises:
            NotImplementedError: If delete is not supported.

        Example::

            async def delete(self, item_id: str) -> bool:
                async with httpx.AsyncClient() as client:
                    response = await client.delete(f"https://api.example.com/users/{item_id}")
                    return response.status_code == 204
        """
        msg = f"{self.__class__.__name__} does not support delete operations"
        raise NotImplementedError(msg)

    @classmethod
    async def can_create_item(cls, connection: ASGIConnection) -> bool:
        """Check if an item can be created.

        Args:
            connection: The current ASGI connection.

        Returns:
            True if creation is allowed.
        """
        return cls.can_create and await cls.is_accessible(connection)

    @classmethod
    async def can_edit_item(
        cls,
        connection: ASGIConnection,
        item: dict[str, Any],  # noqa: ARG003
    ) -> bool:
        """Check if a specific item can be edited.

        Args:
            connection: The current ASGI connection.
            item: The item data to check.

        Returns:
            True if editing is allowed.
        """
        return cls.can_edit and await cls.is_accessible(connection)

    @classmethod
    async def can_delete_item(
        cls,
        connection: ASGIConnection,
        item: dict[str, Any],  # noqa: ARG003
    ) -> bool:
        """Check if a specific item can be deleted.

        Args:
            connection: The current ASGI connection.
            item: The item data to check.

        Returns:
            True if deletion is allowed.
        """
        return cls.can_delete and await cls.is_accessible(connection)

    async def on_before_create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Hook called before creating an item.

        Override to modify data before create or perform validation.

        Args:
            data: The data being created.

        Returns:
            The (possibly modified) data to create.
        """
        return data

    async def on_after_create(self, item: dict[str, Any]) -> None:
        """Hook called after creating an item.

        Override to perform post-create actions.

        Args:
            item: The created item data.
        """

    async def on_before_update(
        self,
        item_id: str,  # noqa: ARG002
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Hook called before updating an item.

        Override to modify data before update or perform validation.

        Args:
            item_id: The identifier of the item being updated.
            data: The update data.

        Returns:
            The (possibly modified) data to update.
        """
        return data

    async def on_after_update(self, item: dict[str, Any]) -> None:
        """Hook called after updating an item.

        Override to perform post-update actions.

        Args:
            item: The updated item data.
        """

    async def on_before_delete(self, item_id: str) -> None:
        """Hook called before deleting an item.

        Override to perform pre-delete actions or validation.

        Args:
            item_id: The identifier of the item being deleted.
        """

    async def on_after_delete(self, item_id: str) -> None:
        """Hook called after deleting an item.

        Override to perform post-delete actions.

        Args:
            item_id: The identifier of the deleted item.
        """

    @classmethod
    def _get_normalized_columns(cls) -> list[ColumnDefinition]:
        """Get columns as ColumnDefinition objects.

        This method returns the columns list after normalization (which
        happens in __init_subclass__). At runtime, all columns are
        guaranteed to be ColumnDefinition instances.

        Returns:
            List of ColumnDefinition objects.
        """
        # After __init_subclass__, all columns are ColumnDefinition instances
        return cast("list[ColumnDefinition]", cls.columns)

    @classmethod
    def get_list_columns(cls) -> list[ColumnDefinition]:
        """Get columns to display in list view.

        Returns:
            List of visible ColumnDefinition objects.
        """
        return [col for col in cls._get_normalized_columns() if col.visible]

    @classmethod
    def get_searchable_columns(cls) -> list[ColumnDefinition]:
        """Get columns that are searchable.

        Returns:
            List of searchable ColumnDefinition objects.
        """
        return [col for col in cls._get_normalized_columns() if col.searchable]

    @classmethod
    def get_sortable_columns(cls) -> list[ColumnDefinition]:
        """Get columns that are sortable.

        Returns:
            List of sortable ColumnDefinition objects.
        """
        return [col for col in cls._get_normalized_columns() if col.sortable]

    @classmethod
    def get_filterable_columns(cls) -> list[ColumnDefinition]:
        """Get columns that are filterable.

        Returns:
            List of filterable ColumnDefinition objects.
        """
        return [col for col in cls._get_normalized_columns() if col.filterable]

    @classmethod
    def get_column_by_name(cls, name: str) -> ColumnDefinition | None:
        """Get a column definition by name.

        Args:
            name: The column name to find.

        Returns:
            The ColumnDefinition if found, None otherwise.
        """
        for col in cls._get_normalized_columns():
            if col.name == name:
                return col
        return None

    @classmethod
    def get_schema(cls) -> dict[str, Any]:
        """Generate a JSON Schema for this view's data structure.

        Returns:
            JSON Schema dictionary describing the item structure.

        Example::

            {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "email": {"type": "string", "format": "email"},
                    "name": {"type": "string"},
                },
                "required": ["id", "email"],
            }
        """
        type_mapping = {
            "string": "string",
            "integer": "integer",
            "float": "number",
            "boolean": "boolean",
            "datetime": "string",
            "date": "string",
            "time": "string",
            "json": "object",
            "text": "string",
            "email": "string",
            "url": "string",
            "uuid": "string",
        }

        format_mapping = {
            "datetime": "date-time",
            "date": "date",
            "time": "time",
            "email": "email",
            "url": "uri",
            "uuid": "uuid",
        }

        properties: dict[str, Any] = {}
        for col in cls._get_normalized_columns():
            prop: dict[str, Any] = {"type": type_mapping.get(col.type, "string")}
            if col.type in format_mapping:
                prop["format"] = format_mapping[col.type]
            properties[col.name] = prop

        return {
            "type": "object",
            "properties": properties,
        }

    @classmethod
    def get_api_routes(cls) -> list[dict[str, Any]]:
        """Return API route definitions for this custom view.

        Returns:
            List of route definitions for CRUD operations.
        """
        base_path = f"/api/custom/{cls.identity}"
        routes = [
            {
                "path": base_path,
                "methods": ["GET"],
                "operation": "list",
                "name": f"{cls.identity}-list",
            },
            {
                "path": f"{base_path}/{{{cls.pk_field}:str}}",
                "methods": ["GET"],
                "operation": "get",
                "name": f"{cls.identity}-get",
            },
        ]

        if cls.can_create:
            routes.append(
                {
                    "path": base_path,
                    "methods": ["POST"],
                    "operation": "create",
                    "name": f"{cls.identity}-create",
                }
            )

        if cls.can_edit:
            routes.append(
                {
                    "path": f"{base_path}/{{{cls.pk_field}:str}}",
                    "methods": ["PUT", "PATCH"],
                    "operation": "update",
                    "name": f"{cls.identity}-update",
                }
            )

        if cls.can_delete:
            routes.append(
                {
                    "path": f"{base_path}/{{{cls.pk_field}:str}}",
                    "methods": ["DELETE"],
                    "operation": "delete",
                    "name": f"{cls.identity}-delete",
                }
            )

        return routes

    @classmethod
    def get_navigation_info(cls) -> dict[str, Any]:
        """Return navigation metadata for the sidebar.

        Extends the base navigation info with custom view specific data.

        Returns:
            Dictionary with navigation and capability information.
        """
        info = super().get_navigation_info()
        info.update(
            {
                "pk_field": cls.pk_field,
                "can_create": cls.can_create,
                "can_edit": cls.can_edit,
                "can_delete": cls.can_delete,
                "can_view_details": cls.can_view_details,
                "can_export": cls.can_export,
            }
        )
        return info
