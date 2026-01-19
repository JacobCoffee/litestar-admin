"""OAuthController for OAuth authentication operations."""

from __future__ import annotations

import secrets
from typing import Any, ClassVar

from litestar import Controller, get
from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException, NotFoundException
from litestar.response import Redirect
from litestar.status_codes import HTTP_200_OK

from litestar_admin.config import AdminConfig  # noqa: TC001

__all__ = ["OAuthController"]


class OAuthController(Controller):
    """Controller for OAuth authentication operations.

    Provides REST API endpoints for OAuth login flow including
    initiating authentication and handling callbacks.

    Example:
        Access endpoints at:
        - GET /admin/auth/oauth/{provider}/login - Initiate OAuth flow
        - GET /admin/auth/oauth/{provider}/callback - Handle OAuth callback
    """

    path = "/auth/oauth"
    tags: ClassVar[list[str]] = ["OAuth Authentication"]

    @get(
        "/{provider:str}/login",
        status_code=HTTP_200_OK,
        summary="Initiate OAuth login",
        description="Redirect user to OAuth provider for authentication.",
    )
    async def oauth_login(
        self,
        provider: str,
        admin_config: AdminConfig,
    ) -> Redirect:
        """Initiate OAuth login flow.

        Redirects the user to the OAuth provider's authorization page.

        Args:
            provider: The OAuth provider name (e.g., "github", "demo").
            admin_config: The admin configuration containing the auth backend.

        Returns:
            Redirect to the OAuth provider's authorization URL.

        Raises:
            NotFoundException: If the provider is not configured.
            NotAuthorizedException: If OAuth is not configured.
        """
        if admin_config.auth_backend is None:
            raise NotAuthorizedException(detail="Authentication is not configured")

        # Check if this is an OAuth backend with the required method
        if not hasattr(admin_config.auth_backend, "get_authorization_url"):
            raise NotFoundException(detail=f"OAuth provider '{provider}' not found")

        try:
            auth_url, _ = admin_config.auth_backend.get_authorization_url(provider)
            return Redirect(path=auth_url)
        except ValueError as e:
            raise NotFoundException(detail=str(e)) from e

    @get(
        "/demo/authorize",
        status_code=HTTP_200_OK,
        summary="Demo OAuth authorize",
        description="Simulated OAuth authorization for demo provider.",
    )
    async def demo_authorize(
        self,
        request: ASGIConnection,
        admin_config: AdminConfig,
    ) -> Redirect:
        """Simulate OAuth authorization for demo provider.

        This endpoint simulates the OAuth provider's authorize page.
        In a real OAuth flow, users would be redirected to the provider's
        login page. For demo purposes, we immediately redirect back to
        the callback with a mock authorization code.

        Args:
            request: The ASGI connection to access query params.
            admin_config: The admin configuration.

        Returns:
            Redirect to the callback URL with a mock authorization code.
        """
        # Get state from query params (can't use 'state' as param name - reserved by Litestar)
        state_value = request.query_params.get("state")

        # Generate a mock authorization code
        mock_code = secrets.token_urlsafe(32)

        # Build callback URL - use 'state' in the URL since that's what OAuth spec uses
        base_url = admin_config.base_url
        callback_url = f"{base_url}/auth/oauth/demo/callback?code={mock_code}"
        if state_value:
            callback_url += f"&state={state_value}"

        return Redirect(path=callback_url)

    @get(
        "/{provider:str}/callback",
        status_code=HTTP_200_OK,
        summary="OAuth callback",
        description="Handle OAuth provider callback after authentication.",
    )
    async def oauth_callback(
        self,
        provider: str,
        code: str,
        admin_config: AdminConfig,
        request: ASGIConnection,
    ) -> Redirect | dict[str, Any]:
        """Handle OAuth callback from provider.

        Exchanges the authorization code for tokens and authenticates the user.

        Args:
            provider: The OAuth provider name.
            code: The authorization code from the provider.
            admin_config: The admin configuration containing the auth backend.
            request: The current ASGI connection.

        Returns:
            Redirect to the admin dashboard with session established, or
            token response for API clients.

        Raises:
            NotAuthorizedException: If authentication fails.
        """
        if admin_config.auth_backend is None:
            raise NotAuthorizedException(detail="Authentication is not configured")

        # Check if this is an OAuth backend
        if not hasattr(admin_config.auth_backend, "handle_callback"):
            raise NotAuthorizedException(detail="OAuth not configured")

        # Get state from query params (can't use 'state' as param name - reserved by Litestar)
        state_value = request.query_params.get("state")

        # Handle the callback
        user, tokens = await admin_config.auth_backend.handle_callback(
            provider_name=provider,
            code=code,
            state=state_value,
        )

        if user is None:
            raise NotAuthorizedException(detail="OAuth authentication failed")

        # Create session tokens
        session_tokens = await admin_config.auth_backend.login(request, user)

        # For browser clients, redirect to admin with token in URL fragment
        # The frontend will extract and store the token
        access_token = session_tokens.get("access_token", "")
        base_url = admin_config.base_url

        # Redirect with token as URL fragment (not visible to server on subsequent requests)
        return Redirect(path=f"{base_url}?token={access_token}")
