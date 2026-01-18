"""RBAC guards and permissions for admin panel access control.

This module provides role-based access control (RBAC) primitives for protecting
admin panel routes, including Permission and Role enums, guard classes, and
helper functions.

Example:
    Import and use guards::

        from litestar_admin.guards import (
            Permission,
            Role,
            require_permission,
            require_role,
        )

        @get("/admin/users", guards=[require_permission(Permission.USERS_MANAGE)])
        async def list_users(): ...

        @get("/admin/settings", guards=[require_role(Role.ADMIN)])
        async def get_settings(): ...
"""

from __future__ import annotations

from litestar_admin.guards.permissions import (
    ROLE_PERMISSIONS,
    Permission,
    PermissionGuard,
    Role,
    RoleGuard,
    get_permissions_for_role,
    require_permission,
    require_role,
    user_has_permission,
    user_has_role,
)

__all__ = [
    "Permission",
    "PermissionGuard",
    "ROLE_PERMISSIONS",
    "Role",
    "RoleGuard",
    "get_permissions_for_role",
    "require_permission",
    "require_role",
    "user_has_permission",
    "user_has_role",
]
