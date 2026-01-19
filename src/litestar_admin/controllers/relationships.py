"""RelationshipsController for FK autocomplete search endpoints."""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass, field
from typing import Any, ClassVar

from litestar import Controller, get
from litestar.exceptions import NotFoundException
from litestar.status_codes import HTTP_200_OK
from sqlalchemy import String, func, or_, select

# Litestar requires these imports at runtime for dependency injection type resolution
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from litestar_admin.registry import ModelRegistry  # noqa: TC001
from litestar_admin.relationships import get_relationship_detector

__all__ = [
    "RelationshipOption",
    "RelationshipSearchRequest",
    "RelationshipSearchResponse",
    "RelationshipsController",
]

_logger = logging.getLogger(__name__)


@dataclass
class RelationshipSearchRequest:
    """Request parameters for relationship search.

    Attributes:
        q: Search query string.
        limit: Maximum number of results to return.
        page: Page number for pagination (1-indexed).
    """

    q: str = ""
    limit: int = 20
    page: int = 1


@dataclass
class RelationshipOption:
    """A single option for a relationship autocomplete.

    Attributes:
        id: The primary key value of the related record.
        label: The display label for the record.
        data: Optional additional display data.
    """

    id: str | int
    label: str
    data: dict[str, Any] | None = None


@dataclass
class RelationshipSearchResponse:
    """Response for relationship search endpoints.

    Attributes:
        items: List of matching options.
        total: Total number of matching records.
        has_more: Whether there are more results available.
    """

    items: list[RelationshipOption] = field(default_factory=list)
    total: int = 0
    has_more: bool = False


def _serialize_pk(value: Any) -> str | int:
    """Serialize a primary key value to a JSON-compatible type.

    Args:
        value: The primary key value.

    Returns:
        The serialized primary key.
    """
    from uuid import UUID

    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, int):
        return value
    return str(value)


def _get_label_value(record: Any, display_column: str) -> str:
    """Get the display label from a record.

    Args:
        record: The database record.
        display_column: The column name to use for display.

    Returns:
        The string label for the record.
    """
    value = getattr(record, display_column, None)
    if value is None:
        # Fall back to string representation
        return str(record)
    return str(value)


def _build_search_clauses(
    related_model: type[Any],
    search_fields: list[str],
    query_string: str,
) -> list[Any]:
    """Build search clauses for the given fields.

    Args:
        related_model: The related model class.
        search_fields: List of field names to search.
        query_string: The search query string.

    Returns:
        List of SQLAlchemy filter clauses.
    """
    search_clauses = []

    for search_field in search_fields:
        if not hasattr(related_model, search_field):
            continue

        column = getattr(related_model, search_field)
        # Use ilike for case-insensitive search on string columns
        if hasattr(column, "type") and isinstance(column.type, String):
            search_clauses.append(column.ilike(f"%{query_string}%"))
        else:
            # Try exact match for non-string columns (like ID)
            with contextlib.suppress(Exception):
                search_clauses.append(column == query_string)

    return search_clauses


