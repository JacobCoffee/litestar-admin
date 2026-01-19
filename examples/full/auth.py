"""Authentication setup for the full admin demo.

This module provides the authentication configuration including:
- AdminUser dataclass implementing the AdminUser protocol
- user_loader async function for loading users by email/id
- password_verifier async function for credential validation
- JWTAuthBackend configuration (default)
- OAuthAuthBackend configuration (optional, for GitHub OAuth)
- DemoOAuthProvider for local testing without real OAuth credentials

Example:
    JWT Authentication (default):
        >>> from examples.full.auth import get_auth_backend
        >>> backend = get_auth_backend(db_session_factory)

    OAuth Authentication (GitHub):
        >>> from examples.full.auth import get_oauth_backend
        >>> backend = get_oauth_backend(db_session_factory)

    Demo OAuth Authentication (local testing):
        >>> from examples.full.auth import get_demo_oauth_backend
        >>> backend = get_demo_oauth_backend(db_session_factory)

OAuth Setup Requirements:
    To use GitHub OAuth authentication:
    1. Create a GitHub OAuth App at https://github.com/settings/developers
    2. Set the callback URL to: http://localhost:8000/admin/auth/oauth/github/callback
    3. Set environment variables:
       - GITHUB_CLIENT_ID: Your GitHub OAuth App client ID
       - GITHUB_CLIENT_SECRET: Your GitHub OAuth App client secret
    4. Install OAuth dependencies: pip install 'litestar-admin[oauth]'

Demo OAuth Mode:
    For local development and testing without GitHub credentials, use the demo
    OAuth provider. This simulates the OAuth flow without making external calls:

    1. Set environment variable: OAUTH_DEMO_MODE=true
    2. Run the application: litestar --app examples.full.app:app run --reload

    The demo provider will:
    - Accept any authorization code and return mock tokens
    - Return a configurable demo user (default: demo@example.com)
    - Skip the real OAuth flow entirely
    - Create a real user in the database on first login

    Configure the demo user via environment variables:
    - DEMO_OAUTH_EMAIL: Email for demo user (default: demo@example.com)
    - DEMO_OAUTH_NAME: Display name for demo user (default: Demo User)
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from litestar_admin.auth.jwt import JWTAuthBackend, JWTConfig
from litestar_admin.guards import ROLE_PERMISSIONS, Permission, Role

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy.ext.asyncio import AsyncSession

    from litestar_admin.contrib.oauth import OAuthAuthBackend, OAuthUserInfo

__all__ = [
    "DemoAdminUser",
    "DemoOAuthProvider",
    "create_oauth_user_creator",
    "create_password_updater",
    "get_auth_backend",
    "get_demo_oauth_backend",
    "get_oauth_backend",
    "hash_password",
    "hash_password_async",
    "verify_password",
]


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


async def hash_password_async(password: str) -> str:
    """Async version of hash_password for JWT backend.

    Args:
        password: The plaintext password to hash.

    Returns:
        The hashed password as a hex string.
    """
    return hash_password(password)


def create_password_updater(session_factory: Callable[[], AsyncSession]) -> Callable[[int | str, str], bool]:
    """Create a password updater function for the JWT backend.

    The password updater is called when a user changes their password.

    Args:
        session_factory: A callable that returns an AsyncSession.

    Returns:
        An async function that updates a user's password hash.
    """

    async def password_updater(user_id: int | str, new_hash: str) -> bool:
        """Update a user's password hash.

        Args:
            user_id: The user's ID.
            new_hash: The new password hash to set.

        Returns:
            True if the update succeeded, False otherwise.
        """
        from sqlalchemy import update

        from examples.full.models import User

        try:
            user_id_int = int(user_id)
        except (TypeError, ValueError):
            return False

        async with session_factory() as session:
            stmt = update(User).where(User.id == user_id_int).values(password_hash=new_hash)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    return password_updater


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

    This is the default authentication backend for the demo application.
    It uses username/password authentication with JWT tokens.

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
    password_updater = create_password_updater(session_factory)

    return JWTAuthBackend(
        config=config,
        user_loader=user_loader,
        password_verifier=verify_password,
        password_hasher=hash_password_async,
        password_updater=password_updater,
    )


def create_user_loader_by_email(
    session_factory: Callable[[], AsyncSession],
) -> Callable[[str], DemoAdminUser | None]:
    """Create a user loader function that loads users by email only.

    This loader is specifically for OAuth authentication where we need
    to find users by their email address from the OAuth provider.

    Args:
        session_factory: A callable that returns an AsyncSession.

    Returns:
        An async function that loads a user by email.
    """

    async def user_loader_by_email(email: str) -> DemoAdminUser | None:
        """Load a user by email address.

        Args:
            email: The user's email address.

        Returns:
            A DemoAdminUser instance if found, None otherwise.
        """
        from sqlalchemy import select

        from examples.full.models import User

        async with session_factory() as session:
            stmt = select(User).where(User.email == email)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if user is None:
                return None

            if not user.is_active:
                return None

            return DemoAdminUser.from_db_user(user)

    return user_loader_by_email


def create_oauth_user_creator(
    session_factory: Callable[[], AsyncSession],
) -> Callable[[OAuthUserInfo], DemoAdminUser]:
    """Create a function to create new users from OAuth user info.

    This function is called when a user logs in via OAuth for the first time
    and no existing user with that email exists in the database.

    Args:
        session_factory: A callable that returns an AsyncSession.

    Returns:
        An async function that creates a new user from OAuth info.
    """

    async def create_oauth_user(user_info: OAuthUserInfo) -> DemoAdminUser:
        """Create a new user from OAuth provider information.

        This function creates a new User record in the database using
        information provided by the OAuth provider (e.g., GitHub).

        The new user is assigned the VIEWER role by default. You can
        customize this based on your application's requirements.

        Args:
            user_info: Normalized user information from the OAuth provider.
                Contains: id, email, name, picture, provider, raw_data

        Returns:
            A DemoAdminUser instance for the newly created user.

        Example:
            OAuth user_info from GitHub might contain:
            - id: "12345678"
            - email: "user@example.com"
            - name: "John Doe"
            - picture: "https://avatars.githubusercontent.com/u/12345678"
            - provider: "github"
            - raw_data: {"login": "johndoe", "id": 12345678, ...}
        """
        import secrets

        from examples.full.models import User, UserRole

        async with session_factory() as session:
            # Create a new user with OAuth-provided information
            # Generate a random password hash since OAuth users don't use password auth
            # but the database column requires a value
            random_password_hash = hash_password(secrets.token_urlsafe(32))

            new_user = User(
                email=user_info.email,
                name=user_info.name or user_info.email.split("@")[0],
                password_hash=random_password_hash,  # Random hash - OAuth users use OAuth, not password
                role=UserRole.VIEWER,  # Default role for new OAuth users
                is_active=True,
            )
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)

            return DemoAdminUser.from_db_user(new_user)

    return create_oauth_user


def get_oauth_backend(session_factory: Callable[[], AsyncSession]) -> OAuthAuthBackend:
    """Create and configure the OAuth authentication backend for GitHub.

    This backend enables "Login with GitHub" functionality. Users authenticate
    via GitHub's OAuth flow and are automatically created in the database
    on first login.

    Requirements:
        1. Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET environment variables
        2. Install OAuth dependencies: pip install 'litestar-admin[oauth]'
        3. Configure GitHub OAuth App callback URL:
           http://localhost:8000/admin/auth/oauth/github/callback

    Args:
        session_factory: A callable that returns an AsyncSession for database access.

    Returns:
        A configured OAuthAuthBackend instance.

    Raises:
        ValueError: If GITHUB_CLIENT_ID or GITHUB_CLIENT_SECRET are not set.

    Example:
        >>> import os
        >>> os.environ["GITHUB_CLIENT_ID"] = "your-client-id"
        >>> os.environ["GITHUB_CLIENT_SECRET"] = "your-client-secret"
        >>> backend = get_oauth_backend(get_session)
    """
    from litestar_admin.contrib.oauth import (
        OAuthAuthBackend,
        OAuthConfig,
        OAuthProviderConfig,
        OAuthProviderType,
    )

    # Get GitHub OAuth credentials from environment variables
    github_client_id = os.environ.get("GITHUB_CLIENT_ID")
    github_client_secret = os.environ.get("GITHUB_CLIENT_SECRET")

    if not github_client_id or not github_client_secret:
        msg = (
            "GitHub OAuth credentials not configured. "
            "Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET environment variables. "
            "See module docstring for setup instructions."
        )
        raise ValueError(msg)

    # Configure OAuth with GitHub provider
    oauth_config = OAuthConfig(
        providers=[
            OAuthProviderConfig(
                name="github",
                client_id=github_client_id,
                client_secret=github_client_secret,
                provider_type=OAuthProviderType.GITHUB,
                # GitHub default scopes include 'user:email' which gives us the email
                # You can request additional scopes if needed:
                # scopes=["user:email", "read:user", "read:org"],
            ),
        ],
        # Base URL for OAuth callbacks - must match your GitHub OAuth App settings
        # For local development: http://localhost:8000
        # For production: https://your-domain.com
        redirect_base_url=os.environ.get("OAUTH_REDIRECT_BASE_URL", "http://localhost:8000"),
        # Automatically create users on first OAuth login
        auto_create_user=True,
        # Optional: Restrict to specific email domains
        # allowed_domains=["example.com", "yourcompany.com"],
    )

    # Create the OAuth backend with user management functions
    return OAuthAuthBackend(
        config=oauth_config,
        user_loader=create_user_loader(session_factory),
        user_loader_by_email=create_user_loader_by_email(session_factory),
        user_creator=create_oauth_user_creator(session_factory),
        # JWT settings for session tokens (used after OAuth authentication)
        jwt_secret_key=DEMO_SECRET_KEY,
        jwt_algorithm="HS256",
        token_expiry=3600,  # 1 hour
        refresh_token_expiry=86400,  # 24 hours
    )


class DemoOAuthTokens:
    """Mock OAuth tokens for demo provider.

    This class mimics the token response from real OAuth providers,
    providing mock access and refresh tokens for testing purposes.

    Attributes:
        access_token: A mock access token string.
        token_type: Token type (always "Bearer").
        refresh_token: A mock refresh token string.
        expires_in: Token expiry in seconds (default: 3600).
        scope: Granted scopes string.
    """

    def __init__(
        self,
        access_token: str = "demo_access_token_12345",  # noqa: S107
        token_type: str = "Bearer",  # noqa: S107
        refresh_token: str = "demo_refresh_token_67890",  # noqa: S107
        expires_in: int = 3600,
        scope: str = "user:email",
    ) -> None:
        """Initialize demo tokens.

        Args:
            access_token: Mock access token.
            token_type: Token type.
            refresh_token: Mock refresh token.
            expires_in: Token expiry in seconds.
            scope: Granted scopes.
        """
        self.access_token = access_token
        self.token_type = token_type
        self.refresh_token = refresh_token
        self.expires_in = expires_in
        self.scope = scope


class DemoOAuthUserInfo:
    """Mock user info for demo provider.

    This class mimics the user info response from real OAuth providers,
    providing configurable demo user information for testing.

    Attributes:
        id: Demo user ID.
        email: Demo user email.
        name: Demo user display name.
        avatar_url: Demo user avatar URL.
        login: Demo user login/username.
        raw_data: Raw user data dictionary.
    """

    def __init__(
        self,
        email: str = "demo@example.com",
        name: str = "Demo User",
        user_id: str = "demo_user_001",
    ) -> None:
        """Initialize demo user info.

        Args:
            email: Demo user email address.
            name: Demo user display name.
            user_id: Demo user unique ID.
        """
        self.id = user_id
        self.email = email
        self.name = name
        self.avatar_url = "https://www.gravatar.com/avatar/demo?d=identicon"
        self.login = email.split("@")[0]
        self.raw_data = {
            "id": user_id,
            "email": email,
            "name": name,
            "login": self.login,
            "avatar_url": self.avatar_url,
        }


class DemoOAuthProvider:
    """Demo OAuth provider that simulates OAuth flow without external calls.

    This provider is designed for local development and testing, allowing
    developers to test the OAuth login flow without needing real OAuth
    credentials (e.g., GitHub Client ID/Secret).

    The provider:
    - Accepts any authorization code and returns mock tokens
    - Returns configurable demo user information
    - Does not make any external HTTP requests
    - Creates a real user in the database on first login

    Configuration is done via environment variables:
    - DEMO_OAUTH_EMAIL: Email for the demo user (default: demo@example.com)
    - DEMO_OAUTH_NAME: Display name for the demo user (default: Demo User)

    Example:
        >>> provider = DemoOAuthProvider(
        ...     client_id="demo",
        ...     client_secret="demo",
        ...     redirect_uri="http://localhost:8000/admin/auth/oauth/demo/callback",
        ... )
        >>> tokens = await provider.exchange_code("any_code")
        >>> user_info = await provider.get_user_info(tokens.access_token)
        >>> print(user_info.email)  # demo@example.com
    """

    def __init__(
        self,
        client_id: str = "demo_client_id",
        client_secret: str = "demo_client_secret",  # noqa: S107
        redirect_uri: str = "http://localhost:8000/admin/auth/oauth/demo/callback",
        scopes: list[str] | None = None,
        demo_email: str | None = None,
        demo_name: str | None = None,
    ) -> None:
        """Initialize the demo OAuth provider.

        Args:
            client_id: Demo client ID (not used but required for interface compatibility).
            client_secret: Demo client secret (not used but required for interface compatibility).
            redirect_uri: OAuth callback URL.
            scopes: Requested scopes (not used but required for interface compatibility).
            demo_email: Email for the demo user. Defaults to DEMO_OAUTH_EMAIL env var or demo@example.com.
            demo_name: Name for the demo user. Defaults to DEMO_OAUTH_NAME env var or Demo User.
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = scopes or ["user:email"]

        # Get demo user configuration from environment or use defaults
        self.demo_email = demo_email or os.environ.get("DEMO_OAUTH_EMAIL", "demo@example.com")
        self.demo_name = demo_name or os.environ.get("DEMO_OAUTH_NAME", "Demo User")

    def get_authorization_url(self, state: str | None = None) -> str:
        """Get the authorization URL for the demo provider.

        For the demo provider, this returns a special URL that the frontend
        can detect and handle appropriately. The URL includes the state
        parameter for CSRF protection compatibility.

        Args:
            state: CSRF state token.

        Returns:
            The authorization URL with state parameter.
        """
        # Return a special demo URL that the frontend can intercept
        # In a real scenario, this would redirect to GitHub/Google/etc.
        # For demo mode, the frontend should detect this and auto-complete the flow
        base_url = self.redirect_uri.replace("/callback", "/authorize")
        if state:
            return f"{base_url}?state={state}&demo=true"
        return f"{base_url}?demo=true"

    async def exchange_code(self, code: str) -> DemoOAuthTokens:
        """Exchange authorization code for tokens.

        For the demo provider, this accepts any code and returns mock tokens.
        No validation is performed - this is intentional for ease of testing.

        Args:
            code: Authorization code (any value accepted).

        Returns:
            Mock OAuth tokens.
        """
        # Accept any code and return mock tokens
        # In production OAuth, this would validate the code against the provider
        _ = code  # Acknowledge the parameter (unused intentionally)
        return DemoOAuthTokens()

    async def get_user_info(self, access_token: str) -> DemoOAuthUserInfo:
        """Get user information using the access token.

        For the demo provider, this returns the configured demo user
        regardless of the access token value.

        Args:
            access_token: OAuth access token (any value accepted).

        Returns:
            Demo user information.
        """
        # Return demo user info regardless of token
        # In production OAuth, this would fetch real user data from the provider
        _ = access_token  # Acknowledge the parameter (unused intentionally)
        return DemoOAuthUserInfo(
            email=self.demo_email,
            name=self.demo_name,
        )

    async def refresh_token(self, refresh_token: str) -> DemoOAuthTokens:
        """Refresh the access token.

        For the demo provider, this returns new mock tokens regardless
        of the refresh token value.

        Args:
            refresh_token: OAuth refresh token (any value accepted).

        Returns:
            New mock OAuth tokens.
        """
        # Return new mock tokens regardless of refresh token
        _ = refresh_token  # Acknowledge the parameter (unused intentionally)
        return DemoOAuthTokens()


