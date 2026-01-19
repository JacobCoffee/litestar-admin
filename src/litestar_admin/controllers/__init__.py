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
from litestar_admin.controllers.files import (
    DeleteFileResponse,
    FileInfoResponse,
    FilesController,
    ThumbnailResponse,
    UploadFileRequest,
    UploadFileResponse,
)
from litestar_admin.controllers.import_data import (
    ColumnMapping,
    ColumnTypeInfo,
    ImportController,
    ImportExecuteResponse,
    ImportPreviewResponse,
    ImportValidationResponse,
    ModelFieldInfo,
    RowError,
)
from litestar_admin.controllers.models import (
    DeleteResponse,
    ListRecordsResponse,
    ModelInfo,
    ModelsController,
)
from litestar_admin.controllers.oauth import OAuthController
from litestar_admin.controllers.relationships import (
    RelationshipOption,
    RelationshipsController,
    RelationshipSearchRequest,
    RelationshipSearchResponse,
)
from litestar_admin.controllers.settings import (
    BulkSettingsRequest,
    CreateSettingRequest,
    SettingResponse,
    SettingsController,
    SettingsListResponse,
    UpdateSettingRequest,
)
from litestar_admin.controllers.users import (
    ActivateDeactivateResponse,
    UserCreateRequest,
    UserListRequest,
    UserListResponse,
    UserManagementController,
    UserUpdateRequest,
)
from litestar_admin.controllers.users import (
    UserResponse as UserManagementUserResponse,
)

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
    "FilesController",
    "ImportController",
    "LinksController",
    "ModelsController",
    "OAuthController",
    "PagesController",
    "RelationshipsController",
    "SettingsController",
    "UserManagementController",
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
    # DTOs - Import
    "ColumnMapping",
    "ColumnTypeInfo",
    "ImportExecuteResponse",
    "ImportPreviewResponse",
    "ImportValidationResponse",
    "ModelFieldInfo",
    "RowError",
    # DTOs - Files
    "DeleteFileResponse",
    "FileInfoResponse",
    "ThumbnailResponse",
    "UploadFileRequest",
    "UploadFileResponse",
    # DTOs - Config
    "ConfigResponse",
    "DevCredential",
    # DTOs - Models
    "DeleteResponse",
    "ListRecordsResponse",
    "ModelInfo",
    # DTOs - Relationships
    "RelationshipOption",
    "RelationshipSearchRequest",
    "RelationshipSearchResponse",
    # DTOs - User Management
    "ActivateDeactivateResponse",
    "UserCreateRequest",
    "UserListRequest",
    "UserListResponse",
    "UserManagementUserResponse",
    "UserUpdateRequest",
    # DTOs - Settings
    "BulkSettingsRequest",
    "CreateSettingRequest",
    "SettingResponse",
    "SettingsListResponse",
    "UpdateSettingRequest",
]
