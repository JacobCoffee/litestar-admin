"""Tests for RBAC guards and permissions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from litestar.exceptions import NotAuthorizedException

from litestar_admin.guards import (
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

if TYPE_CHECKING:
    pass


# ==============================================================================
# Test Fixtures
# ==============================================================================


@dataclass
class MockAdminUser:
    """Mock admin user for testing."""

    id: int
    email: str
    roles: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)


@pytest.fixture
def viewer_user() -> MockAdminUser:
    """Return a user with viewer role."""
    return MockAdminUser(
        id=1,
        email="viewer@example.com",
        roles=["viewer"],
        permissions=[],
    )


@pytest.fixture
def editor_user() -> MockAdminUser:
    """Return a user with editor role."""
    return MockAdminUser(
        id=2,
        email="editor@example.com",
        roles=["editor"],
        permissions=[],
    )


@pytest.fixture
def admin_user() -> MockAdminUser:
    """Return a user with admin role."""
    return MockAdminUser(
        id=3,
        email="admin@example.com",
        roles=["admin"],
        permissions=[],
    )


@pytest.fixture
def superadmin_user() -> MockAdminUser:
    """Return a user with superadmin role."""
    return MockAdminUser(
        id=4,
        email="superadmin@example.com",
        roles=["superadmin"],
        permissions=[],
    )


@pytest.fixture
def user_with_direct_permissions() -> MockAdminUser:
    """Return a user with direct permissions but no roles."""
    return MockAdminUser(
        id=5,
        email="direct@example.com",
        roles=[],
        permissions=["models:read", "models:write"],
    )


@pytest.fixture
def mock_connection(viewer_user: MockAdminUser) -> MagicMock:
    """Return a mock ASGI connection with a user."""
    conn = MagicMock()
    conn.scope = {"user": viewer_user}
    return conn


@pytest.fixture
def mock_handler() -> MagicMock:
    """Return a mock route handler."""
    return MagicMock()


# ==============================================================================
# Permission Enum Tests
# ==============================================================================


class TestPermissionEnum:
    """Tests for the Permission enum."""

    def test_permission_values(self) -> None:
        """Verify all permission values are correct."""
        assert Permission.MODELS_READ.value == "models:read"
        assert Permission.MODELS_WRITE.value == "models:write"
        assert Permission.MODELS_DELETE.value == "models:delete"
        assert Permission.MODELS_EXPORT.value == "models:export"
        assert Permission.DASHBOARD_VIEW.value == "dashboard:view"
        assert Permission.USERS_MANAGE.value == "users:manage"
        assert Permission.SETTINGS_MANAGE.value == "settings:manage"
        assert Permission.AUDIT_VIEW.value == "audit:view"

    def test_permission_is_string_enum(self) -> None:
        """Verify permissions can be used as strings."""
        assert Permission.MODELS_READ == "models:read"
        assert Permission.MODELS_READ.value == "models:read"


# ==============================================================================
# Role Enum Tests
# ==============================================================================


class TestRoleEnum:
    """Tests for the Role enum."""

    def test_role_values(self) -> None:
        """Verify all role values are correct."""
        assert Role.VIEWER.value == "viewer"
        assert Role.EDITOR.value == "editor"
        assert Role.ADMIN.value == "admin"
        assert Role.SUPERADMIN.value == "superadmin"

    def test_role_is_string_enum(self) -> None:
        """Verify roles can be used as strings."""
        assert Role.ADMIN == "admin"
        assert Role.ADMIN.value == "admin"


# ==============================================================================
# ROLE_PERMISSIONS Tests
# ==============================================================================


class TestRolePermissions:
    """Tests for the ROLE_PERMISSIONS mapping."""

    def test_viewer_permissions(self) -> None:
        """Verify viewer has correct permissions."""
        perms = ROLE_PERMISSIONS[Role.VIEWER]
        assert Permission.MODELS_READ in perms
        assert Permission.DASHBOARD_VIEW in perms
        assert Permission.MODELS_WRITE not in perms
        assert Permission.MODELS_DELETE not in perms

    def test_editor_permissions(self) -> None:
        """Verify editor has correct permissions."""
        perms = ROLE_PERMISSIONS[Role.EDITOR]
        # Inherited from viewer
        assert Permission.MODELS_READ in perms
        assert Permission.DASHBOARD_VIEW in perms
        # Editor-specific
        assert Permission.MODELS_WRITE in perms
        # Not included
        assert Permission.MODELS_DELETE not in perms
        assert Permission.USERS_MANAGE not in perms

    def test_admin_permissions(self) -> None:
        """Verify admin has correct permissions."""
        perms = ROLE_PERMISSIONS[Role.ADMIN]
        # Inherited from lower roles
        assert Permission.MODELS_READ in perms
        assert Permission.DASHBOARD_VIEW in perms
        assert Permission.MODELS_WRITE in perms
        # Admin-specific
        assert Permission.MODELS_DELETE in perms
        assert Permission.MODELS_EXPORT in perms
        assert Permission.USERS_MANAGE in perms
        assert Permission.AUDIT_VIEW in perms
        # Not included
        assert Permission.SETTINGS_MANAGE not in perms

    def test_superadmin_has_all_permissions(self) -> None:
        """Verify superadmin has all permissions."""
        perms = ROLE_PERMISSIONS[Role.SUPERADMIN]
        for permission in Permission:
            assert permission in perms, f"Superadmin missing {permission}"


# ==============================================================================
# get_permissions_for_role Tests
# ==============================================================================


class TestGetPermissionsForRole:
    """Tests for get_permissions_for_role function."""

    def test_get_viewer_permissions(self) -> None:
        """Verify get_permissions_for_role returns correct viewer permissions."""
        perms = get_permissions_for_role(Role.VIEWER)
        assert perms == ROLE_PERMISSIONS[Role.VIEWER]

    def test_get_permissions_returns_set(self) -> None:
        """Verify get_permissions_for_role returns a set."""
        perms = get_permissions_for_role(Role.ADMIN)
        assert isinstance(perms, set)


# ==============================================================================
# user_has_permission Tests
# ==============================================================================


class TestUserHasPermission:
    """Tests for user_has_permission function."""

    def test_viewer_has_read_permission(self, viewer_user: MockAdminUser) -> None:
        """Verify viewer can read models."""
        assert user_has_permission(viewer_user, Permission.MODELS_READ) is True

    def test_viewer_cannot_write(self, viewer_user: MockAdminUser) -> None:
        """Verify viewer cannot write models."""
        assert user_has_permission(viewer_user, Permission.MODELS_WRITE) is False

    def test_editor_can_write(self, editor_user: MockAdminUser) -> None:
        """Verify editor can write models."""
        assert user_has_permission(editor_user, Permission.MODELS_WRITE) is True

    def test_admin_can_delete(self, admin_user: MockAdminUser) -> None:
        """Verify admin can delete models."""
        assert user_has_permission(admin_user, Permission.MODELS_DELETE) is True

    def test_superadmin_can_manage_settings(self, superadmin_user: MockAdminUser) -> None:
        """Verify superadmin can manage settings."""
        assert user_has_permission(superadmin_user, Permission.SETTINGS_MANAGE) is True

    def test_direct_permissions(self, user_with_direct_permissions: MockAdminUser) -> None:
        """Verify direct permissions are respected."""
        assert user_has_permission(user_with_direct_permissions, Permission.MODELS_READ) is True
        assert user_has_permission(user_with_direct_permissions, Permission.MODELS_WRITE) is True
        assert user_has_permission(user_with_direct_permissions, Permission.MODELS_DELETE) is False

    def test_unknown_role_is_ignored(self) -> None:
        """Verify unknown roles don't cause errors."""
        user = MockAdminUser(
            id=99,
            email="unknown@example.com",
            roles=["unknown_role", "viewer"],
            permissions=[],
        )
        # Should still get viewer permissions
        assert user_has_permission(user, Permission.MODELS_READ) is True
        assert user_has_permission(user, Permission.MODELS_DELETE) is False


