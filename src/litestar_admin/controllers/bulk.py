"""BulkActionsController for batch operations on model records."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

from litestar import Controller, post
from litestar.exceptions import HTTPException, NotFoundException
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
)

# Litestar requires these imports at runtime for dependency injection type resolution
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from litestar_admin.registry import ModelRegistry  # noqa: TC001
from litestar_admin.service import AdminService

if TYPE_CHECKING:
    from litestar.connection import Request

    from litestar_admin.views import BaseModelView

__all__ = [
    "BulkActionRequest",
    "BulkActionResponse",
    "BulkActionsController",
    "BulkDeleteRequest",
    "BulkDeleteResponse",
]


@dataclass
class BulkDeleteRequest:
    """Request body for bulk delete operations.

    Attributes:
        ids: List of primary key values to delete.
        soft_delete: If True, perform soft delete (set deleted_at) if supported.
    """

    ids: list[Any]
    soft_delete: bool = False


@dataclass
class BulkDeleteResponse:
    """Response for bulk delete operations.

    Attributes:
        deleted: Number of records successfully deleted.
        success: Whether the operation completed successfully.
    """

    deleted: int
    success: bool = True


@dataclass
class BulkActionRequest:
    """Request body for custom bulk actions.

    Attributes:
        ids: List of primary key values to apply the action to.
        params: Additional parameters for the action.
    """

    ids: list[Any]
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class BulkActionResponse:
    """Response for custom bulk actions.

    Attributes:
        success: Whether the action completed successfully.
        affected: Number of records affected by the action.
        result: Action-specific result data.
    """

    success: bool
    affected: int
    result: dict[str, Any] = field(default_factory=dict)


class BulkActionsController(Controller):
    """Controller for bulk operations on model records.

    Provides endpoints for performing batch operations such as bulk delete
    and custom bulk actions defined on model views.

    Example:
        The controller is automatically registered by AdminPlugin.
        Access endpoints at:
        - POST /admin/api/models/{model_name}/bulk/delete
        - POST /admin/api/models/{model_name}/bulk/{action}

        Define a custom bulk action on your model view:

        ```python
        class UserAdmin(ModelView, model=User):
            @classmethod
            async def bulk_activate(
                cls,
                session: AsyncSession,
                ids: list[Any],
                params: dict[str, Any],
            ) -> dict[str, Any]:
                # Activate multiple users
                count = 0
                for pk in ids:
                    user = await session.get(User, pk)
                    if user:
                        user.is_active = True
                        count += 1
                await session.flush()
                return {"affected": count}
        ```

        Then call via API:
        - POST /admin/api/models/User/bulk/activate
    """

    path = "/api/models"
    tags: ClassVar[list[str]] = ["Bulk Actions"]

    @post(
        "/{model_name:str}/bulk/delete",
        status_code=HTTP_200_OK,
        summary="Bulk delete records",
        description="Delete multiple records by their primary keys.",
    )
    async def bulk_delete(
        self,
        request: Request,
        model_name: str,
        data: BulkDeleteRequest,
        admin_registry: ModelRegistry,
        db_session: AsyncSession,
    ) -> BulkDeleteResponse:
        """Delete multiple records in a single operation.

        The operation is atomic - all deletions occur within the same
        transaction. If any deletion fails, the entire operation is rolled back.

        Args:
            request: The incoming request (for permission checks).
            model_name: The name of the model to delete records from.
            data: Request body containing IDs and soft_delete flag.
            admin_registry: The model registry for view lookup.
            db_session: The database session for transaction handling.

        Returns:
            Response containing the count of deleted records.

        Raises:
            HTTPException: 400 if ids array is empty or invalid.
            HTTPException: 403 if bulk delete is not allowed for this model.
            HTTPException: 404 if model is not registered.
        """
        # Validate request
        if not data.ids:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="IDs array cannot be empty",
            )

        # Get the view class for the model
        view_class = self._get_view_or_raise(admin_registry, model_name)

        # Check if bulk delete is allowed
        if not view_class.can_delete:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail=f"Bulk delete is not allowed for model '{model_name}'",
            )

        # Optionally check per-request permissions
        if not await view_class.is_accessible(request):
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail=f"Access denied to model '{model_name}'",
            )

        # Create service and perform bulk delete
        service = AdminService(view_class, db_session)
        deleted_count = await service.bulk_delete(
            data.ids,
            soft_delete=data.soft_delete,
        )

        return BulkDeleteResponse(deleted=deleted_count, success=True)

    @post(
        "/{model_name:str}/bulk/{action:str}",
        status_code=HTTP_200_OK,
        summary="Execute custom bulk action",
        description="Execute a custom bulk action defined on the model view.",
    )
    async def custom_action(
        self,
        request: Request,
        model_name: str,
        action: str,
        data: BulkActionRequest,
        admin_registry: ModelRegistry,
        db_session: AsyncSession,
    ) -> BulkActionResponse:
        """Execute a custom bulk action on multiple records.

        Custom actions are defined on the model view class as class methods
        named `bulk_{action}`. The method signature should be:

            @classmethod
            async def bulk_{action}(
                cls,
                session: AsyncSession,
                ids: list[Any],
                params: dict[str, Any],
            ) -> dict[str, Any]

        The method should return a dictionary with action-specific results.
        If the returned dictionary contains an "affected" key, that value
        will be used as the affected count in the response.

        Args:
            request: The incoming request (for permission checks).
            model_name: The name of the model to perform the action on.
            action: The name of the custom action to execute.
            data: Request body containing IDs and action parameters.
            admin_registry: The model registry for view lookup.
            db_session: The database session for transaction handling.

        Returns:
            Response containing success status, affected count, and action results.

        Raises:
            HTTPException: 400 if ids array is empty or action fails.
            HTTPException: 403 if access to the model is denied.
            HTTPException: 404 if model or action is not found.
        """
        # Validate request
        if not data.ids:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="IDs array cannot be empty",
            )

        # Get the view class for the model
        view_class = self._get_view_or_raise(admin_registry, model_name)

        # Check model accessibility
        if not await view_class.is_accessible(request):
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail=f"Access denied to model '{model_name}'",
            )

        # Look for the bulk action method on the view class
        action_method_name = f"bulk_{action}"
        if not hasattr(view_class, action_method_name):
            raise NotFoundException(
                detail=f"Bulk action '{action}' not found on model '{model_name}'",
            )

        action_method = getattr(view_class, action_method_name)

        # Verify it's callable
        if not callable(action_method):
            raise NotFoundException(
                detail=f"Bulk action '{action}' is not a callable method",
            )

        # Execute the custom action
        try:
            result = await action_method(
                session=db_session,
                ids=data.ids,
                params=data.params,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Bulk action '{action}' failed: {exc!s}",
            ) from exc

        # Normalize result to dictionary
        if not isinstance(result, dict):
            result = {"data": result}

        # Extract affected count from result if provided, otherwise use len(ids)
        affected = result.pop("affected", len(data.ids))

        return BulkActionResponse(
            success=True,
            affected=affected,
            result=result,
        )

    @staticmethod
    def _get_view_or_raise(
        registry: ModelRegistry,
        model_name: str,
    ) -> type[BaseModelView]:
        """Get a view class from the registry or raise 404.

        Args:
            registry: The model registry to search.
            model_name: The name of the model view to find.

        Returns:
            The view class for the model.

        Raises:
            HTTPException: 404 if model is not registered.
        """
        if not registry.has_model_by_name(model_name):
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"Model '{model_name}' not found",
            )
        return registry.get_view_by_name(model_name)
