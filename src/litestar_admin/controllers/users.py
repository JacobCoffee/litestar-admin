"""UserManagementController for CRUD operations on admin users."""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass, field
from typing import Any, ClassVar

from litestar import Controller, Request, delete, get, post, put
from litestar.exceptions import HTTPException, NotFoundException
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT

# Litestar requires these imports at runtime for dependency injection type resolution
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from litestar_admin.audit import AuditAction, audit_admin_action, calculate_changes
from litestar_admin.audit.models import AuditLog
from litestar_admin.auth.models import AdminUser
from litestar_admin.guards.permissions import Permission, PermissionGuard

_audit_logger = logging.getLogger("litestar_admin.audit")

__all__ = [
    "ActivateDeactivateResponse",
    "UserCreateRequest",
    "UserListRequest",
    "UserListResponse",
    "UserManagementController",
    "UserResponse",
    "UserUpdateRequest",
]


@dataclass
class UserListRequest:
    """Request parameters for listing users with pagination and filtering.

    Attributes:
        page: Page number (1-indexed).
        page_size: Number of records per page.
        email: Optional email filter (partial match).
        is_active: Optional filter by active status.
        roles: Optional filter by roles (any match).
        sort_by: Column to sort by.
        sort_order: Sort order (asc or desc).
    """

    page: int = 1
    page_size: int = 20
    email: str | None = None
    is_active: bool | None = None
    roles: list[str] | None = None
    sort_by: str = "created_at"
    sort_order: str = "desc"


@dataclass
class UserResponse:
    """Response containing user data (without password_hash).

    Attributes:
        id: User's unique identifier.
        email: User's email address.
        name: User's display name.
        roles: List of role names.
        permissions: List of direct permission strings.
        is_active: Whether the user can log in.
        is_superuser: Whether the user bypasses permission checks.
        created_at: When the user was created.
        updated_at: When the user was last modified.
        last_login: When the user last logged in.
    """

    id: str
    email: str
    name: str | None
    roles: list[str]
    permissions: list[str]
    is_active: bool
    is_superuser: bool
    created_at: str
    updated_at: str
    last_login: str | None


@dataclass
class UserListResponse:
    """Response for paginated user list.

    Attributes:
        items: List of user responses.
        total: Total number of users matching the query.
        page: Current page number.
        page_size: Number of records per page.
        total_pages: Total number of pages.
    """

    items: list[UserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


@dataclass
class UserCreateRequest:
    """Request payload for creating a new user.

    Attributes:
        email: User's email address.
        password: User's password (will be hashed).
        name: Optional display name.
        roles: List of role names.
        permissions: List of direct permission strings.
        is_active: Whether the user can log in.
        is_superuser: Whether the user bypasses permission checks.
    """

    email: str
    password: str
    name: str | None = None
    roles: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    is_active: bool = True
    is_superuser: bool = False


@dataclass
class UserUpdateRequest:
    """Request payload for updating a user (partial update, no password).

    Attributes:
        email: New email address.
        name: New display name.
        roles: New list of role names.
        permissions: New list of direct permission strings.
        is_active: New active status.
        is_superuser: New superuser status.
    """

    email: str | None = None
    name: str | None = None
    roles: list[str] | None = None
    permissions: list[str] | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None


@dataclass
class ActivateDeactivateResponse:
    """Response for activate/deactivate operations.

    Attributes:
        success: Whether the operation was successful.
        message: Descriptive message about the result.
        is_active: The new active status.
    """

    success: bool
    message: str
    is_active: bool


def _user_to_response(user: AdminUser) -> UserResponse:
    """Convert an AdminUser model to a UserResponse DTO.

    Args:
        user: The AdminUser model instance.

    Returns:
        UserResponse DTO without password_hash.
    """
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        roles=user.roles or [],
        permissions=user.permissions or [],
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        created_at=user.created_at.isoformat() if user.created_at else "",
        updated_at=user.updated_at.isoformat() if user.updated_at else "",
        last_login=user.last_login.isoformat() if user.last_login else None,
    )


def _user_to_dict(user: AdminUser) -> dict[str, Any]:
    """Convert an AdminUser model to a dictionary for change tracking.

    Args:
        user: The AdminUser model instance.

    Returns:
        Dictionary representation (without password_hash).
    """
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "roles": user.roles,
        "permissions": user.permissions,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }


