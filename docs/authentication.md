# Authentication

litestar-admin provides flexible authentication options to secure your admin panel. This guide covers JWT authentication, custom backends, and OAuth integration.

## Overview

Authentication in litestar-admin is handled through pluggable backends that implement the `AuthBackend` protocol. The package includes a built-in JWT backend, and you can create custom backends for other authentication methods.

## Quick Setup with JWT

The fastest way to add authentication is using the built-in JWT backend:

```python
from litestar_admin import AdminPlugin, AdminConfig
from litestar_admin.auth import JWTAuthBackend, JWTConfig


async def load_user(user_id: str | int):
    """Load user from database by ID or email."""
    # Your user loading logic here
    return await user_repository.get(user_id)


# Create JWT backend
jwt_config = JWTConfig(
    secret_key="your-super-secret-key-change-in-production",
)

auth_backend = JWTAuthBackend(
    config=jwt_config,
    user_loader=load_user,
)

# Add to admin config
admin_config = AdminConfig(
    title="Secure Admin",
    auth_backend=auth_backend,
)
```

## JWT Configuration

The `JWTConfig` dataclass provides comprehensive options for JWT authentication.

### Required Settings

#### secret_key

The secret key used for signing JWT tokens. This must be kept secure.

```python
import os

JWTConfig(
    secret_key=os.environ["JWT_SECRET_KEY"],  # Load from environment
)
```

```{warning}
Never hardcode secret keys in your source code. Always use environment variables or a secrets manager.
```

### Token Settings

#### algorithm

JWT signing algorithm. Defaults to `"HS256"`.

```python
JWTConfig(
    secret_key="...",
    algorithm="HS512",  # Use HS512 for extra security
)
```

#### token_expiry

Access token expiry time in seconds. Defaults to `3600` (1 hour).

```python
JWTConfig(
    secret_key="...",
    token_expiry=1800,  # 30 minutes
)
```

#### refresh_token_expiry

Refresh token expiry time in seconds. Defaults to `86400` (24 hours).

```python
JWTConfig(
    secret_key="...",
    refresh_token_expiry=604800,  # 7 days
)
```

### Token Location

#### token_location

Where to look for the JWT token. Options are `"header"` (default) or `"cookie"`.

```python
# Header-based (default)
JWTConfig(
    secret_key="...",
    token_location="header",
)

# Cookie-based
JWTConfig(
    secret_key="...",
    token_location="cookie",
)
```

#### token_header

HTTP header name for token extraction. Defaults to `"Authorization"`.

```python
JWTConfig(
    secret_key="...",
    token_header="X-Admin-Token",
)
```

#### token_prefix

Prefix for header-based tokens. Defaults to `"Bearer"`.

```python
JWTConfig(
    secret_key="...",
    token_prefix="Bearer",  # Token: "Bearer <token>"
)
```

### Cookie Settings

When using `token_location="cookie"`:

#### cookie_name

Name of the cookie storing the token. Defaults to `"admin_access_token"`.

```python
JWTConfig(
    secret_key="...",
    token_location="cookie",
    cookie_name="admin_jwt",
)
```

#### cookie_secure

Whether the cookie should only be sent over HTTPS. Defaults to `True`.

```python
JWTConfig(
    secret_key="...",
    token_location="cookie",
    cookie_secure=False,  # Only for local development!
)
```

#### cookie_httponly

Whether the cookie should be HTTP-only. Defaults to `True`.

```python
JWTConfig(
    secret_key="...",
    token_location="cookie",
    cookie_httponly=True,  # Prevents JavaScript access
)
```

#### cookie_samesite

SameSite attribute for the cookie. Options: `"strict"`, `"lax"`, `"none"`. Defaults to `"lax"`.

```python
JWTConfig(
    secret_key="...",
    token_location="cookie",
    cookie_samesite="strict",
)
```

### Optional Claims

#### issuer

Token issuer claim for additional validation.

```python
JWTConfig(
    secret_key="...",
    issuer="https://myapp.com",
)
```

#### audience

Token audience claim for additional validation.

