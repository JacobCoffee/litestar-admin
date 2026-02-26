"""Session-based authentication backend for litestar-admin.

This module provides a session-based authentication backend that implements
the AuthBackend protocol. It reads from the host app's existing session middleware,
following the same pattern as Litestar's built-in ``SessionAuth``.

Example:
    Usage with a retrieve_user_handler::

        >>> from litestar_admin.auth.session import SessionAuthBackend
        >>>
        >>> async def retrieve_user_handler(session: dict, connection: ASGIConnection) -> AdminUser | None:
        ...     user_id = session.get("user_id")
        ...     if not user_id:
        ...         return None
        ...     return await load_admin_user(user_id)
        >>>
        >>> backend = SessionAuthBackend(retrieve_user_handler=retrieve_user_handler)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from litestar.connection import ASGIConnection

    from litestar_admin.auth.protocols import AdminUserProtocol

__all__ = ["SessionAuthBackend"]

_logger = logging.getLogger(__name__)


class SessionAuthBackend:
    """Session-based authentication backend.

    This backend delegates to the host application's session middleware,
    following the same ``retrieve_user_handler(session, connection)`` pattern
    as Litestar's built-in :class:`~litestar.security.session_auth.SessionAuth`.

    The host app is responsible for configuring session middleware (cookie-based
    or server-side). This backend simply reads from ``connection.session``.

    Args:
        retrieve_user_handler: Async callable matching Litestar's SessionAuth
            signature: ``(session_dict, connection) -> AdminUserProtocol | None``.
        session_key: Key in the session dict that holds the user identifier.
            Defaults to ``"user_id"``.
        authenticate_handler: Optional async callable for email/password login
            via the admin login form. Signature:
            ``(connection, credentials) -> AdminUserProtocol | None``.
    """

    def __init__(
        self,
        retrieve_user_handler: Callable[[dict, ASGIConnection], Awaitable[AdminUserProtocol | None]],
        session_key: str = "user_id",
        authenticate_handler: (
            Callable[[ASGIConnection, dict[str, str]], Awaitable[AdminUserProtocol | None]] | None
        ) = None,
    ) -> None:
        self.retrieve_user_handler = retrieve_user_handler
        self.session_key = session_key
        self.authenticate_handler = authenticate_handler

    async def authenticate(
        self,
        connection: ASGIConnection,
        credentials: dict[str, str],
    ) -> AdminUserProtocol | None:
        """Authenticate a user with email/password credentials.

        Delegates to ``authenticate_handler`` if provided; otherwise returns None
        (session-based auth typically doesn't use the admin login form).
        """
        if self.authenticate_handler is not None:
            return await self.authenticate_handler(connection, credentials)
        return None

    async def get_current_user(
        self,
        connection: ASGIConnection,
    ) -> AdminUserProtocol | None:
        """Get the currently authenticated user from the session.

        Calls ``retrieve_user_handler(connection.session, connection)``
        following the same pattern as Litestar's ``SessionAuth``.
        """
        try:
            session = connection.session
        except Exception:
            _logger.debug("No session available on connection")
            return None

        if not session or not session.get(self.session_key):
            return None

        return await self.retrieve_user_handler(session, connection)

    async def login(
        self,
        connection: ASGIConnection,
        user: AdminUserProtocol,
    ) -> dict[str, str]:
        """Create a session for the user.

        Sets the user ID in the session and returns a response compatible
        with the admin frontend's token storage expectations.
        """
        connection.session[self.session_key] = str(user.id)
        return {
            "access_token": "session",
            "refresh_token": "session",
            "token_type": "session",
        }

    async def logout(
        self,
        connection: ASGIConnection,
    ) -> None:
        """Clear the session key."""
        connection.session.pop(self.session_key, None)

    async def refresh(
        self,
        connection: ASGIConnection,  # noqa: ARG002
    ) -> dict[str, str] | None:
        """No-op for session auth — sessions don't need token refresh."""
        return {
            "access_token": "session",
            "refresh_token": "session",
            "token_type": "session",
        }
