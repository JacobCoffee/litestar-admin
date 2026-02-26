"""ModelsController for CRUD operations on registered models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from litestar import Controller, Request, delete, get, patch, post, put
from litestar.exceptions import NotFoundException
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED

# Litestar requires these imports at runtime for dependency injection type resolution
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from litestar_admin.audit import AuditAction, audit_admin_action, calculate_changes
from litestar_admin.registry import ModelRegistry  # noqa: TC001
from litestar_admin.service import AdminService

__all__ = [
    "DeleteResponse",
    "ListRecordsResponse",
    "ModelInfo",
    "ModelsController",
]


@dataclass
class ModelInfo:
    """Information about a registered model.

    Attributes:
        name: The display name of the model.
        model_name: The underlying model class name.
        icon: Icon identifier for the model.
        category: Category grouping for the model.
        can_create: Whether new records can be created.
        can_edit: Whether records can be edited.
        can_delete: Whether records can be deleted.
        can_view_details: Whether record details can be viewed.
    """

    name: str
    model_name: str
    icon: str = "table"
    category: str | None = None
    can_create: bool = True
    can_edit: bool = True
    can_delete: bool = True
    can_view_details: bool = True


@dataclass
class ListRecordsResponse:
    """Response for listing records with pagination.

    Attributes:
        items: List of serialized records.
        total: Total number of records matching the query.
        offset: Current offset in the result set.
        limit: Number of records requested.
    """

    items: list[dict[str, Any]]
    total: int
    offset: int
    limit: int


@dataclass
class DeleteResponse:
    """Response for delete operations.

    Attributes:
        success: Whether the deletion was successful.
        message: Optional message describing the result.
    """

    success: bool
    message: str = ""


def _serialize_record(record: Any, columns: list[str] | None = None) -> dict[str, Any]:
    """Serialize a SQLAlchemy model instance to a dictionary.

    Args:
        record: The SQLAlchemy model instance.
        columns: Optional list of columns to include. If None, includes all.

    Returns:
        Dictionary representation of the record.
    """
    from datetime import date, datetime
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy import inspect as sa_inspect

    result: dict[str, Any] = {}
    mapper = sa_inspect(type(record))

    for column in mapper.columns:
        column_name = column.name
        if columns is not None and column_name not in columns:
            continue

        value = getattr(record, column_name, None)

        # Convert non-JSON-serializable types
        if value is None:
            result[column_name] = None
        elif isinstance(value, (datetime, date)):
            result[column_name] = value.isoformat()
        elif isinstance(value, Decimal):
            result[column_name] = float(value)
        elif isinstance(value, UUID):
            result[column_name] = str(value)
        elif isinstance(value, bytes):
            result[column_name] = value.decode("utf-8", errors="replace")
        else:
            result[column_name] = value

    return result


class ModelsController(Controller):
    """Controller for CRUD operations on registered models.

    Provides REST API endpoints for managing model records in the admin panel.
    All endpoints require proper authentication and authorization when
    configured via guards.

    Example:
        The controller is automatically registered by AdminPlugin.
        Access endpoints at:
        - GET /admin/api/models - List all registered models
        - GET /admin/api/models/{model_name} - List records for a model
        - POST /admin/api/models/{model_name} - Create a new record
        - GET /admin/api/models/{model_name}/{record_id} - Get a single record
        - PUT /admin/api/models/{model_name}/{record_id} - Full update
        - PATCH /admin/api/models/{model_name}/{record_id} - Partial update
        - DELETE /admin/api/models/{model_name}/{record_id} - Delete a record
        - GET /admin/api/models/{model_name}/schema - Get JSON schema
    """

    path = "/api/models"
    tags: ClassVar[list[str]] = ["Models"]

    @get(
        "/",
        status_code=HTTP_200_OK,
        summary="List registered models",
        description="Returns a list of all models registered with the admin panel.",
    )
    async def list_models(
        self,
        admin_registry: ModelRegistry,
    ) -> list[ModelInfo]:
        """List all registered models with their metadata.

        Args:
            admin_registry: The model registry containing all registered views.

        Returns:
            List of model information objects.
        """
        models = admin_registry.list_models()
        return [
            ModelInfo(
                name=m["name"],
                model_name=m["model"],
                icon=m["icon"],
                category=m["category"],
                can_create=m["can_create"],
                can_edit=m["can_edit"],
                can_delete=m["can_delete"],
                can_view_details=m["can_view_details"],
            )
            for m in models
        ]

    @get(
        "/{model_name:str}",
        status_code=HTTP_200_OK,
        summary="List records for a model",
        description="Returns paginated records for a specific model.",
    )
    async def list_records(
        self,
        model_name: str,
        admin_registry: ModelRegistry,
        db_session: AsyncSession,
        offset: int = 0,
        limit: int = 50,
        sort_by: str | None = None,
        sort_order: str = "asc",
        search: str | None = None,
    ) -> ListRecordsResponse:
        """List records for a specific model with pagination and filtering.

        Args:
            model_name: The name of the registered model.
            admin_registry: The model registry.
            db_session: The database session.
            offset: Number of records to skip.
            limit: Maximum number of records to return (max 100).
            sort_by: Column name to sort by.
            sort_order: Sort order ("asc" or "desc").
            search: Search string for searchable columns.

        Returns:
            Paginated response with records and total count.

        Raises:
            NotFoundException: If the model is not registered.
        """
        # Validate and cap limit
        limit = min(max(1, limit), 100)
        offset = max(0, offset)

        # Validate sort_order
        if sort_order not in ("asc", "desc"):
            sort_order = "asc"

        try:
            view_class = admin_registry.get_view_by_name(model_name)
        except KeyError as exc:
            raise NotFoundException(f"Model '{model_name}' not found") from exc

        service: AdminService[Any] = AdminService(view_class, db_session)

        records, total = await service.list_records(
            offset=offset,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
            search=search,
        )

        # Get columns to serialize
        columns = view_class.get_list_columns()

        return ListRecordsResponse(
            items=[_serialize_record(r, columns if columns else None) for r in records],
            total=total,
            offset=offset,
            limit=limit,
        )

    @post(
        "/{model_name:str}",
        status_code=HTTP_201_CREATED,
        summary="Create a new record",
        description="Creates a new record for the specified model.",
    )
    async def create_record(
        self,
        request: Request[Any, Any, Any],
        model_name: str,
        data: dict[str, Any],
        admin_registry: ModelRegistry,
        db_session: AsyncSession,
    ) -> dict[str, Any]:
        """Create a new record for a model.

        Args:
            request: The incoming request.
            model_name: The name of the registered model.
            data: The record data to create.
            admin_registry: The model registry.
            db_session: The database session.

        Returns:
            The created record as a dictionary.

        Raises:
            NotFoundException: If the model is not registered.
        """
        try:
            view_class = admin_registry.get_view_by_name(model_name)
        except KeyError as exc:
            raise NotFoundException(f"Model '{model_name}' not found") from exc

        service: AdminService[Any] = AdminService(view_class, db_session)
        record = await service.create_record(data, request=request)

        serialized = _serialize_record(record)

        # Log audit entry
        await self._log_audit(
            db_session,
            request,
            AuditAction.CREATE,
            model_name,
            serialized.get("id"),
        )

        return serialized

    @get(
        "/{model_name:str}/schema",
        status_code=HTTP_200_OK,
        summary="Get model JSON schema",
        description="Returns the JSON schema for a model's fields.",
    )
    async def get_schema(
        self,
        model_name: str,
        admin_registry: ModelRegistry,
        db_session: AsyncSession,
        mode: str = "create",
    ) -> dict[str, Any]:
        """Get the JSON schema for a model.

        This endpoint returns a JSON schema that describes the model's fields,
        types, and validation rules. Useful for form generation in the frontend.

        Args:
            model_name: The name of the registered model.
            admin_registry: The model registry.
            db_session: The database session.
            mode: Form mode - "create" or "edit" (default: "create").

        Returns:
            JSON schema dictionary.

        Raises:
            NotFoundException: If the model is not registered.
        """
        try:
            view_class = admin_registry.get_view_by_name(model_name)
        except KeyError as exc:
            raise NotFoundException(f"Model '{model_name}' not found") from exc

        service: AdminService[Any] = AdminService(view_class, db_session)
        is_create = mode.lower() == "create"
        return service.get_model_schema(is_create=is_create)

    @get(
        "/{model_name:str}/{record_id:str}",
        status_code=HTTP_200_OK,
        summary="Get a single record",
        description="Returns a single record by its primary key.",
    )
    async def get_record(
        self,
        model_name: str,
        record_id: str,
        admin_registry: ModelRegistry,
        db_session: AsyncSession,
    ) -> dict[str, Any]:
        """Get a single record by primary key.

        Args:
            model_name: The name of the registered model.
            record_id: The primary key value (as string, will be converted).
            admin_registry: The model registry.
            db_session: The database session.

        Returns:
            The record as a dictionary.

        Raises:
            NotFoundException: If the model or record is not found.
        """
        try:
            view_class = admin_registry.get_view_by_name(model_name)
        except KeyError as exc:
            raise NotFoundException(f"Model '{model_name}' not found") from exc

        service: AdminService[Any] = AdminService(view_class, db_session)

        # Convert record_id to appropriate type
        pk = _convert_pk(record_id, service)

        record = await service.get_record(pk)
        if record is None:
            raise NotFoundException(f"Record '{record_id}' not found in '{model_name}'")

        return _serialize_record(record)

    @put(
        "/{model_name:str}/{record_id:str}",
        status_code=HTTP_200_OK,
        summary="Full update a record",
        description="Replaces all fields of a record with the provided data.",
    )
    async def update_record_full(
        self,
        request: Request[Any, Any, Any],
        model_name: str,
        record_id: str,
        data: dict[str, Any],
        admin_registry: ModelRegistry,
        db_session: AsyncSession,
    ) -> dict[str, Any]:
        """Fully update a record (replace all fields).

        Args:
            request: The incoming request.
            model_name: The name of the registered model.
            record_id: The primary key value.
            data: The complete record data.
            admin_registry: The model registry.
            db_session: The database session.

        Returns:
            The updated record as a dictionary.

        Raises:
            NotFoundException: If the model or record is not found.
        """
        print(f"[UPDATE] PUT request for {model_name}/{record_id} with data: {data}")
        try:
            view_class = admin_registry.get_view_by_name(model_name)
        except KeyError as exc:
            raise NotFoundException(f"Model '{model_name}' not found") from exc

        service: AdminService[Any] = AdminService(view_class, db_session)
        pk = _convert_pk(record_id, service)

        # Get old data for change tracking
        old_record = await service.get_record(pk)
        old_data = _serialize_record(old_record) if old_record else {}

        record = await service.update_record(pk, data, partial=False, request=request)
        if record is None:
            raise NotFoundException(f"Record '{record_id}' not found in '{model_name}'")

        serialized = _serialize_record(record)

        # Calculate and log changes
        changes = calculate_changes(old_data, serialized)
        await self._log_audit(
            db_session,
            request,
            AuditAction.UPDATE,
            model_name,
            record_id,
            changes=changes if changes else None,
        )

        return serialized

    @patch(
        "/{model_name:str}/{record_id:str}",
        status_code=HTTP_200_OK,
        summary="Partial update a record",
        description="Updates only the provided fields of a record.",
    )
    async def update_record_partial(
        self,
        request: Request[Any, Any, Any],
        model_name: str,
        record_id: str,
        data: dict[str, Any],
        admin_registry: ModelRegistry,
        db_session: AsyncSession,
    ) -> dict[str, Any]:
        """Partially update a record (only provided fields).

        Args:
            request: The incoming request.
            model_name: The name of the registered model.
            record_id: The primary key value.
            data: The fields to update.
            admin_registry: The model registry.
            db_session: The database session.

        Returns:
            The updated record as a dictionary.

        Raises:
            NotFoundException: If the model or record is not found.
        """
        try:
            view_class = admin_registry.get_view_by_name(model_name)
        except KeyError as exc:
            raise NotFoundException(f"Model '{model_name}' not found") from exc

        service: AdminService[Any] = AdminService(view_class, db_session)
        pk = _convert_pk(record_id, service)

        # Get old data for change tracking
        old_record = await service.get_record(pk)
        old_data = _serialize_record(old_record) if old_record else {}

        record = await service.update_record(pk, data, partial=True, request=request)
        if record is None:
            raise NotFoundException(f"Record '{record_id}' not found in '{model_name}'")

        serialized = _serialize_record(record)

        # Calculate and log changes
        changes = calculate_changes(old_data, serialized)
        await self._log_audit(
            db_session,
            request,
            AuditAction.UPDATE,
            model_name,
            record_id,
            changes=changes if changes else None,
        )

        return serialized

    @delete(
        "/{model_name:str}/{record_id:str}",
        status_code=HTTP_200_OK,
        summary="Delete a record",
        description="Deletes a record by its primary key.",
    )
    async def delete_record(
        self,
        request: Request[Any, Any, Any],
        model_name: str,
        record_id: str,
        admin_registry: ModelRegistry,
        db_session: AsyncSession,
        *,
        soft_delete: bool = False,
    ) -> DeleteResponse:
        """Delete a record by primary key.

        Args:
            request: The incoming request.
            model_name: The name of the registered model.
            record_id: The primary key value.
            admin_registry: The model registry.
            db_session: The database session.
            soft_delete: If True, perform soft delete if supported.

        Returns:
            Delete response indicating success.

        Raises:
            NotFoundException: If the model or record is not found.
        """
        try:
            view_class = admin_registry.get_view_by_name(model_name)
        except KeyError as exc:
            raise NotFoundException(f"Model '{model_name}' not found") from exc

        service: AdminService[Any] = AdminService(view_class, db_session)
        pk = _convert_pk(record_id, service)

        success = await service.delete_record(pk, soft_delete=soft_delete)
        if not success:
            raise NotFoundException(f"Record '{record_id}' not found in '{model_name}'")

        # Log audit entry
        await self._log_audit(
            db_session,
            request,
            AuditAction.DELETE,
            model_name,
            record_id,
            metadata={"soft_delete": soft_delete},
        )

        return DeleteResponse(success=True, message=f"Record '{record_id}' deleted successfully")

    @staticmethod
    async def _log_audit(
        db_session: AsyncSession,
        request: Request[Any, Any, Any],
        action: AuditAction,
        model_name: str,
        record_id: str | int | None,
        *,
        changes: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log an audit entry for a CRUD operation.

        Args:
            db_session: The database session.
            request: The incoming request for actor/request info.
            action: The action being performed.
            model_name: The name of the model being modified.
            record_id: The ID of the record being modified.
            changes: Optional dictionary of field changes.
            metadata: Optional additional metadata.
        """
        import logging

        from litestar_admin.audit.models import AuditLog

        audit_logger = logging.getLogger("litestar_admin.audit")
        audit_logger.info(f"Audit log: {action.value} on {model_name} record {record_id}")

        try:
            print(f"[AUDIT] Starting audit log for {action.value} on {model_name} record {record_id}")

            entry = await audit_admin_action(
                connection=request,
                action=action,
                model_name=model_name,
                record_id=record_id,
                changes=changes,
                metadata=metadata,
            )
            print(f"[AUDIT] Created audit entry: {entry.id}, actor: {entry.actor_email}")

            # Create the AuditLog model directly and add to session
            audit_log = AuditLog(
                id=entry.id,
                timestamp=entry.timestamp,
                action=entry.action.value,
                actor_id=str(entry.actor_id) if entry.actor_id is not None else None,
                actor_email=entry.actor_email,
                model_name=entry.model_name,
                record_id=str(entry.record_id) if entry.record_id is not None else None,
                changes=entry.changes,
                metadata_=entry.metadata,
                ip_address=entry.ip_address,
                user_agent=entry.user_agent,
            )

            print(f"[AUDIT] Session state before add: in_transaction={db_session.in_transaction()}")
            db_session.add(audit_log)
            print("[AUDIT] Added to session, flushing...")
            await db_session.flush()
            print("[AUDIT] Flushed, committing...")
            await db_session.commit()
            print("[AUDIT] Committed successfully!")
            audit_logger.info("Audit entry committed successfully")
        except Exception as e:
            print(f"[AUDIT] ERROR: {type(e).__name__}: {e}")
            audit_logger.error(f"Audit logging failed: {e}", exc_info=True)
            try:
                await db_session.rollback()
            except Exception:
                pass


def _convert_pk(pk_str: str, service: AdminService[Any]) -> Any:
    """Convert a string primary key to the appropriate type.

    Args:
        pk_str: The primary key as a string.
        service: The admin service instance.

    Returns:
        The primary key in the appropriate type.
    """
    from uuid import UUID

    pk_column = service._get_primary_key_column()  # noqa: SLF001
    type_name = type(pk_column.type).__name__.upper()

    # Attempt type conversion based on column type
    if type_name in ("INTEGER", "BIGINTEGER", "SMALLINTEGER"):
        try:
            return int(pk_str)
        except ValueError:
            return pk_str
    elif type_name == "UUID":
        try:
            return UUID(pk_str)
        except ValueError:
            return pk_str

    return pk_str
