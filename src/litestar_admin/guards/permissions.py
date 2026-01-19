"""RBAC permissions and guards for admin panel access control.

This module provides role-based access control (RBAC) primitives including
Permission and Role enums, guard classes, and helper functions for protecting
admin panel routes.

Example:
    Apply guards to routes::

        from litestar import get
        from litestar_admin.guards import require_permission, Permission


        @get("/admin/users", guards=[require_permission(Permission.USERS_MANAGE)])
        async def list_users(): ...

    Use role-based guards::

        from litestar_admin.guards import require_role, Role


        @get("/admin/settings", guards=[require_role(Role.ADMIN)])
        async def get_settings(): ...
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from litestar.exceptions import NotAuthorizedException

if TYPE_CHECKING:
    from litestar.connection import ASGIConnection
    from litestar.handlers.base import BaseRouteHandler
    from litestar.types import Guard

    from litestar_admin.auth.protocols import AdminUserProtocol

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


class Permission(str, Enum):
    """Enumeration of available permissions in the admin panel.

    Permissions follow a resource:action pattern for clarity and consistency.

    Attributes:
        MODELS_READ: Permission to read/list model records.
        MODELS_WRITE: Permission to create and update model records.
        MODELS_DELETE: Permission to delete model records.
        MODELS_EXPORT: Permission to export model data.
        DASHBOARD_VIEW: Permission to view the admin dashboard.
        USERS_MANAGE: Permission to manage admin users.
        SETTINGS_MANAGE: Permission to manage admin settings.
        AUDIT_VIEW: Permission to view audit logs.
    """

    MODELS_READ = "models:read"
    MODELS_WRITE = "models:write"
    MODELS_DELETE = "models:delete"
    MODELS_EXPORT = "models:export"
    DASHBOARD_VIEW = "dashboard:view"
    USERS_MANAGE = "users:manage"
    SETTINGS_MANAGE = "settings:manage"
    AUDIT_VIEW = "audit:view"


class Role(str, Enum):
    """Enumeration of available roles in the admin panel.

    Roles are hierarchical, with each role inheriting permissions from
    lower-level roles.

    Attributes:
        VIEWER: Read-only access to models and dashboard.
        EDITOR: Can create and update records, plus viewer permissions.
        ADMIN: Full model management plus user and audit access.
        SUPERADMIN: Complete access to all features including settings.
    """

    VIEWER = "viewer"
    EDITOR = "editor"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


# Role to permissions mapping
# Each role has its own permissions plus inherits from lower roles
ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.VIEWER: {
        Permission.MODELS_READ,
        Permission.DASHBOARD_VIEW,
    },
    Role.EDITOR: {
        Permission.MODELS_READ,
        Permission.DASHBOARD_VIEW,
        Permission.MODELS_WRITE,
    },
    Role.ADMIN: {
        Permission.MODELS_READ,
        Permission.DASHBOARD_VIEW,
        Permission.MODELS_WRITE,
        Permission.MODELS_DELETE,
        Permission.MODELS_EXPORT,
        Permission.USERS_MANAGE,
        Permission.AUDIT_VIEW,
    },
    Role.SUPERADMIN: {
        Permission.MODELS_READ,
        Permission.MODELS_WRITE,
        Permission.MODELS_DELETE,
        Permission.MODELS_EXPORT,
        Permission.DASHBOARD_VIEW,
        Permission.USERS_MANAGE,
        Permission.SETTINGS_MANAGE,
        Permission.AUDIT_VIEW,
    },
}


def get_permissions_for_role(role: Role) -> set[Permission]:
    """Get all permissions associated with a role.

    Args:
        role: The role to get permissions for.

    Returns:
        A set of permissions granted to the specified role.

    Example:
        >>> perms = get_permissions_for_role(Role.VIEWER)
        >>> Permission.MODELS_READ in perms
        True
        >>> Permission.MODELS_DELETE in perms
        False
    """
    return ROLE_PERMISSIONS.get(role, set())


def _get_valid_role(role_str: str) -> Role | None:
    """Safely convert a role string to a Role enum.

    Args:
        role_str: The role string to convert.

    Returns:
        The Role enum value, or None if invalid.
    """
    try:
        return Role(role_str)
    except ValueError:
        return None


def user_has_permission(user: AdminUserProtocol, permission: Permission) -> bool:
    """Check if a user has a specific permission.

    Checks both direct permission assignment and role-based permissions.

    Args:
        user: The admin user to check.
        permission: The permission to check for.

    Returns:
        True if the user has the permission, False otherwise.

    Example:
        >>> user_has_permission(admin_user, Permission.MODELS_READ)
        True
    """
    # Check direct permissions first
    if permission.value in user.permissions:
        return True

    # Check role-based permissions
    # Convert role strings to Role enums, filtering out invalid ones
    valid_roles = [role for role_str in user.roles if (role := _get_valid_role(role_str)) is not None]

    return any(permission in get_permissions_for_role(role) for role in valid_roles)


def user_has_role(user: AdminUserProtocol, role: Role) -> bool:
    """Check if a user has a specific role.

    Args:
        user: The admin user to check.
        role: The role to check for.

    Returns:
        True if the user has the role, False otherwise.

    Example:
        >>> user_has_role(admin_user, Role.ADMIN)
        True
    """
    return role.value in user.roles


class PermissionGuard:
    """Guard that checks if the user has required permission(s).

    This guard verifies that the authenticated user has all of the specified
    permissions before allowing access to the protected route.

    Attributes:
        required_permissions: The permissions required for access.

    Example:
        Apply to a route::

            @get("/data", guards=[PermissionGuard(Permission.MODELS_READ)])
            async def get_data(): ...

        Require multiple permissions::

            @post(
                "/data", guards=[PermissionGuard(Permission.MODELS_READ, Permission.MODELS_WRITE)]
            )
            async def create_data(): ...
    """

    __slots__ = ("required_permissions",)

    def __init__(self, *permissions: Permission) -> None:
        """Initialize the permission guard.

        Args:
            *permissions: One or more permissions required for access.
                         All specified permissions must be present.

        Raises:
            ValueError: If no permissions are provided.
        """
        if not permissions:
            msg = "At least one permission must be specified"
            raise ValueError(msg)
        self.required_permissions: tuple[Permission, ...] = permissions

    def __call__(self, connection: ASGIConnection, _: BaseRouteHandler) -> None:
        """Check if the user has the required permissions.

        Args:
            connection: The ASGI connection containing user information.
            _: The route handler (unused).

        Raises:
            NotAuthorizedException: If the user is not authenticated or
                                   lacks required permissions.
        """
        user = getattr(connection, "user", None)
        if user is None:
            raise NotAuthorizedException("Authentication required")

        for permission in self.required_permissions:
            if not user_has_permission(user, permission):
                raise NotAuthorizedException(f"Permission '{permission.value}' required")


class RoleGuard:
    """Guard that checks if the user has at least one of the required roles.

    This guard verifies that the authenticated user has at least one of the
    specified roles before allowing access to the protected route.

    Attributes:
        required_roles: The roles that grant access (any one is sufficient).

    Example:
        Apply to a route::

            @get("/admin", guards=[RoleGuard(Role.ADMIN)])
            async def admin_only(): ...

        Allow multiple roles::

            @get("/manage", guards=[RoleGuard(Role.ADMIN, Role.SUPERADMIN)])
            async def admin_or_superadmin(): ...
    """

    __slots__ = ("required_roles",)

    def __init__(self, *roles: Role) -> None:
        """Initialize the role guard.

        Args:
            *roles: One or more roles that grant access.
                   Having any one of these roles is sufficient.

        Raises:
            ValueError: If no roles are provided.
        """
        if not roles:
            msg = "At least one role must be specified"
            raise ValueError(msg)
        self.required_roles: tuple[Role, ...] = roles

    def __call__(self, connection: ASGIConnection, _: BaseRouteHandler) -> None:
        """Check if the user has at least one of the required roles.

        Args:
            connection: The ASGI connection containing user information.
            _: The route handler (unused).

        Raises:
            NotAuthorizedException: If the user is not authenticated or
                                   lacks any of the required roles.
        """
        user = getattr(connection, "user", None)
        if user is None:
            raise NotAuthorizedException("Authentication required")

        for role in self.required_roles:
            if user_has_role(user, role):
                return

        role_names = ", ".join(f"'{r.value}'" for r in self.required_roles)
        raise NotAuthorizedException(f"One of roles {role_names} required")


def require_permission(*permissions: Permission) -> Guard:
    """Create a guard that requires specific permission(s).

    Factory function for creating PermissionGuard instances.

    Args:
        *permissions: One or more permissions required for access.
                     All specified permissions must be present.

    Returns:
        A Guard instance that checks for the required permissions.

    Example:
        >>> guard = require_permission(Permission.MODELS_READ)
        >>> @get("/data", guards=[guard])
        ... async def get_data(): ...

        Or inline::

        >>> @get("/data", guards=[require_permission(Permission.MODELS_READ)])
        ... async def get_data(): ...
    """
    return PermissionGuard(*permissions)


def require_role(*roles: Role) -> Guard:
    """Create a guard that requires at least one of the specified roles.

    Factory function for creating RoleGuard instances.

    Args:
        *roles: One or more roles that grant access.
               Having any one of these roles is sufficient.

    Returns:
        A Guard instance that checks for the required roles.

    Example:
        >>> guard = require_role(Role.ADMIN)
        >>> @get("/admin", guards=[guard])
        ... async def admin_panel(): ...

        Or inline::

        >>> @get("/admin", guards=[require_role(Role.ADMIN, Role.SUPERADMIN)])
        ... async def admin_panel(): ...
    """
    return RoleGuard(*roles)
