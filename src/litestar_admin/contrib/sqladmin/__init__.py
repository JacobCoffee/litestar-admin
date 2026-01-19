"""SQLAdmin integration bridge.

This module provides utilities for migrating from sqladmin to litestar-admin,
allowing users to reuse existing sqladmin ModelView configurations.

Example:
    ```python
    from sqladmin import ModelView as SQLAdminModelView
    from litestar_admin.contrib.sqladmin import SQLAdminBridge, convert_sqladmin_view
    from litestar_admin import AdminPlugin, AdminConfig, ModelRegistry


    # Define sqladmin views (existing code)
    class UserAdmin(SQLAdminModelView, model=User):
        column_list = ["id", "email", "name"]
        column_searchable_list = ["email", "name"]
        can_delete = False


    # Option 1: Convert single view
    LitestarUserAdmin = convert_sqladmin_view(UserAdmin)

    # Option 2: Use bridge for multiple views
    bridge = SQLAdminBridge()
    bridge.register(UserAdmin)
    bridge.register(PostAdmin)
    litestar_views = bridge.convert_all()

    # Use converted views with litestar-admin
    registry = ModelRegistry()
    for view in litestar_views:
        registry.register(view)

    app = Litestar(plugins=[AdminPlugin(config=AdminConfig(registry=registry))])
    ```

Note:
    Some sqladmin-specific features cannot be converted directly:
    - column_labels (display labels)
    - column_formatters (value formatters)
    - form_args, form_widget_args (WTForms configuration)
    - form_ajax_refs (AJAX relationship handling)
    - edit_modal, create_modal, details_modal (modal editing)

    These features will be skipped during conversion. Enable strict mode
    in SQLAdminBridge to raise errors instead of silently skipping.
"""

from __future__ import annotations

from litestar_admin.contrib.sqladmin.bridge import (
    SQLADMIN_ATTR_MAPPING,
    SQLADMIN_SPECIFIC_ATTRS,
    SQLAdminBridge,
    convert_sqladmin_view,
)

__all__ = [
    "SQLADMIN_ATTR_MAPPING",
    "SQLADMIN_SPECIFIC_ATTRS",
    "SQLAdminBridge",
    "convert_sqladmin_view",
]
