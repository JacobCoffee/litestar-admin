"""Authentication setup for the full admin demo.

This module provides the authentication configuration including:
- AdminUser dataclass implementing the AdminUser protocol
- user_loader async function for loading users by email/id
- password_verifier async function for credential validation
- JWTAuthBackend configuration

Example:
    >>> from examples.full.auth import get_auth_backend
    >>> backend = get_auth_backend(db_session_factory)
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from litestar_admin.auth.jwt import JWTAuthBackend, JWTConfig
from litestar_admin.guards import ROLE_PERMISSIONS, Permission, Role

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy.ext.asyncio import AsyncSession

__all__ = ["DemoAdminUser", "get_auth_backend", "hash_password", "verify_password"]


# Simple secret key for demo purposes - in production use environment variables
DEMO_SECRET_KEY = "demo-secret-key-change-in-production-12345"  # noqa: S105


@dataclass
class DemoAdminUser:
    """Admin user implementation for the demo application.

    This dataclass implements the AdminUser protocol required by litestar-admin,
    providing the necessary properties for authentication and authorization.

    Attributes:
        id: Unique identifier for the user.
        email: User's email address.
        roles: List of role names assigned to the user.
        permissions: List of permission strings the user has.
        password_hash: Hashed password for verification (optional, used internally).
        name: Display name for the user (optional).
        is_active: Whether the user account is active (optional).
    """

    id: int
    email: str
    roles: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    password_hash: str | None = None
    name: str | None = None
    is_active: bool = True

    @classmethod
    def from_db_user(cls, user: object) -> DemoAdminUser:
        """Create a DemoAdminUser from a database User model.

        Args:
            user: The database User model instance.

        Returns:
            A DemoAdminUser instance with data from the database user.
        """
        # Get user attributes safely
        user_id = getattr(user, "id", 0)
        email = getattr(user, "email", "")
        name = getattr(user, "name", None)
        password_hash = getattr(user, "password_hash", None)
        is_active = getattr(user, "is_active", True)

        # Get role from user model
        role_value = getattr(user, "role", None)
        if role_value is not None:
            if hasattr(role_value, "value"):
                role_str = role_value.value
            else:
                role_str = str(role_value)
        else:
            role_str = Role.VIEWER.value

        roles = [role_str]

        # Calculate permissions based on role
        permissions: list[str] = []
        try:
            role_enum = Role(role_str)
            role_perms = ROLE_PERMISSIONS.get(role_enum, set())
            permissions = [p.value for p in role_perms]
        except ValueError:
            # Unknown role, grant minimal permissions
            permissions = [Permission.DASHBOARD_VIEW.value, Permission.MODELS_READ.value]

        return cls(
            id=user_id,
            email=email,
            roles=roles,
            permissions=permissions,
            password_hash=password_hash,
            name=name,
            is_active=is_active,
        )


def hash_password(password: str) -> str:
    """Hash a password using SHA-256.

    Note: This is a simple hash for demo purposes only.
    In production, use bcrypt, argon2, or similar secure hashing.

    Args:
        password: The plaintext password to hash.

    Returns:
        The hashed password as a hex string.
    """
    return hashlib.sha256(password.encode()).hexdigest()


async def verify_password(stored_hash: str, password: str) -> bool:
    """Verify a password against a stored hash.

    Note: This is a simple comparison for demo purposes only.
    In production, use bcrypt.checkpw or similar secure verification.

    Args:
        stored_hash: The stored password hash.
        password: The plaintext password to verify.

    Returns:
        True if the password matches, False otherwise.
    """
    computed_hash = hash_password(password)
    return computed_hash == stored_hash


def create_user_loader(session_factory: Callable[[], AsyncSession]) -> Callable[[str | int], DemoAdminUser | None]:
    """Create a user loader function for the JWT backend.

    The user loader is called by the JWT backend to load a user by their
    identifier (email for login, user ID for token verification).

    Args:
        session_factory: A callable that returns an AsyncSession.

    Returns:
        An async function that loads a user by email or ID.
    """

    async def user_loader(identifier: str | int) -> DemoAdminUser | None:
        """Load a user by email or ID.

        Args:
            identifier: Either the user's email (for login) or ID (for token verification).

        Returns:
            A DemoAdminUser instance if found, None otherwise.
        """
        from sqlalchemy import select

        from examples.full.models import User

        async with session_factory() as session:
            # Try to find by email first (for login)
            if isinstance(identifier, str) and "@" in identifier:
                stmt = select(User).where(User.email == identifier)
            else:
                # Find by ID (for token verification)
                try:
                    user_id = int(identifier)
                except (TypeError, ValueError):
                    return None
                stmt = select(User).where(User.id == user_id)

            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if user is None:
                return None

            if not user.is_active:
                return None

            return DemoAdminUser.from_db_user(user)

    return user_loader


def get_auth_backend(session_factory: Callable[[], AsyncSession]) -> JWTAuthBackend:
    """Create and configure the JWT authentication backend.

    Args:
        session_factory: A callable that returns an AsyncSession for database access.

    Returns:
        A configured JWTAuthBackend instance.

    Example:
        >>> from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
        >>> engine = create_async_engine("sqlite+aiosqlite:///demo.db")
        >>> session_factory = async_sessionmaker(engine, expire_on_commit=False)
        >>> backend = get_auth_backend(session_factory)
    """
    config = JWTConfig(
        secret_key=DEMO_SECRET_KEY,
        algorithm="HS256",
        token_expiry=3600,  # 1 hour
        refresh_token_expiry=86400,  # 24 hours
        token_location="header",
        cookie_secure=False,  # Allow HTTP for local development
    )

    user_loader = create_user_loader(session_factory)

    return JWTAuthBackend(
        config=config,
        user_loader=user_loader,
        password_verifier=verify_password,
    )
