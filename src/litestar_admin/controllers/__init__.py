"""REST API controllers for admin panel."""

from __future__ import annotations

from litestar_admin.controllers.bulk import (
    BulkActionRequest,
    BulkActionResponse,
    BulkActionsController,
    BulkDeleteRequest,
    BulkDeleteResponse,
)
from litestar_admin.controllers.dashboard import (
    ActivityEntry,
    DashboardController,
    DashboardStats,
    ModelStats,
    WidgetData,
)
from litestar_admin.controllers.export import (
    BulkExportRequest,
    ExportController,
)
from litestar_admin.controllers.models import (
    DeleteResponse,
    ListRecordsResponse,
    ModelInfo,
    ModelsController,
)

__all__ = [
    # Controllers
    "BulkActionsController",
    "DashboardController",
    "ExportController",
    "ModelsController",
    # DTOs - Bulk Actions
    "BulkActionRequest",
    "BulkActionResponse",
    "BulkDeleteRequest",
    "BulkDeleteResponse",
    # DTOs - Dashboard
    "ActivityEntry",
    "DashboardStats",
    "ModelStats",
    "WidgetData",
    # DTOs - Export
    "BulkExportRequest",
    # DTOs - Models
    "DeleteResponse",
    "ListRecordsResponse",
    "ModelInfo",
]