class UserManagementController(Controller):
    """Controller for CRUD operations on admin users.

    Provides REST API endpoints for managing AdminUser records.
    All endpoints require authentication and appropriate permissions.

    Example:
        The controller is automatically registered by AdminPlugin.
        Access endpoints at:
        - GET /admin/api/users - List users with pagination/filtering
        - GET /admin/api/users/{user_id} - Get a single user
        - POST /admin/api/users - Create a new user
        - PUT /admin/api/users/{user_id} - Update a user
        - DELETE /admin/api/users/{user_id} - Delete a user
        - POST /admin/api/users/{user_id}/activate - Activate a user
        - POST /admin/api/users/{user_id}/deactivate - Deactivate a user
    """

    path = "/api/users"
    tags: ClassVar[list[str]] = ["User Management"]

    @get(
        "/",
        status_code=HTTP_200_OK,
        guards=[PermissionGuard(Permission.USERS_READ)],
        summary="List admin users",
        description="Returns a paginated list of admin users with optional filtering.",
    )
    async def list_users(
        self,
        db_session: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        email: str | None = None,
        active: str | None = None,
        role: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> UserListResponse:
        """List admin users with pagination and filtering.

        Args:
            db_session: The database session.
            page: Page number (1-indexed, default 1).
            page_size: Number of records per page (default 20, max 100).
            email: Optional email filter (partial match).
            active: Optional filter by active status (string: "true" or "false").
            role: Optional filter by role (users with this role).
            sort_by: Column to sort by (default: created_at).
            sort_order: Sort order - asc or desc (default: desc).

        Returns:
            Paginated list of users.
        """
        # Validate and cap pagination parameters
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        offset = (page - 1) * page_size

        # Validate sort_order
        if sort_order not in ("asc", "desc"):
            sort_order = "desc"

        # Parse active filter from string to bool
        is_active: bool | None = None
        if active is not None:
            is_active = active.lower() == "true"

        # Build base query
        query = select(AdminUser)
        count_query = select(func.count(AdminUser.id))

        # Apply filters
        if email:
            query = query.where(AdminUser.email.ilike(f"%{email}%"))
            count_query = count_query.where(AdminUser.email.ilike(f"%{email}%"))

        if is_active is not None:
            query = query.where(AdminUser.is_active == is_active)
            count_query = count_query.where(AdminUser.is_active == is_active)

        if role:
            # Filter by role - check if role is in the JSON roles array
            # SQLAlchemy JSON contains for filtering
            query = query.where(AdminUser.roles.contains([role]))
            count_query = count_query.where(AdminUser.roles.contains([role]))

        # Apply sorting
        sort_column = getattr(AdminUser, sort_by, AdminUser.created_at)
        query = query.order_by(sort_column.desc() if sort_order == "desc" else sort_column.asc())

        # Apply pagination
        query = query.offset(offset).limit(page_size)

        # Execute queries
        result = await db_session.execute(query)
        users = list(result.scalars().all())

        count_result = await db_session.execute(count_query)
        total = count_result.scalar() or 0

        # Calculate total pages
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        return UserListResponse(
            items=[_user_to_response(u) for u in users],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @get(
        "/{user_id:str}",
        status_code=HTTP_200_OK,
        guards=[PermissionGuard(Permission.USERS_READ)],
        summary="Get a single user",
        description="Returns a single admin user by ID.",
    )
    async def get_user(
        self,
        user_id: str,
        db_session: AsyncSession,
    ) -> UserResponse:
        """Get a single admin user by ID.

        Args:
            user_id: The user's unique identifier.
            db_session: The database session.

        Returns:
            The user data.

        Raises:
            NotFoundException: If the user is not found.
        """
        result = await db_session.execute(select(AdminUser).where(AdminUser.id == user_id))
        user = result.scalar_one_or_none()

        if user is None:
            raise NotFoundException(f"User '{user_id}' not found")

        return _user_to_response(user)

    @post(
        "/",
        status_code=HTTP_201_CREATED,
        guards=[PermissionGuard(Permission.USERS_CREATE)],
        summary="Create a new user",
        description="Creates a new admin user with the provided data.",
    )
    async def create_user(
        self,
        request: Request[Any, Any, Any],
        data: UserCreateRequest,
        db_session: AsyncSession,
    ) -> UserResponse:
        """Create a new admin user.

        Args:
            request: The incoming request.
            data: The user creation data.
            db_session: The database session.

        Returns:
            The created user data.

        Raises:
            HTTPException: If a user with the same email already exists.
        """
        # Check if email already exists
        existing = await db_session.execute(select(AdminUser).where(AdminUser.email == data.email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"User with email '{data.email}' already exists")

        # Create user with hashed password
        user = AdminUser.create(
            email=data.email,
            password=data.password,
            name=data.name,
            roles=data.roles,
            permissions=data.permissions,
            is_active=data.is_active,
            is_superuser=data.is_superuser,
        )

        db_session.add(user)
        await db_session.flush()

        # Log audit entry
        await self._log_audit(
            db_session=db_session,
            request=request,
            action=AuditAction.CREATE,
            record_id=user.id,
            metadata={"email": user.email},
        )

        await db_session.commit()

        return _user_to_response(user)

    @put(
        "/{user_id:str}",
        status_code=HTTP_200_OK,
        guards=[PermissionGuard(Permission.USERS_EDIT)],
        summary="Update a user",
        description="Updates an existing admin user with the provided data.",
    )
    async def update_user(
        self,
        request: Request[Any, Any, Any],
        user_id: str,
        data: UserUpdateRequest,
        db_session: AsyncSession,
    ) -> UserResponse:
        """Update an existing admin user.

        Args:
            request: The incoming request.
            user_id: The user's unique identifier.
            data: The user update data (partial).
            db_session: The database session.

        Returns:
            The updated user data.

        Raises:
            NotFoundException: If the user is not found.
            HTTPException: If the new email already exists.
        """
        result = await db_session.execute(select(AdminUser).where(AdminUser.id == user_id))
        user = result.scalar_one_or_none()

        if user is None:
            raise NotFoundException(f"User '{user_id}' not found")

        # Store old data for change tracking
        old_data = _user_to_dict(user)

        # Update fields if provided
        if data.email is not None and data.email != user.email:
            # Check if new email already exists
            existing = await db_session.execute(select(AdminUser).where(AdminUser.email == data.email))
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=400, detail=f"User with email '{data.email}' already exists")
            user.email = data.email

        if data.name is not None:
            user.name = data.name

        if data.roles is not None:
            user.roles = data.roles

        if data.permissions is not None:
            user.permissions = data.permissions

        if data.is_active is not None:
            user.is_active = data.is_active

        if data.is_superuser is not None:
            user.is_superuser = data.is_superuser

        await db_session.flush()

        # Calculate and log changes
        new_data = _user_to_dict(user)
        changes = calculate_changes(old_data, new_data)

        await self._log_audit(
            db_session=db_session,
            request=request,
            action=AuditAction.UPDATE,
            record_id=user_id,
            changes=changes if changes else None,
        )

        await db_session.commit()

        return _user_to_response(user)

    @delete(
        "/{user_id:str}",
        status_code=HTTP_204_NO_CONTENT,
        guards=[PermissionGuard(Permission.USERS_DELETE)],
        summary="Delete a user",
        description="Deletes an admin user by ID.",
    )
    async def delete_user(
        self,
        request: Request[Any, Any, Any],
        user_id: str,
        db_session: AsyncSession,
    ) -> None:
        """Delete an admin user.

        Args:
            request: The incoming request.
            user_id: The user's unique identifier.
            db_session: The database session.

        Raises:
            NotFoundException: If the user is not found.
            HTTPException: If trying to delete yourself.
        """
        result = await db_session.execute(select(AdminUser).where(AdminUser.id == user_id))
        user = result.scalar_one_or_none()

        if user is None:
            raise NotFoundException(f"User '{user_id}' not found")

        # Prevent self-deletion
        current_user = getattr(request, "user", None)
        if current_user and str(getattr(current_user, "id", None)) == user_id:
            raise HTTPException(status_code=400, detail="Cannot delete your own account")

        email = user.email  # Store for audit log

        await db_session.delete(user)
        await db_session.flush()

        # Log audit entry
        await self._log_audit(
            db_session=db_session,
            request=request,
            action=AuditAction.DELETE,
            record_id=user_id,
            metadata={"email": email},
        )

        await db_session.commit()

    @post(
        "/{user_id:str}/activate",
        status_code=HTTP_200_OK,
        guards=[PermissionGuard(Permission.USERS_EDIT)],
        summary="Activate a user",
        description="Activates a deactivated admin user.",
    )
    async def activate_user(
        self,
        request: Request[Any, Any, Any],
        user_id: str,
        db_session: AsyncSession,
    ) -> ActivateDeactivateResponse:
        """Activate an admin user.

        Args:
            request: The incoming request.
            user_id: The user's unique identifier.
            db_session: The database session.

        Returns:
            Response indicating the result.

        Raises:
            NotFoundException: If the user is not found.
        """
        result = await db_session.execute(select(AdminUser).where(AdminUser.id == user_id))
        user = result.scalar_one_or_none()

        if user is None:
            raise NotFoundException(f"User '{user_id}' not found")

        was_active = user.is_active
        user.is_active = True

        await db_session.flush()

        if not was_active:
            await self._log_audit(
                db_session=db_session,
                request=request,
                action=AuditAction.UPDATE,
                record_id=user_id,
                changes={"is_active": {"old": False, "new": True}},
                metadata={"operation": "activate"},
            )

        await db_session.commit()

        return ActivateDeactivateResponse(
            success=True,
            message="User activated successfully" if not was_active else "User was already active",
            is_active=True,
        )

    @post(
        "/{user_id:str}/deactivate",
        status_code=HTTP_200_OK,
        guards=[PermissionGuard(Permission.USERS_EDIT)],
        summary="Deactivate a user",
        description="Deactivates an active admin user.",
    )
    async def deactivate_user(
        self,
        request: Request[Any, Any, Any],
        user_id: str,
        db_session: AsyncSession,
    ) -> ActivateDeactivateResponse:
        """Deactivate an admin user.

        Args:
            request: The incoming request.
            user_id: The user's unique identifier.
            db_session: The database session.

        Returns:
            Response indicating the result.

        Raises:
            NotFoundException: If the user is not found.
            HTTPException: If trying to deactivate yourself.
        """
        result = await db_session.execute(select(AdminUser).where(AdminUser.id == user_id))
        user = result.scalar_one_or_none()

        if user is None:
            raise NotFoundException(f"User '{user_id}' not found")

        # Prevent self-deactivation
        current_user = getattr(request, "user", None)
        if current_user and str(getattr(current_user, "id", None)) == user_id:
            raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

        was_active = user.is_active
        user.is_active = False

        await db_session.flush()

        if was_active:
            await self._log_audit(
                db_session=db_session,
                request=request,
                action=AuditAction.UPDATE,
                record_id=user_id,
                changes={"is_active": {"old": True, "new": False}},
                metadata={"operation": "deactivate"},
            )

        await db_session.commit()

        return ActivateDeactivateResponse(
            success=True,
            message="User deactivated successfully" if was_active else "User was already inactive",
            is_active=False,
        )

    @staticmethod
    async def _log_audit(
        db_session: AsyncSession,
        request: Request[Any, Any, Any],
        action: AuditAction,
        record_id: str,
        *,
        changes: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log an audit entry for a user management operation.

        Args:
            db_session: The database session.
            request: The incoming request for actor/request info.
            action: The action being performed.
            record_id: The ID of the user being modified.
            changes: Optional dictionary of field changes.
            metadata: Optional additional metadata.
        """
        _audit_logger.info(
            "Audit log: %s on AdminUser record %s",
            action.value,
            record_id,
        )

        try:
            entry = await audit_admin_action(
                connection=request,
                action=action,
                model_name="AdminUser",
                record_id=record_id,
                changes=changes,
                metadata=metadata,
            )

            # Create the AuditLog model directly and add to session
            audit_log = AuditLog(
                id=entry.id,
                timestamp=entry.timestamp,
                action=entry.action.value,
                actor_id=str(entry.actor_id) if entry.actor_id is not None else None,
                actor_email=entry.actor_email,
                model_name=entry.model_name,
                record_id=str(entry.record_id) if entry.record_id is not None else None,
                changes=entry.changes,
                metadata_=entry.metadata,
                ip_address=entry.ip_address,
                user_agent=entry.user_agent,
            )

            db_session.add(audit_log)
            await db_session.flush()
            _audit_logger.info("Audit entry committed successfully")
        except Exception:
            _audit_logger.exception("Audit logging failed")
            # Don't fail the main operation if audit logging fails
            with contextlib.suppress(Exception):
                await db_session.rollback()
