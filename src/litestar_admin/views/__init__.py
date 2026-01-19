"""View classes for admin panel."""

from __future__ import annotations

from litestar_admin.views.action import ActionResult, ActionView, FormField
from litestar_admin.views.admin_view import BaseAdminView
from litestar_admin.views.base import BaseModelView
from litestar_admin.views.custom import ColumnDefinition, CustomView, ListResult
from litestar_admin.views.embed import EmbedView
from litestar_admin.views.link import LinkView
from litestar_admin.views.model import ModelView
from litestar_admin.views.page import PageView

__all__ = [
    "ActionResult",
    "ActionView",
    "BaseAdminView",
    "BaseModelView",
    "ColumnDefinition",
    "CustomView",
    "EmbedView",
    "FormField",
    "LinkView",
    "ListResult",
    "ModelView",
    "PageView",
]