```python
JWTConfig(
    secret_key="...",
    audience="myapp-admin",
)
```

## JWTAuthBackend

The `JWTAuthBackend` class handles authentication using the configured JWT settings.

### Constructor Arguments

#### config

The `JWTConfig` instance with JWT settings.

#### user_loader

An async callable that takes a user ID (or email) and returns an `AdminUser` object or `None`.

```python
async def load_user(user_id: str | int) -> AdminUser | None:
    """Load user from database."""
    user = await db.get_user(user_id)
    return user  # Must implement AdminUser protocol
```

#### password_verifier (optional)

An async callable for verifying passwords during login.

```python
async def verify_password(stored_hash: str, password: str) -> bool:
    """Verify password against stored hash."""
    return bcrypt.checkpw(password.encode(), stored_hash.encode())


backend = JWTAuthBackend(
    config=jwt_config,
    user_loader=load_user,
    password_verifier=verify_password,
)
```

## The AdminUser Protocol

Your user class must implement the `AdminUser` protocol:

```python
from litestar_admin.auth import AdminUser


class User:
    """Your user class implementing AdminUser protocol."""

    @property
    def id(self) -> str | int:
        """User's unique identifier."""
        return self._id

    @property
    def email(self) -> str:
        """User's email address."""
        return self._email

    @property
    def roles(self) -> list[str]:
        """User's role names (e.g., ['admin', 'editor'])."""
        return self._roles

    @property
    def permissions(self) -> list[str]:
        """User's permission strings (e.g., ['models:read', 'models:write'])."""
        return self._permissions
```

### Example Implementation

```python
from dataclasses import dataclass


@dataclass
class AdminUserModel:
    """Admin user implementation."""

    id: int
    email: str
    password_hash: str
    _roles: list[str]
    _permissions: list[str]

    @property
    def roles(self) -> list[str]:
        return self._roles

    @property
    def permissions(self) -> list[str]:
        return self._permissions
```

## Complete JWT Example

Here's a complete example with database integration:

```python
from __future__ import annotations

import os
from dataclasses import dataclass

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from litestar import Litestar
from litestar.plugins.sqlalchemy import SQLAlchemyConfig, SQLAlchemyPlugin
from litestar_admin import AdminConfig, AdminPlugin
from litestar_admin.auth import JWTAuthBackend, JWTConfig


# User model (simplified)
@dataclass
class User:
    id: int
    email: str
    password_hash: str
    is_admin: bool

    @property
    def roles(self) -> list[str]:
        return ["admin"] if self.is_admin else ["viewer"]

    @property
    def permissions(self) -> list[str]:
        if self.is_admin:
            return ["models:read", "models:write", "models:delete"]
        return ["models:read"]


# Database session (you'd get this from your app state)
async def get_db_session() -> AsyncSession:
    ...


# User loader function
async def load_user(identifier: str | int) -> User | None:
    """Load user by ID or email."""
    async with get_db_session() as session:
        # Try to load by ID first
        if isinstance(identifier, int) or identifier.isdigit():
            query = select(User).where(User.id == int(identifier))
        else:
            # Load by email for authentication
            query = select(User).where(User.email == identifier)

        result = await session.execute(query)
        return result.scalar_one_or_none()


# Password verification
async def verify_password(stored_hash: str, password: str) -> bool:
    """Verify password using bcrypt."""
    return bcrypt.checkpw(
        password.encode("utf-8"),
        stored_hash.encode("utf-8"),
    )


# JWT configuration
jwt_config = JWTConfig(
    secret_key=os.environ["JWT_SECRET_KEY"],
    algorithm="HS256",
    token_expiry=3600,  # 1 hour
    refresh_token_expiry=86400 * 7,  # 7 days
    token_location="header",
)

# Create auth backend
auth_backend = JWTAuthBackend(
    config=jwt_config,
    user_loader=load_user,
    password_verifier=verify_password,
)

# Create admin plugin
admin_plugin = AdminPlugin(
    config=AdminConfig(
        title="Secure Admin",
        auth_backend=auth_backend,
    ),
)

# Create app
app = Litestar(
    plugins=[admin_plugin],
)
```

