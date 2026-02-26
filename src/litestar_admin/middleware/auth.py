"""Authentication Middleware for the admin panel.

This middleware extracts authentication from JWT tokens or session data,
setting the user in the connection scope for use by guards.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from litestar.connection import ASGIConnection
from litestar.middleware import AbstractMiddleware

if TYPE_CHECKING:
    from litestar.types import ASGIApp, Receive, Scope, Send

    from litestar_admin.auth.protocols import AuthBackend
    from litestar_admin.config import AdminConfig

__all__ = ["AdminAuthMiddleware", "JWTAuthMiddleware", "create_auth_middleware", "create_jwt_auth_middleware"]

_logger = logging.getLogger(__name__)


class AdminAuthMiddleware(AbstractMiddleware):
    """Middleware that handles authentication for admin routes.

    Supports both JWT (Bearer token) and session-based authentication.
    For JWT backends, extracts tokens from Authorization headers.
    For session backends, delegates to ``auth_backend.get_current_user()``.
    """

    def __init__(self, app: ASGIApp, auth_backend: AuthBackend) -> None:
        """Initialize the middleware.

        Args:
            app: The ASGI application.
            auth_backend: The auth backend for user resolution.
        """
        super().__init__(app)
        self.auth_backend = auth_backend

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process the request and extract the authenticated user.

        Args:
            scope: The ASGI scope.
            receive: The receive channel.
            send: The send channel.
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if any(
            skip_path in path
            for skip_path in [
                "/api/auth/login",
                "/api/auth/logout",
                "/api/auth/refresh",
                "/api/auth/oauth",
                "/api/config",
            ]
        ):
            await self.app(scope, receive, send)
            return

        user = await self._get_user(scope)
        if user is not None:
            scope["user"] = user
            await self.app(scope, receive, send)
            return

        # No authenticated user — return 404 to avoid leaking admin existence
        await self._send_not_found(send)

    @staticmethod
    async def _send_not_found(send: Send) -> None:
        """Send a plain 404 response to avoid leaking admin panel existence."""
        await send({
            "type": "http.response.start",
            "status": 404,
            "headers": [(b"content-type", b"text/plain")],
        })
        await send({
            "type": "http.response.body",
            "body": b"Not Found",
        })

    async def _get_user(self, scope: Scope) -> Any | None:
        """Try to authenticate via Bearer token first, then fall back to session."""
        from litestar_admin.auth.jwt import JWTAuthBackend

        # If JWT backend, try token extraction first
        if isinstance(self.auth_backend, JWTAuthBackend):
            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode("utf-8")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                try:
                    user = await self.auth_backend.get_user_from_token(token)
                    if user is not None:
                        return user
                except Exception as e:
                    _logger.debug("Token validation failed: %s", e)

        # Fall back to get_current_user (works for both session and JWT backends)
        try:
            connection = ASGIConnection(scope)
            return await self.auth_backend.get_current_user(connection)
        except Exception as e:
            _logger.debug("Auth check failed: %s", e)
            return None


# Backward compatibility alias
JWTAuthMiddleware = AdminAuthMiddleware


def create_auth_middleware(admin_config: AdminConfig) -> type[AdminAuthMiddleware] | None:
    """Create an auth middleware class configured with the admin's auth backend.

    Args:
        admin_config: The admin configuration containing the auth backend.

    Returns:
        A middleware class configured with the auth backend, or None if no backend.
    """
    if admin_config.auth_backend is None:
        return None

    auth_backend = admin_config.auth_backend

    class ConfiguredAuthMiddleware(AdminAuthMiddleware):
        def __init__(self, app: ASGIApp) -> None:
            super().__init__(app, auth_backend)

    return ConfiguredAuthMiddleware


# Backward compatibility alias
create_jwt_auth_middleware = create_auth_middleware
