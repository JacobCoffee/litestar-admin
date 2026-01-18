"""AuthController for authentication operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from litestar import Controller, get, post
from litestar.exceptions import NotAuthorizedException, PermissionDeniedException
from litestar.status_codes import HTTP_200_OK

if TYPE_CHECKING:
    from litestar.connection import ASGIConnection

from litestar_admin.config import AdminConfig  # noqa: TC001

__all__ = [
    "AuthController",
    "LoginRequest",
    "LogoutResponse",
    "RefreshRequest",
    "TokenResponse",
    "UserResponse",
]


@dataclass
class LoginRequest:
    """Request payload for user login.

    Attributes:
        email: The user's email address.
        password: The user's password.
    """

    email: str
    password: str


@dataclass
class RefreshRequest:
    """Request payload for token refresh.

    Attributes:
        refresh_token: The refresh token to exchange for a new access token.
    """

    refresh_token: str


@dataclass
class TokenResponse:
    """Response containing authentication tokens.

    Attributes:
        access_token: The JWT access token for authenticated requests.
        refresh_token: The refresh token for obtaining new access tokens.
        token_type: The token type, typically "bearer".
        expires_in: Token expiry time in seconds.
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105
    expires_in: str | None = None


@dataclass
class UserResponse:
    """Response containing current user information.

    Attributes:
        id: The user's unique identifier.
        email: The user's email address.
        roles: List of role names assigned to the user.
        permissions: List of permission strings the user has.
    """

    id: str | int
    email: str
    roles: list[str]
    permissions: list[str]


@dataclass
class LogoutResponse:
    """Response for logout operation.

    Attributes:
        success: Whether the logout was successful.
        message: Optional message describing the result.
    """

    success: bool
    message: str = "Logged out successfully"


class AuthController(Controller):
    """Controller for authentication operations.

    Provides REST API endpoints for user authentication, token management,
    and session handling in the admin panel.

    Example:
        The controller is automatically registered by AdminPlugin.
        Access endpoints at:
        - POST /admin/api/auth/login - Authenticate with email/password
        - POST /admin/api/auth/logout - End the current session
        - POST /admin/api/auth/refresh - Refresh access token
        - GET /admin/api/auth/me - Get current user information
    """

    path = "/api/auth"
    tags: ClassVar[list[str]] = ["Authentication"]

    @post(
        "/login",
        status_code=HTTP_200_OK,
        summary="Authenticate user",
        description="Authenticate a user with email and password credentials. Returns access and refresh tokens.",
    )
    async def login(
        self,
        data: LoginRequest,
        admin_config: AdminConfig,
        request: ASGIConnection,
    ) -> TokenResponse:
        """Authenticate a user with email and password.

        Args:
            data: Login credentials containing email and password.
            admin_config: The admin configuration containing the auth backend.
            request: The current ASGI connection.

        Returns:
            TokenResponse containing access and refresh tokens.

        Raises:
            NotAuthorizedException: If authentication fails or no auth backend is configured.
        """
        if admin_config.auth_backend is None:
            raise NotAuthorizedException(detail="Authentication is not configured")

        # Authenticate user with credentials
        user = await admin_config.auth_backend.authenticate(
            request,
            {"email": data.email, "password": data.password},
        )

        if user is None:
            raise NotAuthorizedException(detail="Invalid email or password")

        # Create session/tokens for authenticated user
        tokens = await admin_config.auth_backend.login(request, user)

        return TokenResponse(
            access_token=tokens.get("access_token", ""),
            refresh_token=tokens.get("refresh_token", ""),
            token_type=tokens.get("token_type", "bearer"),
            expires_in=tokens.get("expires_in"),
        )

    @post(
        "/logout",
        status_code=HTTP_200_OK,
        summary="Logout user",
        description="End the current user session and invalidate tokens.",
    )
    async def logout(
        self,
        admin_config: AdminConfig,
        request: ASGIConnection,
    ) -> LogoutResponse:
        """End the current user session.

        Args:
            admin_config: The admin configuration containing the auth backend.
            request: The current ASGI connection.

        Returns:
            LogoutResponse indicating successful logout.

        Raises:
            NotAuthorizedException: If no auth backend is configured.
        """
        if admin_config.auth_backend is None:
            raise NotAuthorizedException(detail="Authentication is not configured")

        await admin_config.auth_backend.logout(request)

        return LogoutResponse(success=True, message="Logged out successfully")

    @post(
        "/refresh",
        status_code=HTTP_200_OK,
        summary="Refresh access token",
        description="Exchange a refresh token for a new access token.",
    )
    async def refresh(
        self,
        data: RefreshRequest,
        admin_config: AdminConfig,
        request: ASGIConnection,
    ) -> TokenResponse:
        """Refresh the access token using a refresh token.

        Args:
            data: Request containing the refresh token.
            admin_config: The admin configuration containing the auth backend.
            request: The current ASGI connection.

        Returns:
            TokenResponse containing the new access token.

        Raises:
            NotAuthorizedException: If refresh fails or no auth backend is configured.
        """
        if admin_config.auth_backend is None:
            raise NotAuthorizedException(detail="Authentication is not configured")

        # Store refresh token in request state for the backend to access
        request.state.refresh_token = data.refresh_token

        tokens = await admin_config.auth_backend.refresh(request)

        if tokens is None:
            raise NotAuthorizedException(detail="Invalid or expired refresh token")

        return TokenResponse(
            access_token=tokens.get("access_token", ""),
            refresh_token=tokens.get("refresh_token", data.refresh_token),
            token_type=tokens.get("token_type", "bearer"),
            expires_in=tokens.get("expires_in"),
        )

    @get(
        "/me",
        status_code=HTTP_200_OK,
        summary="Get current user",
        description="Return information about the currently authenticated user.",
    )
    async def me(
        self,
        admin_config: AdminConfig,
        request: ASGIConnection,
    ) -> UserResponse:
        """Get the currently authenticated user's information.

        Args:
            admin_config: The admin configuration containing the auth backend.
            request: The current ASGI connection.

        Returns:
            UserResponse containing current user information.

        Raises:
            NotAuthorizedException: If no auth backend is configured.
            PermissionDeniedException: If the user is not authenticated.
        """
        if admin_config.auth_backend is None:
            raise NotAuthorizedException(detail="Authentication is not configured")

        user = await admin_config.auth_backend.get_current_user(request)

        if user is None:
            raise PermissionDeniedException(detail="Not authenticated")

        return UserResponse(
            id=user.id,
            email=user.email,
            roles=user.roles,
            permissions=user.permissions,
        )