## Custom Auth Backend

You can create custom authentication backends by implementing the `AuthBackend` protocol:

```python
from litestar_admin.auth import AuthBackend, AdminUser


class CustomAuthBackend:
    """Custom authentication backend."""

    async def authenticate(
        self,
        connection: ASGIConnection,
        credentials: dict[str, str],
    ) -> AdminUser | None:
        """Authenticate user with credentials.

        Args:
            connection: The ASGI connection.
            credentials: Dict with 'email' and 'password'.

        Returns:
            Authenticated user or None.
        """
        email = credentials.get("email")
        password = credentials.get("password")

        # Your authentication logic
        user = await your_auth_service.authenticate(email, password)
        return user

    async def get_current_user(
        self,
        connection: ASGIConnection,
    ) -> AdminUser | None:
        """Get currently authenticated user.

        Args:
            connection: The ASGI connection.

        Returns:
            Current user or None.
        """
        # Extract session/token from connection
        session_id = connection.cookies.get("session_id")
        if not session_id:
            return None

        return await your_session_service.get_user(session_id)

    async def login(
        self,
        connection: ASGIConnection,
        user: AdminUser,
    ) -> dict[str, str]:
        """Create session for user.

        Args:
            connection: The ASGI connection.
            user: The authenticated user.

        Returns:
            Dict with session tokens.
        """
        session_id = await your_session_service.create_session(user)
        return {"session_id": session_id}

    async def logout(
        self,
        connection: ASGIConnection,
    ) -> None:
        """Destroy current session.

        Args:
            connection: The ASGI connection.
        """
        session_id = connection.cookies.get("session_id")
        if session_id:
            await your_session_service.destroy_session(session_id)

    async def refresh(
        self,
        connection: ASGIConnection,
    ) -> dict[str, str] | None:
        """Refresh session tokens.

        Args:
            connection: The ASGI connection.

        Returns:
            New tokens or None if refresh failed.
        """
        # Implement refresh logic
        return None  # Or new tokens
```

## OAuth Integration

For OAuth authentication, install the oauth extra:

```bash
pip install "litestar-admin[oauth]"
```

```{note}
OAuth integration requires the `litestar-oauth` package. This feature is planned for a future release.
```

## Auth API Endpoints

When authentication is enabled, the following endpoints are available:

### POST /admin/api/auth/login

Authenticate with credentials.

**Request:**
```json
{
    "email": "admin@example.com",
    "password": "secret123"
}
```

**Response:**
```json
{
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": "3600"
}
```

### POST /admin/api/auth/logout

Invalidate current session.

**Response:**
```json
{
    "message": "Logged out successfully"
}
```

### POST /admin/api/auth/refresh

Refresh access token using refresh token.

**Request Header:**
```
X-Refresh-Token: eyJ...
```

**Response:**
```json
{
    "access_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": "3600"
}
```

### GET /admin/api/auth/me

Get current user information.

**Response:**
```json
{
    "id": 1,
    "email": "admin@example.com",
    "roles": ["admin"],
    "permissions": ["models:read", "models:write"]
}
```

## Security Best Practices

1. **Use Strong Secret Keys**
   ```python
   import secrets
   secret_key = secrets.token_urlsafe(32)
   ```

2. **Store Secrets Securely**
   ```python
   import os
   JWTConfig(secret_key=os.environ["JWT_SECRET_KEY"])
   ```

3. **Use HTTPS in Production**
   ```python
   JWTConfig(
       cookie_secure=True,  # Only send over HTTPS
   )
   ```

4. **Set Appropriate Token Expiry**
   ```python
   JWTConfig(
       token_expiry=1800,  # 30 minutes for sensitive apps
   )
   ```

5. **Enable HTTP-Only Cookies**
   ```python
   JWTConfig(
       cookie_httponly=True,  # Prevent XSS access
   )
   ```

6. **Use SameSite Cookies**
   ```python
   JWTConfig(
       cookie_samesite="strict",  # Prevent CSRF
   )
   ```
