"""SQLAlchemy models for admin user management.

This module provides database models for admin users with secure password
hashing, role-based access control, and comprehensive audit fields.

Example:
    Using the AdminUser model::

        from litestar_admin.auth.models import AdminUser
        from sqlalchemy.ext.asyncio import AsyncSession

        async def create_admin(session: AsyncSession) -> AdminUser:
            user = AdminUser.create(
                email="admin@example.com",
                password="secure_password",
                roles=["admin"],
                is_superuser=True,
            )
            session.add(user)
            await session.commit()
            return user

    Extending the base model::

        from litestar_admin.auth.models import AdminUserBase

        class CustomAdminUser(AdminUserBase):
            __tablename__ = "custom_admin_users"

            department: Mapped[str | None] = mapped_column(String(100))
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, ClassVar, Self

from sqlalchemy import JSON, Boolean, DateTime, Index, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from litestar_admin.guards.permissions import ROLE_PERMISSIONS, Permission, Role

__all__ = ["AdminUser", "AdminUserBase"]


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


class AdminUserBase(DeclarativeBase):
    """Abstract base class for admin user models.

    Use this as the declarative base for AdminUser if you need a separate
    metadata/base from your main application models. This allows the admin
    tables to be managed independently from your application's tables.

    Example:
        Using separate metadata::

            from litestar_admin.auth.models import AdminUserBase, AdminUser

            # AdminUser uses AdminUserBase.metadata
            # Your app models use their own Base.metadata

            # Create admin tables separately
            async with engine.begin() as conn:
                await conn.run_sync(AdminUserBase.metadata.create_all)
    """



class AdminUser(AdminUserBase):
    """SQLAlchemy model for admin users.

    This model provides a complete admin user implementation with:
    - Secure password hashing (Argon2/bcrypt)
    - Role-based access control
    - Permission management
    - Audit timestamps

    The model implements the AdminUser protocol from litestar_admin.auth.protocols.

    Attributes:
        id: Unique identifier (UUID string).
        email: User's email address (unique, indexed).
        password_hash: Hashed password (never store plain text).
        roles: JSON list of role strings (e.g., ["admin", "viewer"]).
        permissions: JSON list of additional permission strings.
        is_active: Whether the user can log in.
        is_superuser: Whether the user bypasses all permission checks.
        name: Optional display name.
        created_at: When the user was created (UTC).
        updated_at: When the user was last modified (UTC).
        last_login: When the user last logged in (nullable).

    Example:
        Create and authenticate a user::

            user = AdminUser.create(
                email="admin@example.com",
                password="secure123",
                roles=["admin"],
            )
            session.add(user)
            await session.commit()

            # Later, verify password
            if user.check_password("secure123"):
                user.last_login = datetime.now(tz=timezone.utc)
                await session.commit()
    """

    __tablename__: ClassVar[str] = "admin_users"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # Authentication fields
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Authorization fields
    roles: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    permissions: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    # Status flags
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    # Profile fields
    name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=timezone.utc),
        onupdate=lambda: datetime.now(tz=timezone.utc),
        nullable=False,
    )
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Indexes for common queries
    __table_args__ = (
        Index("ix_admin_users_email_active", "email", "is_active"),
        Index("ix_admin_users_created_at", "created_at"),
    )

    def set_password(self, password: str) -> None:
        """Set the user's password using secure hashing.

        Args:
            password: The plain text password to hash and store.

        Raises:
            RuntimeError: If no password hashing backend is available.

        Example:
            >>> user.set_password("new_secure_password")
        """
        from litestar_admin.auth.password import hash_password

        self.password_hash = hash_password(password)

    def check_password(self, password: str) -> bool:
        """Verify a password against the stored hash.

        Args:
            password: The plain text password to verify.

        Returns:
            True if the password is correct, False otherwise.

        Raises:
            RuntimeError: If no password hashing backend is available.

        Example:
            >>> if user.check_password("entered_password"):
            ...     print("Login successful!")
        """
        from litestar_admin.auth.password import verify_password

        return verify_password(password, self.password_hash)

    def has_permission(self, permission: str | Permission) -> bool:
        """Check if the user has a specific permission.

        Superusers always have all permissions. For regular users, checks
        both direct permission assignments and role-based permissions.

        Args:
            permission: The permission to check (string or Permission enum).

        Returns:
            True if the user has the permission, False otherwise.

        Example:
            >>> user.has_permission(Permission.MODELS_READ)
            True
            >>> user.has_permission("models:write")
            True
        """
        # Superusers have all permissions
        if self.is_superuser:
            return True

        # Normalize permission to string
        perm_str = permission.value if isinstance(permission, Permission) else permission

        # Check direct permissions
        if perm_str in self.permissions:
            return True

        # Check role-based permissions
        # Convert role strings to Role enums, filtering out invalid ones
        valid_roles = [role for role_str in self.roles if (role := _get_valid_role(role_str)) is not None]

        return any(
            any(p.value == perm_str for p in ROLE_PERMISSIONS.get(role, set()))
            for role in valid_roles
        )

    def has_role(self, role: str | Role) -> bool:
        """Check if the user has a specific role.

        Args:
            role: The role to check (string or Role enum).

        Returns:
            True if the user has the role, False otherwise.

        Example:
            >>> user.has_role(Role.ADMIN)
            True
            >>> user.has_role("editor")
            False
        """
        role_str = role.value if isinstance(role, Role) else role
        return role_str in self.roles

    def get_all_permissions(self) -> set[str]:
        """Get all permissions the user has.

        Combines direct permissions with role-based permissions.
        Superusers get all defined permissions.

        Returns:
            A set of permission strings.

        Example:
            >>> perms = user.get_all_permissions()
            >>> "models:read" in perms
            True
        """
        if self.is_superuser:
            return {p.value for p in Permission}

        all_perms: set[str] = set(self.permissions)

        # Convert role strings to Role enums, filtering out invalid ones
        valid_roles = [role for role_str in self.roles if (role := _get_valid_role(role_str)) is not None]

        for role in valid_roles:
            role_perms = ROLE_PERMISSIONS.get(role, set())
            all_perms.update(p.value for p in role_perms)

        return all_perms

    @classmethod
    def create(
        cls,
        email: str,
        password: str,
        *,
        roles: list[str] | None = None,
        permissions: list[str] | None = None,
        is_active: bool = True,
        is_superuser: bool = False,
        name: str | None = None,
        **kwargs: Any,
    ) -> Self:
        """Create a new admin user with a hashed password.

        Factory method that handles password hashing automatically.

        Args:
            email: The user's email address.
            password: The plain text password (will be hashed).
            roles: List of role strings (defaults to empty list).
            permissions: List of permission strings (defaults to empty list).
            is_active: Whether the user can log in (default True).
            is_superuser: Whether the user has all permissions (default False).
            name: Optional display name.
            **kwargs: Additional fields to set on the model.

        Returns:
            A new AdminUser instance (not yet persisted to database).

        Raises:
            RuntimeError: If no password hashing backend is available.

        Example:
            >>> user = AdminUser.create(
            ...     email="admin@example.com",
            ...     password="secure_password",
            ...     roles=["admin"],
            ...     name="Site Admin",
            ... )
            >>> session.add(user)
            >>> await session.commit()
        """
        from litestar_admin.auth.password import hash_password

        return cls(
            email=email,
            password_hash=hash_password(password),
            roles=roles or [],
            permissions=permissions or [],
            is_active=is_active,
            is_superuser=is_superuser,
            name=name,
            **kwargs,
        )

    def __repr__(self) -> str:
        """Return string representation of the admin user."""
        return f"<AdminUser(id={self.id!r}, email={self.email!r}, roles={self.roles!r})>"
