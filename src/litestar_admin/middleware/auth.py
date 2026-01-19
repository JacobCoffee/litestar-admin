"""JWT Authentication Middleware for the admin panel.

This middleware extracts JWT tokens from request headers and validates them,
setting the user in the connection scope for use by guards.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from litestar.middleware import AbstractMiddleware
from litestar.types import ASGIApp, Receive, Scope, Send

if TYPE_CHECKING:
    from litestar_admin.auth.jwt import JWTAuthBackend
    from litestar_admin.config import AdminConfig

__all__ = ["JWTAuthMiddleware", "create_jwt_auth_middleware"]

_logger = logging.getLogger(__name__)


class JWTAuthMiddleware(AbstractMiddleware):
    """Middleware that handles JWT authentication for admin routes.

    Extracts JWT tokens from Authorization headers and validates them,
    setting the authenticated user in the connection scope.
    """

    def __init__(self, app: ASGIApp, auth_backend: JWTAuthBackend) -> None:
        """Initialize the middleware.

        Args:
            app: The ASGI application.
            auth_backend: The JWT auth backend for token validation.
        """
        super().__init__(app)
        self.auth_backend = auth_backend

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process the request and extract user from JWT token.

        Args:
            scope: The ASGI scope.
            receive: The receive channel.
            send: The send channel.
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Skip auth for login, logout, refresh, and oauth endpoints
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

        # Try to extract and validate token
        user = await self._get_user_from_token(scope)
        if user is not None:
            scope["user"] = user

        await self.app(scope, receive, send)

    async def _get_user_from_token(self, scope: Scope) -> Any | None:
        """Extract and validate JWT token, returning the user if valid.

        Args:
            scope: The ASGI scope containing headers.

        Returns:
            The authenticated user, or None if no valid token.
        """
        # Get Authorization header
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization", b"").decode("utf-8")

        if not auth_header.startswith("Bearer "):
            return None

        token = auth_header[7:]  # Remove "Bearer " prefix

        try:
            # Validate token and get user
            user = await self.auth_backend.get_user_from_token(token)
            return user
        except Exception as e:
            _logger.debug(f"Token validation failed: {e}")
            return None


def create_jwt_auth_middleware(admin_config: AdminConfig) -> type[JWTAuthMiddleware] | None:
    """Create a JWT auth middleware class configured with the admin's auth backend.

    Args:
        admin_config: The admin configuration containing the auth backend.

    Returns:
        A middleware class configured with the auth backend, or None if no backend.
    """
    if admin_config.auth_backend is None:
        return None

    auth_backend = admin_config.auth_backend

    class ConfiguredJWTAuthMiddleware(JWTAuthMiddleware):
        def __init__(self, app: ASGIApp) -> None:
            super().__init__(app, auth_backend)

    return ConfiguredJWTAuthMiddleware
