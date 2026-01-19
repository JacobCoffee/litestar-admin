"""In-memory data provider for CustomView.

This module provides an InMemoryView class that stores data in memory,
useful for settings, configuration, caching, or testing scenarios.
"""

from __future__ import annotations

import uuid
from typing import Any, ClassVar, Literal

from litestar_admin.views.custom import CustomView, ListResult

__all__ = ["InMemoryView"]


class InMemoryView(CustomView):
    """CustomView backed by an in-memory data store.

    This view stores all data in a class-level dictionary, making it
    suitable for:
    - Application settings and configuration
    - Cached data from external sources
    - Testing and prototyping
    - Small datasets that don't need persistence

    Note:
        Data is lost when the application restarts. For persistence,
        use JSONFileView or implement your own storage backend.

    Attributes:
        _data: Class-level dictionary storing items keyed by primary key.
        auto_generate_pk: Whether to auto-generate UUID primary keys on create.

    Example::

        class AppSettingsView(InMemoryView):
            name = "App Settings"
            icon = "settings"
            pk_field = "key"
            can_create = True
            can_edit = True
            can_delete = True

            columns = [
                ColumnDefinition(name="key", type="string", sortable=True),
                ColumnDefinition(name="value", type="string"),
                ColumnDefinition(name="description", type="text"),
            ]

            # Pre-populate with default settings
            _data = {
                "site_name": {
                    "key": "site_name",
                    "value": "My Application",
                    "description": "The name displayed in the header",
                },
                "maintenance_mode": {
                    "key": "maintenance_mode",
                    "value": "false",
                    "description": "Enable maintenance mode",
                },
            }
    """

    # Storage for items - keyed by primary key value
    _data: ClassVar[dict[str, dict[str, Any]]] = {}

    # Whether to auto-generate UUID primary keys on create
    auto_generate_pk: ClassVar[bool] = True

    # Enable CRUD by default for in-memory views
    can_create: ClassVar[bool] = True
    can_edit: ClassVar[bool] = True
    can_delete: ClassVar[bool] = True

    async def get_list(
        self,
        page: int = 1,
        page_size: int = 25,
        filters: dict[str, Any] | None = None,
        sort_by: str | None = None,
        sort_order: Literal["asc", "desc"] = "asc",
        search: str | None = None,
    ) -> ListResult:
        """Retrieve a paginated list of items from memory.

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
        items = list(self._data.values())

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
        return self._data.get(item_id)

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new item in the in-memory store.

        Args:
            data: Dictionary of field values for the new item.

        Returns:
            The created item data including any generated fields.

        Raises:
            ValueError: If an item with the same primary key already exists.
        """
        # Call pre-create hook
        data = await self.on_before_create(data)

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
        if item_id in self._data:
            msg = f"Item with {pk_field}='{item_id}' already exists"
            raise ValueError(msg)

        # Store the item
        self._data[item_id] = data.copy()

        # Call post-create hook
        await self.on_after_create(self._data[item_id])

        return self._data[item_id]

    async def update(self, item_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing item in the in-memory store.

        Args:
            item_id: The unique identifier for the item.
            data: Dictionary of field values to update.

        Returns:
            The updated item data.

        Raises:
            KeyError: If the item does not exist.
        """
        if item_id not in self._data:
            msg = f"Item with id='{item_id}' not found"
            raise KeyError(msg)

        # Call pre-update hook
        data = await self.on_before_update(item_id, data)

        # Update the item (merge with existing data)
        self._data[item_id].update(data)

        # Call post-update hook
        await self.on_after_update(self._data[item_id])

        return self._data[item_id]

    async def delete(self, item_id: str) -> bool:
        """Delete an item from the in-memory store.

        Args:
            item_id: The unique identifier for the item to delete.

        Returns:
            True if deletion was successful.

        Raises:
            KeyError: If the item does not exist.
        """
        if item_id not in self._data:
            msg = f"Item with id='{item_id}' not found"
            raise KeyError(msg)

        # Call pre-delete hook
        await self.on_before_delete(item_id)

        # Delete the item
        del self._data[item_id]

        # Call post-delete hook
        await self.on_after_delete(item_id)

        return True

    @classmethod
    def clear_data(cls) -> None:
        """Clear all data from the in-memory store.

        Useful for testing or resetting the store.
        """
        cls._data.clear()

    @classmethod
    def seed_data(cls, items: list[dict[str, Any]]) -> None:
        """Seed the in-memory store with initial data.

        Args:
            items: List of item dictionaries to add.
                   Each item must have a value for the pk_field.

        Example::

            SettingsView.seed_data(
                [
                    {"key": "theme", "value": "dark"},
                    {"key": "language", "value": "en"},
                ]
            )
        """
        for item in items:
            pk_value = str(item.get(cls.pk_field, ""))
            if pk_value:
                cls._data[pk_value] = item.copy()