# ==============================================================================
# user_has_role Tests
# ==============================================================================


class TestUserHasRole:
    """Tests for user_has_role function."""

    def test_user_has_assigned_role(self, admin_user: MockAdminUser) -> None:
        """Verify user has their assigned role."""
        assert user_has_role(admin_user, Role.ADMIN) is True

    def test_user_does_not_have_other_role(self, viewer_user: MockAdminUser) -> None:
        """Verify user doesn't have unassigned roles."""
        assert user_has_role(viewer_user, Role.ADMIN) is False

    def test_user_with_multiple_roles(self) -> None:
        """Verify user with multiple roles."""
        user = MockAdminUser(
            id=99,
            email="multi@example.com",
            roles=["editor", "admin"],
            permissions=[],
        )
        assert user_has_role(user, Role.EDITOR) is True
        assert user_has_role(user, Role.ADMIN) is True
        assert user_has_role(user, Role.SUPERADMIN) is False


# ==============================================================================
# PermissionGuard Tests
# ==============================================================================


class TestPermissionGuard:
    """Tests for PermissionGuard class."""

    def test_guard_requires_permission(self) -> None:
        """Verify guard requires at least one permission."""
        with pytest.raises(ValueError, match="At least one permission must be specified"):
            PermissionGuard()

    def test_guard_passes_with_permission(
        self,
        viewer_user: MockAdminUser,
        mock_handler: MagicMock,
    ) -> None:
        """Verify guard passes when user has permission."""
        conn = MagicMock()
        conn.scope = {"user": viewer_user}
        guard = PermissionGuard(Permission.MODELS_READ)
        # Should not raise
        guard(conn, mock_handler)

    def test_guard_fails_without_permission(
        self,
        viewer_user: MockAdminUser,
        mock_handler: MagicMock,
    ) -> None:
        """Verify guard fails when user lacks permission."""
        conn = MagicMock()
        conn.scope = {"user": viewer_user}
        guard = PermissionGuard(Permission.MODELS_DELETE)
        with pytest.raises(NotAuthorizedException, match="Permission 'models:delete' required"):
            guard(conn, mock_handler)

    def test_guard_fails_without_user(self, mock_handler: MagicMock) -> None:
        """Verify guard fails when no user is present."""
        conn = MagicMock()
        conn.scope = {}  # No user in scope
        guard = PermissionGuard(Permission.MODELS_READ)
        with pytest.raises(NotAuthorizedException, match="Authentication required"):
            guard(conn, mock_handler)

    def test_guard_requires_all_permissions(
        self,
        editor_user: MockAdminUser,
        mock_handler: MagicMock,
    ) -> None:
        """Verify guard requires all specified permissions."""
        conn = MagicMock()
        conn.scope = {"user": editor_user}
        guard = PermissionGuard(Permission.MODELS_READ, Permission.MODELS_DELETE)
        with pytest.raises(NotAuthorizedException):
            guard(conn, mock_handler)

    def test_guard_passes_with_all_permissions(
        self,
        admin_user: MockAdminUser,
        mock_handler: MagicMock,
    ) -> None:
        """Verify guard passes when user has all permissions."""
        conn = MagicMock()
        conn.scope = {"user": admin_user}
        guard = PermissionGuard(Permission.MODELS_READ, Permission.MODELS_DELETE)
        # Should not raise
        guard(conn, mock_handler)


