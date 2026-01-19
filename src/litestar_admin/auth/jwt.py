"""JWT authentication backend for litestar-admin.

This module provides a JWT-based authentication backend that implements
the AuthBackend protocol. It supports both header and cookie-based token
authentication with configurable options.

Example:
    Basic usage with a user loader function:

    >>> from litestar_admin.auth.jwt import JWTAuthBackend, JWTConfig
    >>>
    >>> async def load_user(user_id: str | int) -> AdminUser | None:
    ...     return await user_repository.get(user_id)
    >>>
    >>> config = JWTConfig(secret_key="your-secret-key")
    >>> backend = JWTAuthBackend(config=config, user_loader=load_user)
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from litestar.connection import ASGIConnection

    from litestar_admin.auth.protocols import AdminUserProtocol

__all__ = ["JWTAuthBackend", "JWTConfig"]


@dataclass
class JWTConfig:
    """Configuration for JWT authentication.

    This dataclass holds all configuration options for the JWT authentication
    backend. It supports both header-based and cookie-based token storage.

    Attributes:
        secret_key: Secret key used for signing JWT tokens. Required.
        algorithm: JWT signing algorithm. Defaults to "HS256".
        token_expiry: Access token expiry time in seconds. Defaults to 3600 (1 hour).
        refresh_token_expiry: Refresh token expiry time in seconds. Defaults to 86400 (24 hours).
        token_location: Where to look for tokens ("header" or "cookie"). Defaults to "header".
        token_header: Header name for token extraction. Defaults to "Authorization".
        token_prefix: Prefix for header-based tokens. Defaults to "Bearer".
        cookie_name: Cookie name for token storage. Defaults to "admin_access_token".
        cookie_secure: Whether cookie should only be sent over HTTPS. Defaults to True.
        cookie_httponly: Whether cookie should be HTTP-only. Defaults to True.
        cookie_samesite: SameSite cookie attribute. Defaults to "lax".
        issuer: Optional token issuer claim.
        audience: Optional token audience claim.

    Example:
        >>> config = JWTConfig(
        ...     secret_key="my-secret-key",
        ...     algorithm="HS256",
        ...     token_expiry=7200,
        ... )
    """

    secret_key: str
    algorithm: str = "HS256"
    token_expiry: int = 3600  # 1 hour in seconds
    refresh_token_expiry: int = 86400  # 24 hours in seconds
    token_location: str = "header"  # noqa: S105  # "header" or "cookie"
    token_header: str = "Authorization"  # noqa: S105
    token_prefix: str = "Bearer"  # noqa: S105
    cookie_name: str = "admin_access_token"
    cookie_secure: bool = True
    cookie_httponly: bool = True
    cookie_samesite: str = "lax"
    issuer: str | None = None
    audience: str | None = None

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if not self.secret_key:
            msg = "secret_key is required and cannot be empty"
            raise ValueError(msg)

        if self.token_location not in ("header", "cookie"):
            msg = f"token_location must be 'header' or 'cookie', got '{self.token_location}'"
            raise ValueError(msg)

        if self.token_expiry < 1:
            msg = "token_expiry must be at least 1 second"
            raise ValueError(msg)

        if self.refresh_token_expiry < 1:
            msg = "refresh_token_expiry must be at least 1 second"
            raise ValueError(msg)

        if self.cookie_samesite.lower() not in ("strict", "lax", "none"):
            msg = f"cookie_samesite must be 'strict', 'lax', or 'none', got '{self.cookie_samesite}'"
            raise ValueError(msg)


class JWTAuthBackend:
    """JWT-based authentication backend.

    This class implements the AuthBackend protocol using JSON Web Tokens
    for authentication. It supports both access and refresh tokens with
    configurable expiry times.

    The backend requires a user_loader callable that takes a user ID and
    returns an AdminUser object (or None if not found). Optionally, a
    password_verifier callable can be provided for credential authentication.

    Attributes:
        config: JWT configuration options.
        user_loader: Async callable to load user by ID.
        password_verifier: Optional async callable to verify passwords.

    Example:
        >>> async def load_user(user_id: str | int) -> AdminUser | None:
        ...     return await db.get_user(user_id)
        >>>
        >>> async def verify_password(stored_hash: str, password: str) -> bool:
        ...     return bcrypt.checkpw(password.encode(), stored_hash.encode())
        >>>
        >>> config = JWTConfig(secret_key="secret")
        >>> backend = JWTAuthBackend(
        ...     config=config,
        ...     user_loader=load_user,
        ...     password_verifier=verify_password,
        ... )
    """

    def __init__(
        self,
        config: JWTConfig,
        user_loader: Callable[[str | int], Awaitable[AdminUserProtocol | None]],
        password_verifier: Callable[[str, str], Awaitable[bool]] | None = None,
        password_hasher: Callable[[str], Awaitable[str]] | None = None,
        password_updater: Callable[[str | int, str], Awaitable[bool]] | None = None,
    ) -> None:
        """Initialize the JWT authentication backend.

        Args:
            config: JWT configuration options.
            user_loader: Async callable that takes a user ID and returns an AdminUser or None.
            password_verifier: Optional async callable that takes (stored_hash, password) and returns bool.
            password_hasher: Optional async callable that takes a plain password and returns a hash.
            password_updater: Optional async callable that takes (user_id, new_hash) and updates the password.
        """
        self.config = config
        self.user_loader = user_loader
        self.password_verifier = password_verifier
        self.password_hasher = password_hasher
        self.password_updater = password_updater

    async def authenticate(
        self,
        connection: ASGIConnection,  # noqa: ARG002
        credentials: dict[str, str],
    ) -> AdminUserProtocol | None:
        """Authenticate a user with email/password credentials.

        This method validates the provided credentials against the user database.
        If authentication succeeds, it returns the authenticated AdminUser.

        Args:
            connection: The current ASGI connection.
            credentials: Dictionary containing 'email' and 'password' keys.

        Returns:
            The authenticated AdminUser if credentials are valid, None otherwise.
        """
        email = credentials.get("email")
        password = credentials.get("password")

        if not email or not password:
            return None

        # Load user by email (user_loader can accept email as identifier)
        user = await self.user_loader(email)
        if user is None:
            return None

        # Verify password if verifier is configured
        if self.password_verifier:
            # Get password hash from user object (commonly stored as password_hash attribute)
            password_hash = getattr(user, "password_hash", None) or getattr(user, "hashed_password", None)
            if password_hash is None:
                return None
            if not await self.password_verifier(password_hash, password):
                return None

        return user

    async def get_current_user(
        self,
        connection: ASGIConnection,
    ) -> AdminUserProtocol | None:
        """Get the currently authenticated user from the request.

        Extracts the JWT token from the request (header or cookie based on config),
        decodes it, and loads the corresponding user.

        Args:
            connection: The current ASGI connection.

        Returns:
            The current AdminUser if authenticated, None otherwise.
        """
        token = self._extract_token(connection)
        if token is None:
            return None

        payload = self._decode_token(token)
        if payload is None:
            return None

        # Check if this is a refresh token (not allowed for authentication)
        if payload.get("type") == "refresh":
            return None

        user_id = payload.get("sub")
        if user_id is None:
            return None

        return await self.user_loader(user_id)

    async def login(
        self,
        connection: ASGIConnection,  # noqa: ARG002
        user: AdminUserProtocol,
    ) -> dict[str, str]:
        """Create a session for the authenticated user.

        Generates access and refresh tokens for the user.

        Args:
            connection: The current ASGI connection.
            user: The authenticated user to create a session for.

        Returns:
            Dictionary containing 'access_token', 'refresh_token', and 'token_type' keys.
        """
        access_token = self._create_token(user, kind="access")
        refresh_token = self._create_token(user, kind="refresh")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": str(self.config.token_expiry),
        }

    async def logout(
        self,
        connection: ASGIConnection,
    ) -> None:
        """Destroy the current session.

        For stateless JWT authentication, this is typically a no-op on the server side.
        Token invalidation should be handled by the client (discarding tokens) or
        by implementing a token blacklist if needed.

        Args:
            connection: The current ASGI connection.
        """
        # JWT is stateless - actual logout is handled by client discarding tokens
        # For stateful logout, implement a token blacklist

    async def refresh(
        self,
        connection: ASGIConnection,
    ) -> dict[str, str] | None:
        """Refresh the current session tokens.

        Validates the refresh token and generates a new access token.

        Args:
            connection: The current ASGI connection.

        Returns:
            Dictionary containing new tokens, or None if refresh failed.
        """
        # Try to extract refresh token from request body or header
        refresh_token = self._extract_refresh_token(connection)
        if refresh_token is None:
            return None

        payload = self._decode_token(refresh_token)
        if payload is None:
            return None

        # Verify this is a refresh token
        if payload.get("type") != "refresh":
            return None

        user_id = payload.get("sub")
        if user_id is None:
            return None

        user = await self.user_loader(user_id)
        if user is None:
            return None

        # Generate new access token
        access_token = self._create_token(user, kind="access")

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": str(self.config.token_expiry),
        }

    async def change_password(
        self,
        connection: ASGIConnection,
        current_password: str,
        new_password: str,
    ) -> bool:
        """Change the current user's password.

        Validates the current password and updates to the new password.

        Args:
            connection: The current ASGI connection.
            current_password: The user's current password.
            new_password: The new password to set.

        Returns:
            True if password was changed successfully, False otherwise.
        """
        # Get current user
        user = await self.get_current_user(connection)
        if user is None:
            return False

        # Check if password operations are configured
        if not self.password_verifier or not self.password_hasher or not self.password_updater:
            return False

        # Verify current password
        password_hash = getattr(user, "password_hash", None) or getattr(user, "hashed_password", None)
        if password_hash is None:
            return False

        if not await self.password_verifier(password_hash, current_password):
            return False

        # Hash new password and update
        new_hash = await self.password_hasher(new_password)
        return await self.password_updater(user.id, new_hash)

    def _create_token(self, user: AdminUserProtocol, kind: str = "access") -> str:
        """Create a JWT token for a user.

        Args:
            user: The user to create a token for.
            kind: Type of token ("access" or "refresh").

        Returns:
            Encoded JWT token string.
        """
        try:
            import jwt
        except ImportError as e:
            msg = "PyJWT is required for JWT authentication. Install it with: pip install 'litestar-admin[jwt]'"
            raise ImportError(msg) from e

        now = datetime.datetime.now(tz=datetime.timezone.utc)

        expiry = self.config.token_expiry if kind == "access" else self.config.refresh_token_expiry
        exp = now + datetime.timedelta(seconds=expiry)

        payload: dict[str, Any] = {
            "sub": str(user.id),
            "email": user.email,
            "roles": user.roles,
            "permissions": user.permissions,
            "type": kind,
            "iat": now,
            "exp": exp,
        }

        if self.config.issuer:
            payload["iss"] = self.config.issuer
        if self.config.audience:
            payload["aud"] = self.config.audience

        return jwt.encode(
            payload,
            self.config.secret_key,
            algorithm=self.config.algorithm,
        )

    def _decode_token(self, token: str) -> dict[str, Any] | None:
        """Decode and validate a JWT token.

        Args:
            token: The JWT token string to decode.

        Returns:
            The decoded token payload, or None if invalid.
        """
        try:
            import jwt
        except ImportError as e:
            msg = "PyJWT is required for JWT authentication. Install it with: pip install 'litestar-admin[jwt]'"
            raise ImportError(msg) from e

        try:
            options: dict[str, Any] = {}
            if self.config.audience:
                options["audience"] = self.config.audience

            return jwt.decode(
                token,
                self.config.secret_key,
                algorithms=[self.config.algorithm],
                options=options,
            )
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def _extract_token(self, connection: ASGIConnection) -> str | None:
        """Extract the JWT token from the request.

        Looks for the token in the configured location (header or cookie).
        If token_location is "header", also falls back to checking cookies.

        Args:
            connection: The current ASGI connection.

        Returns:
            The extracted token string, or None if not found.
        """
        # Try header first if configured
        if self.config.token_location == "header":  # noqa: S105
            auth_header = connection.headers.get(self.config.token_header)
            if auth_header:
                prefix = f"{self.config.token_prefix} "
                if auth_header.startswith(prefix):
                    return auth_header[len(prefix) :]
                # Also try without prefix for flexibility
                if not auth_header.startswith(("Bearer ", "bearer ")):
                    return auth_header

        # Try cookie
        cookie_value = connection.cookies.get(self.config.cookie_name)
        if cookie_value:
            return cookie_value

        # Fallback: if token_location is cookie, also try header
        if self.config.token_location == "cookie":  # noqa: S105
            auth_header = connection.headers.get(self.config.token_header)
            if auth_header:
                prefix = f"{self.config.token_prefix} "
                if auth_header.startswith(prefix):
                    return auth_header[len(prefix) :]

        return None

    def _extract_refresh_token(self, connection: ASGIConnection) -> str | None:
        """Extract the refresh token from the request.

        Looks for refresh token in request body, headers, or cookies.

        Args:
            connection: The current ASGI connection.

        Returns:
            The extracted refresh token string, or None if not found.
        """
        # Try to get from request state (set by controller)
        if hasattr(connection, "state"):
            refresh_token = getattr(connection.state, "refresh_token", None)
            if refresh_token:
                return refresh_token

        # Try dedicated refresh token header
        refresh_header = connection.headers.get("X-Refresh-Token")
        if refresh_header:
            return refresh_header

        # Try refresh token cookie
        refresh_cookie = connection.cookies.get("admin_refresh_token")
        if refresh_cookie:
            return refresh_cookie

        # Fall back to access token location for refresh endpoint
        return self._extract_token(connection)
