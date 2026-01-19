# Authentication API

The authentication API handles user login, logout, token refresh, and retrieving current user information.

All authentication endpoints are under `/admin/api/auth`.

## Overview

litestar-admin uses a pluggable authentication system. The default implementation uses JWT (JSON Web Tokens) with access and refresh tokens:

- **Access Token**: Short-lived token (default: 15 minutes) for API requests
- **Refresh Token**: Long-lived token (default: 7 days) for obtaining new access tokens

## Endpoints

### Login

Authenticate a user with email and password credentials.

```{rubric} POST /api/auth/login
```

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `email` | string | Yes | User's email address |
| `password` | string | Yes | User's password |

**Example Request**

```http
POST /admin/api/auth/login HTTP/1.1
Content-Type: application/json

{
  "email": "admin@example.com",
  "password": "secretpassword"
}
```

**Success Response (200 OK)**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": "900"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `access_token` | string | JWT for authenticating API requests |
| `refresh_token` | string | Token for obtaining new access tokens |
| `token_type` | string | Always "bearer" |
| `expires_in` | string | Access token lifetime in seconds |

**Error Responses**

:::{list-table}
:header-rows: 1
:widths: 20 80

* - Status
  - Response
* - 401
  - ```json
    {"detail": "Invalid email or password"}
    ```
* - 401
  - ```json
    {"detail": "Authentication is not configured"}
    ```
:::

---

### Logout

End the current user session and invalidate tokens.

```{rubric} POST /api/auth/logout
```

**Headers**

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes | `Bearer <access_token>` |

**Example Request**

```http
POST /admin/api/auth/logout HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Success Response (200 OK)**

```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

**Error Response**

| Status | Response |
|--------|----------|
| 401 | `{"detail": "Authentication is not configured"}` |

---

### Refresh Token

Exchange a refresh token for a new access token.

```{rubric} POST /api/auth/refresh
```

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `refresh_token` | string | Yes | The refresh token from login |

**Example Request**

```http
POST /admin/api/auth/refresh HTTP/1.1
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Success Response (200 OK)**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": "900"
}
```

**Error Responses**

| Status | Response |
|--------|----------|
| 401 | `{"detail": "Invalid or expired refresh token"}` |
| 401 | `{"detail": "Authentication is not configured"}` |

:::{note}
Some auth backends may return the same refresh token, while others rotate it on each refresh.
:::

---

### Get Current User

Return information about the currently authenticated user.

```{rubric} GET /api/auth/me
```

**Headers**

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes | `Bearer <access_token>` |

**Example Request**

```http
GET /admin/api/auth/me HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Success Response (200 OK)**

```json
{
  "id": 1,
  "email": "admin@example.com",
  "roles": ["admin"],
  "permissions": ["models:read", "models:write", "models:delete"]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string or integer | User's unique identifier |
| `email` | string | User's email address |
| `roles` | array | List of assigned role names |
| `permissions` | array | List of permission strings |

**Error Responses**

| Status | Response |
|--------|----------|
| 401 | `{"detail": "Authentication is not configured"}` |
| 403 | `{"detail": "Not authenticated"}` |

---

## Authentication Flow

Here's a typical authentication flow for a frontend application:

1. **Login**: Client sends credentials to `POST /auth/login`
2. **Token Receipt**: Server returns access_token and refresh_token
3. **Token Storage**: Client stores tokens securely (httpOnly cookies or secure storage)
4. **API Requests**: Client includes `Authorization: Bearer {access_token}` header
5. **Token Expiration**: Access token expires (default: 15 minutes)
6. **Token Refresh**: Client sends refresh_token to `POST /auth/refresh`
7. **New Tokens**: Server returns fresh access_token (and optionally new refresh_token)

```text
Client                    Admin API                Auth Backend
  |                           |                         |
  |-- POST /auth/login ------>|                         |
  |   {email, password}       |-- authenticate() ------>|
  |                           |<-- user or null --------|
  |<-- {access_token,         |                         |
  |     refresh_token} -------|                         |
  |                           |                         |
  |-- GET /api/models ------->|                         |
  |   Authorization: Bearer   |-- validate token ------>|
  |                           |<-- user ----------------|
  |<-- model data ------------|                         |
  |                           |                         |
  |   [token expires]         |                         |
  |                           |                         |
  |-- POST /auth/refresh ---->|                         |
  |   {refresh_token}         |-- refresh() ----------->|
  |                           |<-- new tokens ----------|
  |<-- {access_token,         |                         |
  |     refresh_token} -------|                         |
```

## Roles and Permissions

litestar-admin includes a built-in RBAC (Role-Based Access Control) system.

### Available Roles

| Role | Description |
|------|-------------|
| `viewer` | Read-only access to models and dashboard |
| `editor` | Can create and update records |
| `admin` | Full model management, user management, audit access |
| `superadmin` | Complete access to all features |

### Available Permissions

| Permission | Description |
|------------|-------------|
| `models:read` | Read and list model records |
| `models:write` | Create and update records |
| `models:delete` | Delete records |
| `models:export` | Export model data |
| `dashboard:view` | View the admin dashboard |
| `users:manage` | Manage admin users |
| `settings:manage` | Manage admin settings |
| `audit:view` | View audit logs |

### Role-Permission Mapping

| Role | Permissions |
|------|-------------|
| `viewer` | `models:read`, `dashboard:view` |
| `editor` | viewer + `models:write` |
| `admin` | editor + `models:delete`, `models:export`, `users:manage`, `audit:view` |
| `superadmin` | admin + `settings:manage` |

## Custom Auth Backends

You can implement custom authentication by creating a class that implements the `AuthBackend` protocol:

```python
from litestar_admin.auth import AuthBackend, AdminUser

class MyAuthBackend(AuthBackend):
    async def authenticate(self, connection, credentials):
        # Verify credentials, return AdminUser or None
        ...

    async def get_current_user(self, connection):
        # Extract and validate token, return AdminUser or None
        ...

    async def login(self, connection, user):
        # Create tokens, return {"access_token": ..., "refresh_token": ...}
        ...

    async def logout(self, connection):
        # Invalidate tokens if needed
        ...

    async def refresh(self, connection):
        # Validate refresh token, return new tokens or None
        ...
```

Then configure it in `AdminConfig`:

```python
app = Litestar(
    plugins=[
        AdminPlugin(
            config=AdminConfig(
                auth_backend=MyAuthBackend(),
            )
        )
    ]
)
```

## Security Considerations

:::{warning}
Never expose tokens in URLs or logs. Always use HTTPS in production.
:::

Best practices for token handling:

1. **Store tokens securely**: Use `httpOnly` cookies or secure storage mechanisms
2. **Use short access token lifetimes**: 15 minutes is a reasonable default
3. **Implement token rotation**: Rotate refresh tokens on each use
4. **Validate on every request**: Always verify the token signature and expiration
5. **Use HTTPS**: Never transmit tokens over unencrypted connections