# ==============================================================================
# RoleGuard Tests
# ==============================================================================


class TestRoleGuard:
    """Tests for RoleGuard class."""

    def test_guard_requires_role(self) -> None:
        """Verify guard requires at least one role."""
        with pytest.raises(ValueError, match="At least one role must be specified"):
            RoleGuard()

    def test_guard_passes_with_role(
        self,
        admin_user: MockAdminUser,
        mock_handler: MagicMock,
    ) -> None:
        """Verify guard passes when user has role."""
        conn = MagicMock()
        conn.scope = {"user": admin_user}
        guard = RoleGuard(Role.ADMIN)
        # Should not raise
        guard(conn, mock_handler)

    def test_guard_fails_without_role(
        self,
        viewer_user: MockAdminUser,
        mock_handler: MagicMock,
    ) -> None:
        """Verify guard fails when user lacks role."""
        conn = MagicMock()
        conn.scope = {"user": viewer_user}
        guard = RoleGuard(Role.ADMIN)
        with pytest.raises(NotAuthorizedException, match="One of roles 'admin' required"):
            guard(conn, mock_handler)

    def test_guard_fails_without_user(self, mock_handler: MagicMock) -> None:
        """Verify guard fails when no user is present."""
        conn = MagicMock()
        conn.scope = {}  # No user in scope
        guard = RoleGuard(Role.ADMIN)
        with pytest.raises(NotAuthorizedException, match="Authentication required"):
            guard(conn, mock_handler)

    def test_guard_passes_with_any_role(
        self,
        admin_user: MockAdminUser,
        mock_handler: MagicMock,
    ) -> None:
        """Verify guard passes when user has any of the specified roles."""
        conn = MagicMock()
        conn.scope = {"user": admin_user}
        guard = RoleGuard(Role.EDITOR, Role.ADMIN)
        # Should not raise
        guard(conn, mock_handler)

    def test_guard_message_includes_all_roles(
        self,
        viewer_user: MockAdminUser,
        mock_handler: MagicMock,
    ) -> None:
        """Verify error message includes all required roles."""
        conn = MagicMock()
        conn.scope = {"user": viewer_user}
        guard = RoleGuard(Role.ADMIN, Role.SUPERADMIN)
        with pytest.raises(NotAuthorizedException, match="'admin', 'superadmin'"):
            guard(conn, mock_handler)