class RelationshipsController(Controller):
    """Controller for relationship autocomplete search endpoints.

    Provides REST API endpoints for searching and resolving related model
    options for FK/relationship fields in the admin panel.

    Example:
        The controller is automatically registered by AdminPlugin.
        Access endpoints at:
        - GET /admin/api/models/{model_name}/relationships/{field_name}/search
        - GET /admin/api/models/{model_name}/relationships/{field_name}/options
    """

    path = "/api/models/{model_name:str}/relationships/{field_name:str}"
    tags: ClassVar[list[str]] = ["Relationships"]

    @get(
        "/search",
        status_code=HTTP_200_OK,
        summary="Search related records",
        description="Search related records for autocomplete in FK/relationship fields.",
    )
    async def search_relationships(
        self,
        model_name: str,
        field_name: str,
        admin_registry: ModelRegistry,
        db_session: AsyncSession,
        q: str = "",
        limit: int = 20,
        page: int = 1,
    ) -> RelationshipSearchResponse:
        """Search related records for a relationship field.

        This endpoint enables autocomplete functionality for FK and relationship
        fields by searching related model records.

        Args:
            model_name: The name of the source model.
            field_name: The relationship field name.
            admin_registry: The model registry.
            db_session: The database session.
            q: Search query string.
            limit: Maximum number of results (max 100).
            page: Page number (1-indexed).

        Returns:
            Search response with matching options.

        Raises:
            NotFoundException: If the model or relationship is not found.
        """
        # Validate and cap parameters
        limit = min(max(1, limit), 100)
        page = max(1, page)
        offset = (page - 1) * limit

        # Get the source view and validate relationship
        view_class, rel_info = _get_view_and_relationship(admin_registry, model_name, field_name)

        # Get the related model and its display column
        related_model = rel_info.related_model
        detector = get_relationship_detector()
        display_column = detector.get_display_column(related_model)

        # Get primary key column for the related model
        pk_column = _get_pk_column(related_model)

        # Build search query
        query = select(related_model)
        count_query = select(func.count()).select_from(related_model)

        # Apply search if query string provided
        if q:
            search_fields = _get_relationship_search_fields(view_class, field_name, related_model, display_column)
            search_clauses = _build_search_clauses(related_model, search_fields, q)

            if search_clauses:
                search_filter = or_(*search_clauses)
                query = query.where(search_filter)
                count_query = count_query.where(search_filter)

        # Apply ordering - show most relevant first (by display column)
        if hasattr(related_model, display_column):
            query = query.order_by(getattr(related_model, display_column))

        # Apply pagination
        query = query.offset(offset).limit(limit)

        # Execute queries
        result = await db_session.scalars(query)
        records = result.all()

        # Optimize count query
        if len(records) < limit and offset == 0:
            total = len(records)
        else:
            count_result = await db_session.execute(count_query)
            total = count_result.scalar() or 0

        # Build response
        items = [
            RelationshipOption(
                id=_serialize_pk(getattr(record, pk_column.name)),
                label=_get_label_value(record, display_column),
                data=_get_additional_data(record, view_class, field_name),
            )
            for record in records
        ]

        has_more = (offset + len(records)) < total

        return RelationshipSearchResponse(
            items=items,
            total=total,
            has_more=has_more,
        )

    @get(
        "/options",
        status_code=HTTP_200_OK,
        summary="Get options by IDs",
        description="Resolve specific related records by their IDs for display.",
    )
    async def get_relationship_options(
        self,
        model_name: str,
        field_name: str,
        admin_registry: ModelRegistry,
        db_session: AsyncSession,
        ids: str = "",
    ) -> RelationshipSearchResponse:
        """Get specific related records by their IDs.

        This endpoint resolves a list of IDs to their display labels,
        useful for populating existing FK values in forms.

        Args:
            model_name: The name of the source model.
            field_name: The relationship field name.
            admin_registry: The model registry.
            db_session: The database session.
            ids: Comma-separated list of IDs to resolve.

        Returns:
            Response with resolved options.

        Raises:
            NotFoundException: If the model or relationship is not found.
        """
        # Get the source view and validate relationship
        view_class, rel_info = _get_view_and_relationship(admin_registry, model_name, field_name)

        # Parse IDs
        if not ids or not ids.strip():
            return RelationshipSearchResponse(items=[], total=0, has_more=False)

        id_list = [id_str.strip() for id_str in ids.split(",") if id_str.strip()]
        if not id_list:
            return RelationshipSearchResponse(items=[], total=0, has_more=False)

        # Get the related model and its display column
        related_model = rel_info.related_model
        detector = get_relationship_detector()
        display_column = detector.get_display_column(related_model)

        # Get primary key column for the related model
        pk_column = _get_pk_column(related_model)
        pk_attr = getattr(related_model, pk_column.name)

        # Convert IDs to appropriate types
        converted_ids = _convert_ids(id_list, pk_column)

        # Query for the specific records
        query = select(related_model).where(pk_attr.in_(converted_ids))
        result = await db_session.scalars(query)
        records = result.all()

        # Build response maintaining order of requested IDs
        record_map = {_serialize_pk(getattr(r, pk_column.name)): r for r in records}
        items = []
        for id_val in id_list:
            # Try both string and original form
            record = record_map.get(id_val) or record_map.get(int(id_val) if id_val.isdigit() else id_val)
            if record is not None:
                items.append(
                    RelationshipOption(
                        id=_serialize_pk(getattr(record, pk_column.name)),
                        label=_get_label_value(record, display_column),
                        data=_get_additional_data(record, view_class, field_name),
                    )
                )

        return RelationshipSearchResponse(
            items=items,
            total=len(items),
            has_more=False,
        )


