"""JSON file data provider for CustomView.

This module provides a JSONFileView class that reads and writes data
to JSON files, providing simple file-based persistence.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, ClassVar, Literal

from litestar_admin.views.custom import CustomView, ListResult

__all__ = ["JSONFileView"]


class JSONFileView(CustomView):
    """CustomView backed by a JSON file.

    This view reads and writes data to a JSON file, providing simple
    file-based persistence suitable for:
    - Configuration files
    - Small datasets
    - Development and testing
    - Single-server deployments

    Note:
        This implementation uses synchronous file I/O wrapped in async.
        For high-concurrency scenarios, consider using aiofiles or
        a proper database.

    Attributes:
        file_path: Path to the JSON file (must be set by subclass).
        auto_generate_pk: Whether to auto-generate UUID primary keys on create.
        create_file_if_missing: Whether to create the file if it doesn't exist.
        indent: JSON indentation for pretty-printing (None for compact).

    Example::

        class BookmarksView(JSONFileView):
            name = "Bookmarks"
            icon = "bookmark"
            file_path = "/data/bookmarks.json"
            can_create = True
            can_edit = True
            can_delete = True

            columns = [
                ColumnDefinition(name="id", type="uuid"),
                ColumnDefinition(name="title", type="string", sortable=True, searchable=True),
                ColumnDefinition(name="url", type="url"),
                ColumnDefinition(name="tags", type="json"),
                ColumnDefinition(name="created_at", type="datetime"),
            ]
    """

    # Path to the JSON file (must be set by subclass)
    file_path: ClassVar[str | Path] = ""

    # Whether to auto-generate UUID primary keys on create
    auto_generate_pk: ClassVar[bool] = True

    # Whether to create the file if it doesn't exist
    create_file_if_missing: ClassVar[bool] = True

    # JSON indentation (None for compact output)
    indent: ClassVar[int | None] = 2

    # Enable CRUD by default
    can_create: ClassVar[bool] = True
    can_edit: ClassVar[bool] = True
    can_delete: ClassVar[bool] = True

    @classmethod
    def _get_file_path(cls) -> Path:
        """Get the file path as a Path object.

        Returns:
            Path object for the JSON file.

        Raises:
            ValueError: If file_path is not set.
        """
        if not cls.file_path:
            msg = f"{cls.__name__} must define 'file_path' class attribute"
            raise ValueError(msg)
        return Path(cls.file_path)

    @classmethod
    def _read_data(cls) -> list[dict[str, Any]]:
        """Read data from the JSON file.

        Returns:
            List of item dictionaries from the file.
        """
        path = cls._get_file_path()

        if not path.exists():
            if cls.create_file_if_missing:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("[]")
                return []
            msg = f"JSON file not found: {path}"
            raise FileNotFoundError(msg)

        content = path.read_text(encoding="utf-8")
        if not content.strip():
            return []

        data = json.loads(content)

        # Handle both list and dict formats
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            # Assume dict values are items
            return list(data.values())

        return []

    @classmethod
    def _write_data(cls, items: list[dict[str, Any]]) -> None:
        """Write data to the JSON file.

        Args:
            items: List of item dictionaries to write.
        """
        path = cls._get_file_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(items, indent=cls.indent, default=str),
            encoding="utf-8",
        )

    def _build_index(self, items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        """Build an index of items by primary key.

        Args:
            items: List of item dictionaries.

        Returns:
            Dictionary mapping primary key values to items.
        """
        return {str(item.get(self.pk_field, "")): item for item in items if item.get(self.pk_field)}

    async def get_list(
        self,
        page: int = 1,
        page_size: int = 25,
        filters: dict[str, Any] | None = None,
        sort_by: str | None = None,
        sort_order: Literal["asc", "desc"] = "asc",
        search: str | None = None,
    ) -> ListResult:
        """Retrieve a paginated list of items from the JSON file.

        Args:
            page: Page number (1-indexed).
            page_size: Number of items per page.
            filters: Dictionary of filter field names to values.
            sort_by: Field name to sort by.
            sort_order: Sort direction ("asc" or "desc").
            search: Search query string.

        Returns:
            ListResult containing items and pagination info.
        """
        items = self._read_data()

        # Apply search filter
        if search:
            search_lower = search.lower()
            searchable_cols = self.get_searchable_columns()
            if searchable_cols:
                items = [
                    item
                    for item in items
                    if any(search_lower in str(item.get(col.name, "")).lower() for col in searchable_cols)
                ]

        # Apply filters
        if filters:
            for field, value in filters.items():
                items = [item for item in items if item.get(field) == value]

        # Sort items
        if sort_by:
            reverse = sort_order == "desc"
            items = sorted(
                items,
                key=lambda x: (x.get(sort_by) is None, x.get(sort_by, "")),
                reverse=reverse,
            )

        # Calculate pagination
        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_items = items[start:end]

        return ListResult(
            items=paginated_items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_one(self, item_id: str) -> dict[str, Any] | None:
        """Retrieve a single item by its identifier.

        Args:
            item_id: The unique identifier for the item.

        Returns:
            Item data as a dictionary, or None if not found.
        """
        items = self._read_data()
        index = self._build_index(items)
        return index.get(item_id)

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new item in the JSON file.

        Args:
            data: Dictionary of field values for the new item.

        Returns:
            The created item data including any generated fields.

        Raises:
            ValueError: If an item with the same primary key already exists.
        """
        # Call pre-create hook
        data = await self.on_before_create(data)

        items = self._read_data()
        index = self._build_index(items)
        pk_field = self.pk_field

        # Auto-generate primary key if not provided
        if pk_field not in data or not data[pk_field]:
            if self.auto_generate_pk:
                data[pk_field] = str(uuid.uuid4())
            else:
                msg = f"Primary key field '{pk_field}' is required"
                raise ValueError(msg)

        item_id = str(data[pk_field])

        # Check for duplicate
        if item_id in index:
            msg = f"Item with {pk_field}='{item_id}' already exists"
            raise ValueError(msg)

        # Add and save
        items.append(data.copy())
        self._write_data(items)

        # Call post-create hook
        await self.on_after_create(data)

        return data

    async def update(self, item_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing item in the JSON file.

        Args:
            item_id: The unique identifier for the item.
            data: Dictionary of field values to update.

        Returns:
            The updated item data.

        Raises:
            KeyError: If the item does not exist.
        """
        items = self._read_data()
        pk_field = self.pk_field

        # Find the item index
        item_index = None
        for i, item in enumerate(items):
            if str(item.get(pk_field, "")) == item_id:
                item_index = i
                break

        if item_index is None:
            msg = f"Item with {pk_field}='{item_id}' not found"
            raise KeyError(msg)

        # Call pre-update hook
        data = await self.on_before_update(item_id, data)

        # Update the item
        items[item_index].update(data)
        self._write_data(items)

        # Call post-update hook
        await self.on_after_update(items[item_index])

        return items[item_index]

    async def delete(self, item_id: str) -> bool:
        """Delete an item from the JSON file.

        Args:
            item_id: The unique identifier for the item to delete.

        Returns:
            True if deletion was successful.

        Raises:
            KeyError: If the item does not exist.
        """
        items = self._read_data()
        pk_field = self.pk_field

        # Find the item index
        item_index = None
        for i, item in enumerate(items):
            if str(item.get(pk_field, "")) == item_id:
                item_index = i
                break

        if item_index is None:
            msg = f"Item with {pk_field}='{item_id}' not found"
            raise KeyError(msg)

        # Call pre-delete hook
        await self.on_before_delete(item_id)

        # Delete and save
        del items[item_index]
        self._write_data(items)

        # Call post-delete hook
        await self.on_after_delete(item_id)

        return True