# ==============================================================================
# require_permission Factory Tests
# ==============================================================================


class TestRequirePermission:
    """Tests for require_permission factory function."""

    def test_creates_permission_guard(self) -> None:
        """Verify require_permission creates a PermissionGuard."""
        guard = require_permission(Permission.MODELS_READ)
        assert isinstance(guard, PermissionGuard)

    def test_guard_has_correct_permissions(self) -> None:
        """Verify created guard has correct permissions."""
        guard = require_permission(Permission.MODELS_READ, Permission.MODELS_WRITE)
        assert guard.required_permissions == (Permission.MODELS_READ, Permission.MODELS_WRITE)


# ==============================================================================
# require_role Factory Tests
# ==============================================================================


class TestRequireRole:
    """Tests for require_role factory function."""

    def test_creates_role_guard(self) -> None:
        """Verify require_role creates a RoleGuard."""
        guard = require_role(Role.ADMIN)
        assert isinstance(guard, RoleGuard)

    def test_guard_has_correct_roles(self) -> None:
        """Verify created guard has correct roles."""
        guard = require_role(Role.ADMIN, Role.SUPERADMIN)
        assert guard.required_roles == (Role.ADMIN, Role.SUPERADMIN)


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestGuardIntegration:
    """Integration tests for guards with Litestar patterns."""

    def test_guard_can_be_used_in_list(self) -> None:
        """Verify guards can be used in a guards list."""
        guards = [
            require_permission(Permission.MODELS_READ),
            require_role(Role.EDITOR),
        ]
        assert len(guards) == 2
        assert all(callable(g) for g in guards)

    def test_multiple_guards_all_pass(
        self,
        admin_user: MockAdminUser,
        mock_handler: MagicMock,
    ) -> None:
        """Verify multiple guards can all pass."""
        conn = MagicMock()
        conn.scope = {"user": admin_user}
        guards = [
            require_permission(Permission.MODELS_READ),
            require_permission(Permission.MODELS_DELETE),
            require_role(Role.ADMIN),
        ]
        # All guards should pass without exception
        for guard in guards:
            guard(conn, mock_handler)
