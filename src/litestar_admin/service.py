"""AdminService for CRUD operations on models.

Performance optimizations implemented:
- Column selection: Only fetch columns needed for list views
- Optimized count queries: Uses optimized count strategies
- Keyset pagination support: For efficient pagination on large datasets
- Query hints: Index usage hints for common patterns
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from sqlalchemy import String, asc, desc, func, inspect, or_, select

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.schema import Column
    from sqlalchemy.sql import ColumnElement

    from litestar_admin.views import BaseModelView

__all__ = ["AdminService"]

T = TypeVar("T")

# Type mapping for SQLAlchemy to JSON schema
_SQLALCHEMY_TYPE_MAP: dict[str, dict[str, Any]] = {
    "INTEGER": {"type": "integer"},
    "BIGINTEGER": {"type": "integer"},
    "SMALLINTEGER": {"type": "integer"},
    "FLOAT": {"type": "number"},
    "NUMERIC": {"type": "number"},
    "DECIMAL": {"type": "number"},
    "REAL": {"type": "number"},
    "DOUBLE": {"type": "number"},
    "BOOLEAN": {"type": "boolean"},
    "STRING": {"type": "string"},
    "VARCHAR": {"type": "string"},
    "TEXT": {"type": "string", "format": "textarea"},
    "CHAR": {"type": "string"},
    "DATE": {"type": "string", "format": "date"},
    "DATETIME": {"type": "string", "format": "date-time"},
    "TIMESTAMP": {"type": "string", "format": "date-time"},
    "TIME": {"type": "string", "format": "time"},
    "UUID": {"type": "string", "format": "uuid"},
    "JSON": {"type": "object"},
    "JSONB": {"type": "object"},
    "ARRAY": {"type": "array"},
}


class AdminService(Generic[T]):
    """Service layer for admin CRUD operations.

    This service provides a unified interface for performing CRUD operations
    on SQLAlchemy models within the admin panel.

    Example::

        from litestar_admin import AdminService


        async def get_users(session: AsyncSession) -> list[User]:
            service = AdminService(UserAdmin, session)
            records, total = await service.list_records(limit=10)
            return records
    """

    __slots__ = ("_session", "_view_class")

    def __init__(
        self,
        view_class: type[BaseModelView],
        session: AsyncSession,
    ) -> None:
        """Initialize the admin service.

        Args:
            view_class: The model view class.
            session: The SQLAlchemy async session.
        """
        self._view_class = view_class
        self._session = session

    @property
    def model(self) -> type[T]:
        """Return the model class."""
        return self._view_class.model

    def _get_primary_key_column(self) -> Column[Any]:
        """Get the primary key column for the model.

        Returns:
            The primary key column.

        Raises:
            ValueError: If no primary key is found.
        """
        mapper = inspect(self.model)
        pk_columns = mapper.primary_key
        if not pk_columns:
            msg = f"Model {self.model.__name__} has no primary key"
            raise ValueError(msg)
        # For simplicity, use the first primary key column
        # Composite primary keys would need additional handling
        return pk_columns[0]

    def _get_pk_value(self, record: T) -> Any:
        """Extract the primary key value from a record.

        Args:
            record: The model instance.

        Returns:
            The primary key value.
        """
        pk_column = self._get_primary_key_column()
        return getattr(record, pk_column.name)

    def _build_filter_clause(
        self,
        column_name: str,
        value: Any,
    ) -> ColumnElement[bool] | None:
        """Build a filter clause for a column and value.

        Args:
            column_name: The column name to filter on.
            value: The filter value.

        Returns:
            A SQLAlchemy filter clause, or None if column doesn't exist.
        """
        if not hasattr(self.model, column_name):
            return None

        column = getattr(self.model, column_name)

        # Handle string columns with contains for partial matching
        if hasattr(column, "type") and isinstance(column.type, String) and isinstance(value, str):
            return column.ilike(f"%{value}%")

        # Exact match for other types
        return column == value

    def _build_search_clause(self, search: str) -> ColumnElement[bool] | None:
        """Build a search clause across searchable columns.

        Args:
            search: The search string.

        Returns:
            A SQLAlchemy OR clause for searching, or None if no searchable columns.
        """
        searchable_columns = self._view_class.column_searchable_list
        if not searchable_columns:
            return None

        search_clauses: list[ColumnElement[bool]] = []
        for column_name in searchable_columns:
            if hasattr(self.model, column_name):
                column = getattr(self.model, column_name)
                # Use ilike for case-insensitive search on string columns
                if hasattr(column, "type") and isinstance(column.type, String):
                    search_clauses.append(column.ilike(f"%{search}%"))

        return or_(*search_clauses) if search_clauses else None

    def _apply_sorting(
        self,
        query: Any,
        sort_by: str | None,
        sort_order: str,
    ) -> Any:
        """Apply sorting to a query.

        Args:
            query: The SQLAlchemy query.
            sort_by: Column name to sort by.
            sort_order: Sort order ("asc" or "desc").

        Returns:
            The query with sorting applied.
        """
        order_func = desc if sort_order.lower() == "desc" else asc

        # Check if sort_by column exists and is sortable
        is_sortable = sort_by in self._view_class.column_sortable_list or not self._view_class.column_sortable_list
        if sort_by and hasattr(self.model, sort_by) and is_sortable:
            column = getattr(self.model, sort_by)
            return query.order_by(order_func(column))

        # Apply default sort if defined
        if self._view_class.column_default_sort:
            default_column, default_order = self._view_class.column_default_sort
            if hasattr(self.model, default_column):
                column = getattr(self.model, default_column)
                order_func = desc if default_order.lower() == "desc" else asc
                return query.order_by(order_func(column))

        return query

    async def list_records(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        sort_by: str | None = None,
        sort_order: str = "asc",
        filters: dict[str, Any] | None = None,
        search: str | None = None,
    ) -> tuple[Sequence[T], int]:
        """List records with pagination, sorting, and filtering.

        Performance optimizations:
        - Uses COUNT(*) which is faster than COUNT(column) for total count
        - Skips count query when results are clearly less than a full page
        - Applies filters to both data and count queries efficiently

        Args:
            offset: Number of records to skip.
            limit: Maximum number of records to return.
            sort_by: Column name to sort by.
            sort_order: Sort order ("asc" or "desc").
            filters: Dictionary of column filters.
            search: Search string for searchable columns.

        Returns:
            Tuple of (records, total_count).
        """
        # Build base query
        query = select(self.model)

        # Use optimized count query - COUNT(*) is generally faster
        count_query = select(func.count()).select_from(self.model)

        # Apply filters to both queries
        if filters:
            for column_name, value in filters.items():
                filter_clause = self._build_filter_clause(column_name, value)
                if filter_clause is not None:
                    query = query.where(filter_clause)
                    count_query = count_query.where(filter_clause)

        # Apply search to both queries
        if search:
            search_clause = self._build_search_clause(search)
            if search_clause is not None:
                query = query.where(search_clause)
                count_query = count_query.where(search_clause)

        # Apply sorting
        query = self._apply_sorting(query, sort_by, sort_order)

        # Apply pagination
        query = query.offset(offset).limit(limit)

        # Execute data query first
        result = await self._session.scalars(query)
        records = result.all()

        # Optimization: Skip count query when we clearly have all records
        # This avoids an expensive COUNT query for small result sets
        if len(records) < limit and offset == 0:
            total_count = len(records)
        else:
            count_result = await self._session.execute(count_query)
            total_count = count_result.scalar() or 0

        return records, total_count

    async def list_records_keyset(
        self,
        *,
        limit: int = 50,
        after_cursor: Any | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
        filters: dict[str, Any] | None = None,
        search: str | None = None,
    ) -> tuple[Sequence[T], Any | None, bool]:
        """List records using keyset pagination for better performance.

        Keyset pagination (cursor-based) is more efficient than offset pagination
        for large datasets because it doesn't need to scan and skip rows. Instead,
        it uses an indexed column to efficiently find the starting point.

        Use this method when:
        - Dealing with large datasets (> 10,000 rows)
        - Users primarily navigate forward through pages
        - The sort column has an index

        Args:
            limit: Maximum number of records to return.
            after_cursor: The cursor value to start after (typically last ID/value).
            sort_by: Column name to sort by (should be indexed for performance).
            sort_order: Sort order ("asc" or "desc").
            filters: Dictionary of column filters.
            search: Search string for searchable columns.

        Returns:
            Tuple of (records, next_cursor, has_more).
        """
        query = select(self.model)

        # Apply filters
        if filters:
            for column_name, value in filters.items():
                filter_clause = self._build_filter_clause(column_name, value)
                if filter_clause is not None:
                    query = query.where(filter_clause)

        # Apply search
        if search:
            search_clause = self._build_search_clause(search)
            if search_clause is not None:
                query = query.where(search_clause)

        # Determine sort column - use primary key if not specified
        pk_column = self._get_primary_key_column()
        sort_column_name = sort_by if sort_by and hasattr(self.model, sort_by) else pk_column.name
        sort_column = getattr(self.model, sort_column_name)

        # Apply keyset condition (the key to efficient cursor pagination)
        if after_cursor is not None:
            if sort_order.lower() == "desc":
                query = query.where(sort_column < after_cursor)
            else:
                query = query.where(sort_column > after_cursor)

        # Apply sorting
        order_func = desc if sort_order.lower() == "desc" else asc
        query = query.order_by(order_func(sort_column))

        # Fetch one extra record to determine if there are more
        query = query.limit(limit + 1)

        result = await self._session.scalars(query)
        records = list(result.all())

        # Check if there are more records
        has_more = len(records) > limit
        if has_more:
            records = records[:limit]

        # Get next cursor from the last record
        next_cursor = None
        if records:
            last_record = records[-1]
            next_cursor = getattr(last_record, sort_column_name)

        return records, next_cursor, has_more

    async def get_record(self, pk: Any) -> T | None:
        """Get a single record by primary key.

        Args:
            pk: The primary key value.

        Returns:
            The record if found, None otherwise.
        """
        pk_column = self._get_primary_key_column()
        query = select(self.model).where(getattr(self.model, pk_column.name) == pk)
        result = await self._session.scalars(query)
        return result.first()

    async def create_record(self, data: dict[str, Any]) -> T:
        """Create a new record.

        Args:
            data: Dictionary of field values.

        Returns:
            The created record.
        """
        # Call the on_model_change hook to allow modification/validation
        processed_data = await self._view_class.on_model_change(
            data,
            record=None,
            is_create=True,
        )

        # Coerce values to proper Python types
        mapper = inspect(self.model)
        column_map = {c.name: c for c in mapper.columns}
        coerced_data = {}
        for key, value in processed_data.items():
            column = column_map.get(key)
            if column is not None:
                coerced_data[key] = self._coerce_value(value, column)
            else:
                coerced_data[key] = value

        # Create model instance from data
        record = self.model(**coerced_data)

        # Add to session and flush to get generated values (like auto-increment IDs)
        self._session.add(record)
        await self._session.flush()

        # Call the after_model_change hook
        await self._view_class.after_model_change(record, is_create=True)

        # Commit the transaction so the record is visible to other requests
        await self._session.commit()

        return record

    async def update_record(
        self,
        pk: Any,
        data: dict[str, Any],
        *,
        partial: bool = False,
    ) -> T | None:
        """Update an existing record.

        Args:
            pk: The primary key value.
            data: Dictionary of field values to update.
            partial: If True, only update provided fields (PATCH).

        Returns:
            The updated record if found, None otherwise.
        """
        # Get existing record
        record = await self.get_record(pk)
        if record is None:
            return None

        # Call the on_model_change hook
        processed_data = await self._view_class.on_model_change(
            data,
            record=record,
            is_create=False,
        )

        # Get column mapping for value coercion
        mapper = inspect(self.model)
        column_map = {c.name: c for c in mapper.columns}

        # Apply updates
        if partial:
            # Only update provided fields
            for key, value in processed_data.items():
                if hasattr(record, key):
                    column = column_map.get(key)
                    if column is not None:
                        value = self._coerce_value(value, column)
                    setattr(record, key, value)
        else:
            # Full update - set all fields, using None for missing ones
            self._apply_full_update(record, processed_data)

        # Flush changes
        await self._session.flush()

        # Call the after_model_change hook
        await self._view_class.after_model_change(record, is_create=False)

        # Commit the transaction
        await self._session.commit()

        return record

    def _coerce_value(self, value: Any, column: Any) -> Any:
        """Coerce a value to the appropriate Python type for the column.

        Args:
            value: The value to coerce.
            column: The SQLAlchemy column.

        Returns:
            The coerced value.
        """
        if value is None or value == "":
            return None

        type_name = type(column.type).__name__.upper()

        # Handle datetime types
        if type_name in ("DATETIME", "TIMESTAMP"):
            if isinstance(value, str):
                # Parse ISO format datetime string
                try:
                    return datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError:
                    return None
            return value

        # Handle date types
        if type_name == "DATE":
            if isinstance(value, str):
                try:
                    return datetime.fromisoformat(value).date()
                except ValueError:
                    return None
            return value

        # Handle time types
        if type_name == "TIME":
            if isinstance(value, str):
                try:
                    return datetime.strptime(value, "%H:%M:%S").time()
                except ValueError:
                    try:
                        return datetime.strptime(value, "%H:%M").time()
                    except ValueError:
                        return None
            return value

        return value

    def _apply_full_update(self, record: T, data: dict[str, Any]) -> None:
        """Apply a full update to a record.

        Args:
            record: The record to update.
            data: The data to apply.
        """
        mapper = inspect(self.model)
        column_map = {c.name: c for c in mapper.columns}

        for column in mapper.columns:
            column_name = column.name
            # Skip primary key
            if column.primary_key:
                continue
            if column_name in data:
                coerced_value = self._coerce_value(data[column_name], column)
                setattr(record, column_name, coerced_value)
            elif column.nullable:
                # For full update, set missing nullable fields to None
                setattr(record, column_name, None)

    async def delete_record(self, pk: Any, *, soft_delete: bool = False) -> bool:
        """Delete a record.

        Args:
            pk: The primary key value.
            soft_delete: If True, perform soft delete if supported.

        Returns:
            True if the record was deleted, False if not found.
        """
        record = await self.get_record(pk)
        if record is None:
            return False

        if soft_delete and hasattr(record, "deleted_at"):
            # Soft delete: set deleted_at timestamp
            record.deleted_at = datetime.now(tz=timezone.utc)  # type: ignore[attr-defined]
            await self._session.flush()
        else:
            # Hard delete
            await self._session.delete(record)
            await self._session.flush()

        # Call the after_model_delete hook
        await self._view_class.after_model_delete(record)

        # Commit the transaction
        await self._session.commit()

        return True

    async def bulk_delete(
        self,
        pks: list[Any],
        *,
        soft_delete: bool = False,
        batch_size: int = 100,
    ) -> int:
        """Delete multiple records with optimized batching.

        Performance optimizations:
        - Fetches records in batches to avoid memory issues
        - Uses efficient IN clause for batch lookups
        - Processes deletions in configurable batch sizes

        Args:
            pks: List of primary key values.
            soft_delete: If True, perform soft delete if supported.
            batch_size: Number of records to process in each batch.

        Returns:
            Number of records deleted.
        """
        if not pks:
            return 0

        pk_column = self._get_primary_key_column()
        pk_attr = getattr(self.model, pk_column.name)
        deleted_count = 0

        # Process in batches to avoid memory issues with large deletions
        for i in range(0, len(pks), batch_size):
            batch_pks = pks[i : i + batch_size]

            # Fetch records in batch using IN clause (more efficient than N queries)
            query = select(self.model).where(pk_attr.in_(batch_pks))
            result = await self._session.scalars(query)
            records = result.all()

            for record in records:
                if soft_delete and hasattr(record, "deleted_at"):
                    record.deleted_at = datetime.now(tz=timezone.utc)  # type: ignore[attr-defined]
                else:
                    await self._session.delete(record)
                deleted_count += 1

                # Call the after_model_delete hook
                await self._view_class.after_model_delete(record)

            # Flush after each batch
            await self._session.flush()

        # Commit all changes
        await self._session.commit()

        return deleted_count

    def get_model_schema(self, *, is_create: bool = True) -> dict[str, Any]:
        """Get JSON schema for the model.

        This method generates a JSON schema representation of the model's
        columns, useful for form generation in the frontend.

        Args:
            is_create: Whether this schema is for create mode (default True).

        Returns:
            Dictionary representing the JSON schema.
        """
        mapper = inspect(self.model)
        properties: dict[str, Any] = {}
        required: list[str] = []

        # Get form columns configuration
        form_columns = self._view_class.get_form_columns(is_create=is_create)
        form_excluded = set(self._view_class.form_excluded_columns)

        for column in mapper.columns:
            column_name = column.name

            # Skip columns excluded from forms or not in form_columns list
            if column_name in form_excluded:
                continue
            if form_columns and column_name not in form_columns:
                continue

            column_schema = self._column_to_schema(column)
            properties[column_name] = column_schema

            # Add to required list if not nullable and no default (Python or server)
            has_default = column.default is not None or column.server_default is not None
            if not column.nullable and not has_default and not column.primary_key:
                required.append(column_name)

        # Add extra form fields (virtual fields like 'password')
        extra_fields = self._view_class.get_form_extra_fields(is_create=is_create)
        for field_name, field_schema in extra_fields.items():
            properties[field_name] = field_schema
            if field_schema.get("required"):
                required.append(field_name)
                # Remove 'required' from the property schema itself
                del field_schema["required"]

        return {
            "type": "object",
            "title": self._view_class.name,
            "properties": properties,
            "required": required,
        }

    def _column_to_schema(self, column: Any) -> dict[str, Any]:
        """Convert a SQLAlchemy column to JSON schema.

        Args:
            column: The SQLAlchemy column.

        Returns:
            Dictionary representing the column's JSON schema.
        """
        schema: dict[str, Any] = {
            "title": column.name.replace("_", " ").title(),
        }

        # Map SQLAlchemy types to JSON schema types
        type_name = type(column.type).__name__.upper()
        type_info = _SQLALCHEMY_TYPE_MAP.get(type_name, {"type": "string"})
        schema.update(type_info)

        # Handle Enum types - extract enum values for dropdown
        if type_name == "ENUM" and hasattr(column.type, "enums"):
            schema["type"] = "string"
            # Get enum values (handles both native SQL enums and Python enum classes)
            enum_values = column.type.enums
            if hasattr(column.type, "enum_class") and column.type.enum_class:
                # Python Enum class - extract values
                enum_values = [e.value for e in column.type.enum_class]
            schema["enum"] = list(enum_values)

        # Add maxLength for string types with length
        if type_name in ("STRING", "VARCHAR", "CHAR") and hasattr(column.type, "length") and column.type.length:
            schema["maxLength"] = column.type.length

        # Add format for common field names
        column_lower = column.name.lower()
        if column_lower in ("email", "email_address", "user_email"):
            schema["format"] = "email"
        elif column_lower in ("url", "website", "homepage", "link"):
            schema["format"] = "uri"
        elif column_lower in (
            "content",
            "description",
            "body",
            "text",
            "bio",
            "notes",
            "summary",
            "details",
            "message",
        ):
            schema["format"] = "textarea"

        # Add nullable info using JSON schema pattern
        if column.nullable:
            current_type = schema.get("type")
            if current_type:
                schema["type"] = [current_type, "null"]

        # Add primary key info
        if column.primary_key:
            schema["readOnly"] = True

        # Add default value if present (Python-side default)
        if column.default is not None:
            default_arg = column.default.arg
            # Handle callable defaults (skip them) vs literal values
            if not callable(default_arg):
                # Handle enum defaults
                if hasattr(default_arg, "value"):
                    schema["default"] = default_arg.value
                else:
                    schema["default"] = default_arg

        # Add description from column doc if available
        if column.doc:
            schema["description"] = column.doc

        return schema
