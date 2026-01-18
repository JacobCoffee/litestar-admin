"""litestar-admin: Modern admin panel framework for Litestar applications."""

from __future__ import annotations

from litestar_admin.config import AdminConfig
from litestar_admin.plugin import AdminPlugin
from litestar_admin.registry import ModelRegistry
from litestar_admin.service import AdminService
from litestar_admin.views import BaseModelView, ModelView

__all__ = [
    # Core
    "AdminConfig",
    "AdminPlugin",
    "AdminService",
    "ModelRegistry",
    # Views
    "BaseModelView",
    "ModelView",
]

__version__ = "0.1.0"
