"""Authentication protocols for admin panel."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from litestar.connection import ASGIConnection

__all__ = ["AdminUserProtocol", "AuthBackend"]


@runtime_checkable
class AdminUserProtocol(Protocol):
    """Protocol for admin user objects.

    Any user class that implements this protocol can be used with the admin panel.
    This includes the concrete AdminUser model from litestar_admin.auth.models.

    Attributes:
        id: Unique identifier for the user.
        email: User's email address.
        roles: List of role names assigned to the user.
        permissions: List of permission strings the user has.
    """

    @property
    def id(self) -> str | int:
        """Return the user's unique identifier."""
        ...

    @property
    def email(self) -> str:
        """Return the user's email address."""
        ...

    @property
    def roles(self) -> list[str]:
        """Return the user's role names."""
        ...

    @property
    def permissions(self) -> list[str]:
        """Return the user's permission strings."""
        ...


@runtime_checkable
class AuthBackend(Protocol):
    """Protocol for authentication backends.

    Implementations of this protocol handle user authentication,
    token management, and session handling for the admin panel.
    """

    async def authenticate(
        self,
        connection: ASGIConnection,
        credentials: dict[str, str],
    ) -> AdminUserProtocol | None:
        """Authenticate a user with credentials.

        Args:
            connection: The current ASGI connection.
            credentials: Dictionary containing authentication credentials.

        Returns:
            The authenticated user, or None if authentication failed.
        """
        ...

    async def get_current_user(
        self,
        connection: ASGIConnection,
    ) -> AdminUserProtocol | None:
        """Get the currently authenticated user.

        Args:
            connection: The current ASGI connection.

        Returns:
            The current user, or None if not authenticated.
        """
        ...

    async def login(
        self,
        connection: ASGIConnection,
        user: AdminUserProtocol,
    ) -> dict[str, str]:
        """Create a session for the user.

        Args:
            connection: The current ASGI connection.
            user: The user to log in.

        Returns:
            Dictionary containing session tokens (e.g., access_token, refresh_token).
        """
        ...

    async def logout(
        self,
        connection: ASGIConnection,
    ) -> None:
        """Destroy the current session.

        Args:
            connection: The current ASGI connection.
        """
        ...

    async def refresh(
        self,
        connection: ASGIConnection,
    ) -> dict[str, str] | None:
        """Refresh the current session tokens.

        Args:
            connection: The current ASGI connection.

        Returns:
            Dictionary containing new tokens, or None if refresh failed.
        """
        ...
