"""REST API controllers for admin panel."""

from __future__ import annotations

from litestar_admin.controllers.auth import (
    AuthController,
    LoginRequest,
    LogoutResponse,
    RefreshRequest,
    TokenResponse,
    UserResponse,
)
from litestar_admin.controllers.bulk import (
    BulkActionRequest,
    BulkActionResponse,
    BulkActionsController,
    BulkDeleteRequest,
    BulkDeleteResponse,
)
from litestar_admin.controllers.config import (
    ConfigController,
    ConfigResponse,
    DevCredential,
)
from litestar_admin.controllers.custom_views import (
    ActionExecuteRequest,
    ActionExecuteResponse,
    ActionInfoResponse,
    ActionsController,
    CustomViewDeleteResponse,
    CustomViewInfo,
    CustomViewListResponse,
    CustomViewSchemaResponse,
    CustomViewsController,
    EmbedConfigResponse,
    EmbedInfoResponse,
    EmbedPropsResponse,
    EmbedsController,
    LinkInfoResponse,
    LinksController,
    PageContentResponse,
    PageMetadataResponse,
    PagesController,
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
from litestar_admin.controllers.oauth import OAuthController

__all__ = [
    # Controllers
    "ActionsController",
    "AuthController",
    "BulkActionsController",
    "ConfigController",
    "CustomViewsController",
    "DashboardController",
    "EmbedsController",
    "ExportController",
    "LinksController",
    "ModelsController",
    "OAuthController",
    "PagesController",
    # DTOs - Auth
    "LoginRequest",
    "LogoutResponse",
    "RefreshRequest",
    "TokenResponse",
    "UserResponse",
    # DTOs - Bulk Actions
    "BulkActionRequest",
    "BulkActionResponse",
    "BulkDeleteRequest",
    "BulkDeleteResponse",
    # DTOs - Custom Views
    "ActionExecuteRequest",
    "ActionExecuteResponse",
    "ActionInfoResponse",
    "CustomViewDeleteResponse",
    "CustomViewInfo",
    "CustomViewListResponse",
    "CustomViewSchemaResponse",
    "EmbedConfigResponse",
    "EmbedInfoResponse",
    "EmbedPropsResponse",
    "LinkInfoResponse",
    "PageContentResponse",
    "PageMetadataResponse",
    # DTOs - Dashboard
    "ActivityEntry",
    "DashboardStats",
    "ModelStats",
    "WidgetData",
    # DTOs - Export
    "BulkExportRequest",
    # DTOs - Config
    "ConfigResponse",
    "DevCredential",
    # DTOs - Models
    "DeleteResponse",
    "ListRecordsResponse",
    "ModelInfo",
]
