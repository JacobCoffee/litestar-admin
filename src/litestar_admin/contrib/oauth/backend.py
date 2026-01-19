"""OAuth authentication backend for litestar-admin.

This module provides an OAuth-based authentication backend that integrates
with litestar-oauth library and implements the AuthBackend protocol.

Example:
    Basic usage with user loader and creator:

    >>> from litestar_admin.contrib.oauth import (
    ...     OAuthAuthBackend,
    ...     OAuthConfig,
    ...     OAuthProviderConfig,
    ... )
    >>>
    >>> async def load_user(user_id: str | int) -> AdminUser | None:
    ...     return await user_repository.get(user_id)
    >>>
    >>> async def load_user_by_email(email: str) -> AdminUser | None:
    ...     return await user_repository.get_by_email(email)
    >>>
    >>> async def create_user(user_info: OAuthUserInfo) -> AdminUser:
    ...     return await user_repository.create(
    ...         email=user_info.email,
    ...         name=user_info.name,
    ...     )
    >>>
    >>> config = OAuthConfig(
    ...     providers=[
    ...         OAuthProviderConfig(
    ...             name="github",
    ...             client_id="your-client-id",
    ...             client_secret="your-client-secret",
    ...         )
    ...     ],
    ...     redirect_base_url="https://example.com",
    ... )
    >>> backend = OAuthAuthBackend(
    ...     config=config,
    ...     user_loader=load_user,
    ...     user_loader_by_email=load_user_by_email,
    ...     user_creator=create_user,
    ... )
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from litestar_admin.contrib.oauth.config import OAuthConfig, OAuthProviderType

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from litestar.connection import ASGIConnection

    from litestar_admin.auth.protocols import AdminUserProtocol

__all__ = [
    "OAuthAuthBackend",
    "OAuthTokens",
    "OAuthUserInfo",
]


@dataclass
class OAuthUserInfo:
    """Normalized user information from OAuth provider.

    This dataclass holds user information extracted from OAuth providers
    in a consistent format regardless of the provider used.

    Attributes:
        id: Provider-specific user ID.
        email: User's email address.
        name: User's display name (may be None).
        picture: URL to user's profile picture (may be None).
        provider: Name of the OAuth provider.
        raw_data: Raw user data from the provider.
    """

    id: str
    email: str
    name: str | None = None
    picture: str | None = None
    provider: str = ""
    raw_data: dict[str, Any] | None = None


@dataclass
class OAuthTokens:
    """OAuth tokens from provider.

    Attributes:
        access_token: The access token for API requests.
        token_type: Token type (usually "Bearer").
        refresh_token: Optional refresh token for obtaining new access tokens.
        expires_in: Token expiry time in seconds (may be None).
        scope: Granted scopes (may be None).
        id_token: Optional OIDC ID token.
    """

    access_token: str
    token_type: str = "Bearer"  # noqa: S105
    refresh_token: str | None = None
    expires_in: int | None = None
    scope: str | None = None
    id_token: str | None = None


class OAuthAuthBackend:
    """OAuth-based authentication backend.

    This class implements the AuthBackend protocol using OAuth providers
    from litestar-oauth. It supports multiple providers and handles
    user creation, token management, and session handling.

    The backend requires callables for loading users and optionally for
    creating new users on first OAuth login.

    Attributes:
        config: OAuth configuration options.
        user_loader: Async callable to load user by ID.
        user_loader_by_email: Async callable to load user by email.
        user_creator: Optional async callable to create users on first login.
        _providers: Cached provider instances.
        _state_store: Simple state storage for CSRF protection.

    Example:
        >>> async def load_user(user_id: str | int) -> AdminUser | None:
        ...     return await db.get_user(user_id)
        >>>
        >>> async def load_user_by_email(email: str) -> AdminUser | None:
        ...     return await db.get_user_by_email(email)
        >>>
        >>> async def create_user(user_info: OAuthUserInfo) -> AdminUser:
        ...     return await db.create_user(email=user_info.email, name=user_info.name)
        >>>
        >>> config = OAuthConfig(providers=[...], redirect_base_url="https://example.com")
        >>> backend = OAuthAuthBackend(
        ...     config=config,
        ...     user_loader=load_user,
        ...     user_loader_by_email=load_user_by_email,
        ...     user_creator=create_user,
        ... )
    """

    def __init__(
        self,
        config: OAuthConfig,
        user_loader: Callable[[str | int], Awaitable[AdminUserProtocol | None]],
        user_loader_by_email: Callable[[str], Awaitable[AdminUserProtocol | None]],
        user_creator: Callable[[OAuthUserInfo], Awaitable[AdminUserProtocol]] | None = None,
        jwt_secret_key: str | None = None,
        jwt_algorithm: str = "HS256",
        token_expiry: int = 3600,
        refresh_token_expiry: int = 86400,
        password_verifier: Callable[[str, str], Awaitable[bool]] | None = None,
    ) -> None:
        """Initialize the OAuth authentication backend.

        Args:
            config: OAuth configuration options.
            user_loader: Async callable that takes a user ID and returns an AdminUser or None.
            user_loader_by_email: Async callable that takes an email and returns an AdminUser or None.
            user_creator: Optional async callable that takes OAuthUserInfo and creates a new AdminUser.
            jwt_secret_key: Secret key for signing session JWTs. If None, a random key is generated.
            jwt_algorithm: JWT signing algorithm. Defaults to "HS256".
            token_expiry: Access token expiry time in seconds. Defaults to 3600 (1 hour).
            refresh_token_expiry: Refresh token expiry time in seconds. Defaults to 86400 (24 hours).
            password_verifier: Optional async callable for hybrid auth (password + OAuth).
        """
        self.config = config
        self.user_loader = user_loader
        self.user_loader_by_email = user_loader_by_email
        self.user_creator = user_creator
        self.jwt_secret_key = jwt_secret_key or secrets.token_urlsafe(32)
        self.jwt_algorithm = jwt_algorithm
        self.token_expiry = token_expiry
        self.refresh_token_expiry = refresh_token_expiry
        self.password_verifier = password_verifier

        # Provider instances cache
        self._providers: dict[str, Any] = {}

        # Simple state store for CSRF protection (in production, use Redis/database)
        self._state_store: dict[str, str] = {}

    def _get_provider(self, provider_name: str) -> Any:
        """Get or create an OAuth provider instance.

        Args:
            provider_name: Name of the OAuth provider.

        Returns:
            The OAuth provider instance.

        Raises:
            ImportError: If litestar-oauth is not installed.
            ValueError: If provider is not configured.
        """
        if provider_name in self._providers:
            return self._providers[provider_name]

        provider_config = self.config.get_provider(provider_name)
        if not provider_config:
            msg = f"OAuth provider '{provider_name}' is not configured"
            raise ValueError(msg)

        try:
            from litestar_oauth.providers import (
                DiscordOAuthProvider,
                GenericOAuthProvider,
                GitHubOAuthProvider,
                GoogleOAuthProvider,
            )
        except ImportError as e:
            msg = (
                "litestar-oauth is required for OAuth authentication. "
                "Install it with: pip install 'litestar-admin[oauth]'"
            )
            raise ImportError(msg) from e

        kwargs = self.config.to_provider_kwargs(provider_config)

        provider_class_map = {
            OAuthProviderType.GITHUB: GitHubOAuthProvider,
            OAuthProviderType.GOOGLE: GoogleOAuthProvider,
            OAuthProviderType.DISCORD: DiscordOAuthProvider,
            OAuthProviderType.GENERIC: GenericOAuthProvider,
        }

        provider_class = provider_class_map.get(provider_config.provider_type)
        if not provider_class:
            msg = f"Unknown provider type: {provider_config.provider_type}"
            raise ValueError(msg)

        provider = provider_class(**kwargs)
        self._providers[provider_name] = provider
        return provider

    async def authenticate(
        self,
        connection: ASGIConnection,  # noqa: ARG002
        credentials: dict[str, str],
    ) -> AdminUserProtocol | None:
        """Authenticate a user with OAuth or email/password credentials.

        This method supports two authentication modes:
        1. OAuth: Expects 'provider', 'code', and optionally 'state'
        2. Password: Expects 'email' and 'password'

        Args:
            connection: The current ASGI connection.
            credentials: Dictionary containing authentication credentials.

        Returns:
            The authenticated AdminUser if successful, None otherwise.
        """
        # Check for password-based authentication (email + password)
        email = credentials.get("email")
        password = credentials.get("password")

        if email and password:
            # Password authentication mode
            return await self._authenticate_with_password(email, password)

        # OAuth authentication mode
        provider_name = credentials.get("provider")
        code = credentials.get("code")
        state = credentials.get("state")

        if not provider_name or not code:
            return None

        # Verify state if provided (CSRF protection)
        if state and state not in self._state_store:
            return None

        # Clean up used state
        if state:
            self._state_store.pop(state, None)

        try:
            # Get provider and exchange code for tokens
            provider = self._get_provider(provider_name)
            tokens = await provider.exchange_code(code)

            # Get user info from provider
            user_info = await provider.get_user_info(tokens.access_token)

            # Extract normalized user info
            oauth_user_info = self._extract_user_info(user_info, provider_name)

            # Validate email domain if configured
            if not self._validate_email_domain(oauth_user_info.email):
                return None

            # Try to find existing user
            user = await self.user_loader_by_email(oauth_user_info.email)

            # Create user if not found and auto_create is enabled
            if user is None and self.config.auto_create_user and self.user_creator:
                user = await self.user_creator(oauth_user_info)

            return user

        except Exception:
            # Log error in production
            return None

    async def get_current_user(
        self,
        connection: ASGIConnection,
    ) -> AdminUserProtocol | None:
        """Get the currently authenticated user from the request.

        Extracts the session token from cookies or headers and loads the user.

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

        # Check token type
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
            "expires_in": str(self.token_expiry),
        }

    async def logout(
        self,
        connection: ASGIConnection,
    ) -> None:
        """Destroy the current session.

        For stateless JWT authentication, this is typically a no-op on the server side.

        Args:
            connection: The current ASGI connection.
        """
        # JWT is stateless - actual logout is handled by client discarding tokens

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
            "expires_in": str(self.token_expiry),
        }

    def get_authorization_url(self, provider_name: str) -> tuple[str, str]:
        """Get the OAuth authorization URL for a provider.

        Generates the URL to redirect users to for OAuth authentication,
        along with a state token for CSRF protection.

        Args:
            provider_name: Name of the OAuth provider.

        Returns:
            Tuple of (authorization_url, state_token).
        """
        provider = self._get_provider(provider_name)

        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)
        self._state_store[state] = provider_name

        # Get authorization URL from provider
        auth_url = provider.get_authorization_url(state=state)

        return auth_url, state

    async def handle_callback(
        self,
        provider_name: str,
        code: str,
        state: str | None = None,
    ) -> tuple[AdminUserProtocol | None, OAuthTokens | None]:
        """Handle OAuth callback and authenticate user.

        This is a convenience method that combines code exchange, user info
        retrieval, and user authentication/creation.

        Args:
            provider_name: Name of the OAuth provider.
            code: Authorization code from OAuth callback.
            state: State token for CSRF verification (optional).

        Returns:
            Tuple of (user, tokens) if successful, (None, None) otherwise.
        """
        # Verify state if provided
        if state and state not in self._state_store:
            return None, None

        # Clean up used state
        if state:
            stored_provider = self._state_store.pop(state, None)
            if stored_provider != provider_name:
                return None, None

        try:
            provider = self._get_provider(provider_name)

            # Exchange code for tokens
            raw_tokens = await provider.exchange_code(code)
            tokens = OAuthTokens(
                access_token=raw_tokens.access_token,
                token_type=getattr(raw_tokens, "token_type", "Bearer"),
                refresh_token=getattr(raw_tokens, "refresh_token", None),
                expires_in=getattr(raw_tokens, "expires_in", None),
                scope=getattr(raw_tokens, "scope", None),
                id_token=getattr(raw_tokens, "id_token", None),
            )

            # Get user info
            user_info = await provider.get_user_info(tokens.access_token)
            oauth_user_info = self._extract_user_info(user_info, provider_name)

            # Validate email domain
            if not self._validate_email_domain(oauth_user_info.email):
                return None, None

            # Try to find existing user
            user = await self.user_loader_by_email(oauth_user_info.email)

            # Create user if not found and auto_create is enabled
            if user is None and self.config.auto_create_user and self.user_creator:
                user = await self.user_creator(oauth_user_info)

            return user, tokens

        except Exception:
            return None, None

    async def refresh_oauth_token(
        self,
        provider_name: str,
        refresh_token: str,
    ) -> OAuthTokens | None:
        """Refresh an OAuth access token using a refresh token.

        Args:
            provider_name: Name of the OAuth provider.
            refresh_token: The OAuth refresh token.

        Returns:
            New OAuthTokens if successful, None otherwise.
        """
        try:
            provider = self._get_provider(provider_name)

            # Check if provider supports token refresh
            if not hasattr(provider, "refresh_token"):
                return None

            raw_tokens = await provider.refresh_token(refresh_token)
            return OAuthTokens(
                access_token=raw_tokens.access_token,
                token_type=getattr(raw_tokens, "token_type", "Bearer"),
                refresh_token=getattr(raw_tokens, "refresh_token", None),
                expires_in=getattr(raw_tokens, "expires_in", None),
                scope=getattr(raw_tokens, "scope", None),
                id_token=getattr(raw_tokens, "id_token", None),
            )

        except Exception:
            return None

    async def _authenticate_with_password(self, email: str, password: str) -> AdminUserProtocol | None:
        """Authenticate a user with email and password.

        This enables hybrid authentication where both OAuth and password login
        are supported. The password is verified against the user's stored hash.

        Args:
            email: The user's email address.
            password: The user's password.

        Returns:
            The authenticated AdminUser if credentials are valid, None otherwise.
        """
        # Load user by email
        user = await self.user_loader_by_email(email)
        if user is None:
            return None

        # Check if password verifier is configured
        if not self.password_verifier:
            return None

        # Get password hash from user
        password_hash = getattr(user, "password_hash", None) or getattr(user, "hashed_password", None)
        if password_hash is None:
            return None

        # Verify password
        if not await self.password_verifier(password_hash, password):
            return None

        return user

    def _extract_user_info(self, user_info: Any, provider_name: str) -> OAuthUserInfo:
        """Extract normalized user info from provider response.

        Args:
            user_info: Raw user info from OAuth provider.
            provider_name: Name of the OAuth provider.

        Returns:
            Normalized OAuthUserInfo object.
        """
        # Handle dict-like response or object-like response (litestar-oauth UserInfo)
        raw_data = user_info if isinstance(user_info, dict) else getattr(user_info, "raw_data", None) or {}

        # Try common field names for ID
        user_id = str(
            getattr(user_info, "id", None) or raw_data.get("id") or raw_data.get("sub") or raw_data.get("user_id") or ""
        )

        # Try common field names for email
        email = str(getattr(user_info, "email", None) or raw_data.get("email") or "")

        # Try common field names for name
        name = (
            getattr(user_info, "name", None)
            or raw_data.get("name")
            or raw_data.get("login")
            or raw_data.get("username")
        )

        # Try common field names for picture/avatar
        picture = (
            getattr(user_info, "picture", None)
            or raw_data.get("picture")
            or raw_data.get("avatar_url")
            or raw_data.get("avatar")
        )

        return OAuthUserInfo(
            id=user_id,
            email=email,
            name=name,
            picture=picture,
            provider=provider_name,
            raw_data=raw_data if isinstance(raw_data, dict) else None,
        )

    def _validate_email_domain(self, email: str) -> bool:
        """Validate that an email is from an allowed domain.

        Args:
            email: The email address to validate.

        Returns:
            True if the email domain is allowed, False otherwise.
        """
        if not self.config.allowed_domains:
            return True

        if not email or "@" not in email:
            return False

        domain = email.split("@")[-1].lower()
        allowed = [d.lower() for d in self.config.allowed_domains]
        return domain in allowed

    def _create_token(self, user: AdminUserProtocol, kind: str = "access") -> str:
        """Create a JWT token for a user.

        Args:
            user: The user to create a token for.
            kind: Type of token ("access" or "refresh").

        Returns:
            Encoded JWT token string.
        """
        import datetime

        try:
            import jwt
        except ImportError as e:
            msg = (
                "PyJWT is required for OAuth authentication sessions. "
                "Install it with: pip install 'litestar-admin[jwt]'"
            )
            raise ImportError(msg) from e

        now = datetime.datetime.now(tz=datetime.timezone.utc)

        expiry = self.token_expiry if kind == "access" else self.refresh_token_expiry
        exp = now + datetime.timedelta(seconds=expiry)

        payload: dict[str, Any] = {
            "sub": str(user.id),
            "email": user.email,
            "roles": user.roles,
            "permissions": user.permissions,
            "type": kind,
            "auth_method": "oauth",
            "iat": now,
            "exp": exp,
        }

        return jwt.encode(
            payload,
            self.jwt_secret_key,
            algorithm=self.jwt_algorithm,
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
            msg = (
                "PyJWT is required for OAuth authentication sessions. "
                "Install it with: pip install 'litestar-admin[jwt]'"
            )
            raise ImportError(msg) from e

        try:
            return jwt.decode(
                token,
                self.jwt_secret_key,
                algorithms=[self.jwt_algorithm],
            )
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def _extract_token(self, connection: ASGIConnection) -> str | None:
        """Extract the JWT token from the request.

        Args:
            connection: The current ASGI connection.

        Returns:
            The extracted token string, or None if not found.
        """
        # Try Authorization header first
        auth_header = connection.headers.get("Authorization")
        if auth_header:
            if auth_header.startswith("Bearer "):
                return auth_header[7:]
            if auth_header.startswith("bearer "):
                return auth_header[7:]

        # Try session cookie
        cookie_value = connection.cookies.get(self.config.session_cookie_name)
        if cookie_value:
            return cookie_value

        return None

    def _extract_refresh_token(self, connection: ASGIConnection) -> str | None:
        """Extract the refresh token from the request.

        Args:
            connection: The current ASGI connection.

        Returns:
            The extracted refresh token string, or None if not found.
        """
        # Try dedicated refresh token header
        refresh_header = connection.headers.get("X-Refresh-Token")
        if refresh_header:
            return refresh_header

        # Try refresh token cookie
        refresh_cookie = connection.cookies.get(f"{self.config.session_cookie_name}_refresh")
        if refresh_cookie:
            return refresh_cookie

        # Try request state (set by controller)
        if hasattr(connection, "state"):
            refresh_token = getattr(connection.state, "refresh_token", None)
            if refresh_token:
                return refresh_token

        return None

    @property
    def available_providers(self) -> list[str]:
        """Get list of configured provider names.

        Returns:
            List of provider names that are configured.
        """
        return [p.name for p in self.config.providers]