def get_demo_oauth_backend(session_factory: Callable[[], AsyncSession]) -> OAuthAuthBackend:
    """Create and configure the Demo OAuth authentication backend.

    This backend enables testing the OAuth flow without real OAuth credentials.
    It uses a DemoOAuthProvider that accepts any authorization code and returns
    a configurable demo user.

    This is useful for:
    - Local development without setting up GitHub OAuth App
    - Testing the OAuth flow in CI/CD pipelines
    - Demonstrating the admin panel without external dependencies

    The demo user is created in the database on first login, allowing you to
    test the full authentication flow including user creation and role assignment.

    Configuration via environment variables:
    - OAUTH_DEMO_MODE=true: Enable demo OAuth mode in the application
    - DEMO_OAUTH_EMAIL: Email for demo user (default: demo@example.com)
    - DEMO_OAUTH_NAME: Display name for demo user (default: Demo User)

    Args:
        session_factory: A callable that returns an AsyncSession for database access.

    Returns:
        A configured OAuthAuthBackend instance with the demo provider.

    Example:
        Running with demo OAuth:

        >>> # Set environment variable
        >>> import os
        >>> os.environ["OAUTH_DEMO_MODE"] = "true"
        >>>
        >>> # Or run from command line:
        >>> # OAUTH_DEMO_MODE=true litestar --app examples.full.app:app run --reload
        >>>
        >>> # The demo user can be customized:
        >>> os.environ["DEMO_OAUTH_EMAIL"] = "test@mycompany.com"
        >>> os.environ["DEMO_OAUTH_NAME"] = "Test Developer"
    """
    from litestar_admin.contrib.oauth import OAuthAuthBackend, OAuthConfig, OAuthProviderConfig, OAuthProviderType

    # Get demo user configuration from environment
    demo_email = os.environ.get("DEMO_OAUTH_EMAIL", "demo@example.com")
    demo_name = os.environ.get("DEMO_OAUTH_NAME", "Demo User")
    redirect_base_url = os.environ.get("OAUTH_REDIRECT_BASE_URL", "http://localhost:8000")

    # Create a provider config for the demo provider
    # We use GENERIC type but will override the provider instance
    demo_provider_config = OAuthProviderConfig(
        name="demo",
        client_id="demo_client_id",
        client_secret="demo_client_secret",  # noqa: S106
        provider_type=OAuthProviderType.GENERIC,
        # These URLs are required for GENERIC type but won't be used
        authorize_url=f"{redirect_base_url}/admin/auth/oauth/demo/authorize",
        token_url=f"{redirect_base_url}/admin/auth/oauth/demo/token",
        userinfo_url=f"{redirect_base_url}/admin/auth/oauth/demo/userinfo",
    )

    oauth_config = OAuthConfig(
        providers=[demo_provider_config],
        redirect_base_url=redirect_base_url,
        auto_create_user=True,
    )

    # Create the backend with password support for hybrid auth
    # This allows both OAuth login AND password login on the same page
    backend = OAuthAuthBackend(
        config=oauth_config,
        user_loader=create_user_loader(session_factory),
        user_loader_by_email=create_user_loader_by_email(session_factory),
        user_creator=create_oauth_user_creator(session_factory),
        jwt_secret_key=DEMO_SECRET_KEY,
        jwt_algorithm="HS256",
        token_expiry=3600,
        refresh_token_expiry=86400,
        password_verifier=verify_password,  # Enable hybrid auth (password + OAuth)
    )

    # Override the provider with our demo provider
    # This replaces the generic provider that would make HTTP requests
    demo_provider = DemoOAuthProvider(
        client_id="demo_client_id",
        client_secret="demo_client_secret",  # noqa: S106
        redirect_uri=oauth_config.get_callback_url("demo"),
        demo_email=demo_email,
        demo_name=demo_name,
    )
    backend._providers["demo"] = demo_provider

    return backend
