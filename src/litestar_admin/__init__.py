"""litestar-admin: Modern admin panel framework for Litestar applications."""

from __future__ import annotations

from litestar_admin.config import AdminConfig
from litestar_admin.logging import LoggingConfig, configure_logging, get_logger, has_structlog
from litestar_admin.plugin import AdminPlugin
from litestar_admin.registry import ModelRegistry, ViewRegistry
from litestar_admin.service import AdminService
from litestar_admin.settings import AdminSettings, AdminSettingsBase, SettingsCategory, SettingsService
from litestar_admin.views import BaseModelView, ModelView

__all__ = [
    # Core
    "AdminConfig",
    "AdminPlugin",
    "AdminService",
    "ModelRegistry",
    "ViewRegistry",
    # Logging
    "LoggingConfig",
    "configure_logging",
    "get_logger",
    "has_structlog",
    # Settings
    "AdminSettings",
    "AdminSettingsBase",
    "SettingsCategory",
    "SettingsService",
    # Views
    "BaseModelView",
    "ModelView",
]

__version__ = "0.1.0"