def _get_view_and_relationship(
    admin_registry: ModelRegistry,
    model_name: str,
    field_name: str,
) -> tuple[type[Any], Any]:
    """Get view class and relationship info for validation.

    Args:
        admin_registry: The model registry.
        model_name: The name of the source model.
        field_name: The relationship field name (or FK column name).

    Returns:
        Tuple of (view_class, rel_info).

    Raises:
        NotFoundException: If the model or relationship is not found.
    """
    try:
        view_class = admin_registry.get_view_by_name(model_name)
    except KeyError as exc:
        raise NotFoundException(f"Model '{model_name}' not found") from exc

    # Use flexible lookup to support both relationship names and FK column names
    detector = get_relationship_detector()
    rel_info = detector.get_relationship_info_flexible(view_class.model, field_name)
    if rel_info is None:
        raise NotFoundException(f"Relationship '{field_name}' not found on model '{model_name}'")

    return view_class, rel_info


def _get_pk_column(related_model: type[Any]) -> Any:
    """Get the primary key column for a related model.

    Args:
        related_model: The related model class.

    Returns:
        The primary key column.

    Raises:
        NotFoundException: If the related model has no primary key.
    """
    from sqlalchemy import inspect as sa_inspect

    mapper = sa_inspect(related_model)
    pk_columns = mapper.primary_key
    if not pk_columns:
        raise NotFoundException(f"Related model '{related_model.__name__}' has no primary key")
    return pk_columns[0]


def _get_relationship_search_fields(
    view_class: type[Any],
    field_name: str,
    related_model: type[Any],
    display_column: str,
) -> list[str]:
    """Get the search fields for a relationship.

    This function determines which fields to search when performing
    autocomplete on a relationship field.

    Args:
        view_class: The source model's view class.
        field_name: The relationship field name.
        related_model: The related model class.
        display_column: The default display column.

    Returns:
        List of field names to search.
    """
    # Check for custom search fields configuration on the view
    relationship_search_fields = getattr(view_class, "relationship_search_fields", {})

    if field_name in relationship_search_fields:
        return relationship_search_fields[field_name]

    # Default: search the display column and the primary key
    from sqlalchemy import inspect as sa_inspect

    search_fields = [display_column]

    try:
        mapper = sa_inspect(related_model)
        pk_name = mapper.primary_key[0].name
        if pk_name != display_column:
            search_fields.append(pk_name)
    except Exception:
        _logger.debug("Could not get primary key for %s", related_model.__name__)

    return search_fields


def _convert_ids(id_list: list[str], pk_column: Any) -> list[Any]:
    """Convert string IDs to the appropriate type for the primary key column.

    Args:
        id_list: List of string IDs.
        pk_column: The SQLAlchemy primary key column.

    Returns:
        List of converted IDs.
    """
    from uuid import UUID

    type_name = type(pk_column.type).__name__.upper()

    # Determine conversion function based on type
    def convert_single(id_str: str) -> Any:
        try:
            if type_name in ("INTEGER", "BIGINTEGER", "SMALLINTEGER"):
                return int(id_str)
            if type_name == "UUID":
                return UUID(id_str)
            return id_str
        except (ValueError, TypeError):
            return id_str

    return [convert_single(id_str) for id_str in id_list]


def _get_additional_data(
    record: Any,
    view_class: type[Any],
    field_name: str,
) -> dict[str, Any] | None:
    """Get additional display data for a related record.

    This function allows views to configure additional fields to include
    in the autocomplete response.

    Args:
        record: The database record.
        view_class: The source model's view class.
        field_name: The relationship field name.

    Returns:
        Dictionary of additional data, or None if not configured.
    """
    # Check for custom additional data configuration
    relationship_display_fields = getattr(view_class, "relationship_display_fields", {})

    if field_name not in relationship_display_fields:
        return None

    additional_fields = relationship_display_fields[field_name]
    data = {}

    for field_to_include in additional_fields:
        if hasattr(record, field_to_include):
            value = getattr(record, field_to_include)
            # Serialize common non-JSON types
            if value is not None:
                value = _serialize_value(value)
            data[field_to_include] = value

    return data if data else None


def _serialize_value(value: Any) -> Any:
    """Serialize a value to a JSON-compatible type.

    Args:
        value: The value to serialize.

    Returns:
        The serialized value.
    """
    from datetime import date, datetime
    from decimal import Decimal
    from uuid import UUID

    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, UUID):
        return str(value)
    return value
