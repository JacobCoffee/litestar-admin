# Configuration Reference

This page provides a complete reference for all configuration options available in litestar-admin.

## AdminConfig

The `AdminConfig` dataclass is the primary way to configure your admin panel. Pass it to the `AdminPlugin` when initializing your application.

```python
from litestar_admin import AdminPlugin, AdminConfig

plugin = AdminPlugin(
    config=AdminConfig(
        title="My Admin",
        base_url="/admin",
        # ... more options
    )
)
```

### Basic Settings

#### title

- **Type:** `str`
- **Default:** `"Admin"`

The title displayed in the admin panel header and browser tab.

```python
AdminConfig(title="My Application Admin")
```

#### base_url

- **Type:** `str`
- **Default:** `"/admin"`

The base URL path for the admin panel. All admin routes will be prefixed with this path.

```python
# Admin available at /dashboard
AdminConfig(base_url="/dashboard")

# Admin available at /app/admin
AdminConfig(base_url="/app/admin")
```

```{note}
The `base_url` must start with `/` and should not end with `/` (except when set to just `/`).
```

#### logo_url

- **Type:** `str | None`
- **Default:** `None`

URL for a custom logo image displayed in the sidebar header.

```python
AdminConfig(logo_url="/static/images/logo.png")
```

#### favicon_url

- **Type:** `str | None`
- **Default:** `None`

URL for a custom favicon.

```python
AdminConfig(favicon_url="/static/favicon.ico")
```

#### theme

- **Type:** `Literal["dark", "light"]`
- **Default:** `"dark"`

The color theme for the admin panel.

```python
# Dark theme (default, Cloudflare-inspired)
AdminConfig(theme="dark")

# Light theme
AdminConfig(theme="light")
```

### Authentication

#### auth_backend

- **Type:** `AuthBackend | None`
- **Default:** `None`

The authentication backend for securing the admin panel. When `None`, the admin panel is publicly accessible.

```python
from litestar_admin.auth import JWTAuthBackend, JWTConfig

backend = JWTAuthBackend(
    config=JWTConfig(secret_key="your-secret-key"),
    user_loader=load_user_from_db,
)

AdminConfig(auth_backend=backend)
```

See {doc}`authentication` for detailed authentication setup.

### Model Views

#### views

- **Type:** `list[type[BaseModelView]]`
- **Default:** `[]`

List of model view classes to register with the admin panel.

```python
from litestar_admin import AdminConfig, ModelView

class UserAdmin(ModelView, model=User):
    column_list = ["id", "email"]

class PostAdmin(ModelView, model=Post):
    column_list = ["id", "title"]

AdminConfig(views=[UserAdmin, PostAdmin])
```

#### auto_discover

- **Type:** `bool`
- **Default:** `True`

Whether to automatically discover and register SQLAlchemy models that don't have explicit views defined.

```python
# Auto-discover all models (creates default views)
AdminConfig(auto_discover=True)

# Only use explicitly registered views
AdminConfig(auto_discover=False)
```

When enabled, the admin plugin will:
1. Scan for all SQLAlchemy `DeclarativeBase` classes in your application
2. Find all model classes registered with those bases
3. Create default views for models that don't have explicit view classes
4. Skip models that already have registered views

### Development

#### debug

- **Type:** `bool`
- **Default:** `False`

Enable debug mode for additional logging and error details.

```python
AdminConfig(debug=True)
```

```{warning}
Do not enable debug mode in production as it may expose sensitive information.
```

### Rate Limiting

#### rate_limit_enabled

- **Type:** `bool`
- **Default:** `True`

Whether to enable rate limiting on admin API endpoints.

```python
# Disable rate limiting (not recommended for production)
AdminConfig(rate_limit_enabled=False)
```

#### rate_limit_requests

- **Type:** `int`
- **Default:** `100`

Maximum number of requests allowed per window.

```python
AdminConfig(rate_limit_requests=200)
```

#### rate_limit_window_seconds

- **Type:** `int`
- **Default:** `60`

Rate limit window duration in seconds.

```python
# 50 requests per 30 seconds
AdminConfig(
    rate_limit_requests=50,
    rate_limit_window_seconds=30,
)
```

### Static Files

#### static_path

- **Type:** `str | None`
- **Default:** `None`

Path to a custom static files directory. When `None`, uses the built-in frontend.

```python
# Use custom frontend build
AdminConfig(static_path="/path/to/custom/frontend/dist")
```

### UI Customization

#### index_title

- **Type:** `str`
- **Default:** `"Dashboard"`

Title for the dashboard/index page.

```python
AdminConfig(index_title="Overview")
```

### Session Settings

#### session_cookie_name

- **Type:** `str`
- **Default:** `"admin_session"`

Name of the session cookie.

```python
AdminConfig(session_cookie_name="my_admin_session")
```

#### session_cookie_httponly

- **Type:** `bool`
- **Default:** `True`

Whether the session cookie should be HTTP-only (not accessible via JavaScript).

```python
AdminConfig(session_cookie_httponly=True)
```

#### session_cookie_secure

- **Type:** `bool`
- **Default:** `True`

Whether the session cookie should only be sent over HTTPS.

```python
# Disable for local development
AdminConfig(session_cookie_secure=False)
```

```{warning}
Always set `session_cookie_secure=True` in production with HTTPS.
```

#### session_cookie_samesite

- **Type:** `Literal["lax", "strict", "none"]`
- **Default:** `"lax"`

SameSite policy for the session cookie.

```python
AdminConfig(session_cookie_samesite="strict")
```

### Extra Settings

#### extra

- **Type:** `dict[str, Any]`
- **Default:** `{}`

Additional custom settings for extensibility.

```python
AdminConfig(
    extra={
        "custom_setting": "value",
        "feature_flag": True,
    }
)
```

## Complete Example

Here's a comprehensive configuration example:

```python
from litestar_admin import AdminPlugin, AdminConfig, ModelView
from litestar_admin.auth import JWTAuthBackend, JWTConfig

# Define your model views
class UserAdmin(ModelView, model=User):
    column_list = ["id", "email", "name", "is_active"]
    column_searchable_list = ["email", "name"]

class PostAdmin(ModelView, model=Post):
    column_list = ["id", "title", "published"]

# Create auth backend
async def load_user(user_id: str | int):
    # Load user from database
    ...

auth_backend = JWTAuthBackend(
    config=JWTConfig(
        secret_key="your-secure-secret-key",
        token_expiry=3600,
    ),
    user_loader=load_user,
)

# Configure admin
config = AdminConfig(
    # Basic settings
    title="My Application Admin",
    base_url="/admin",
    logo_url="/static/logo.png",
    theme="dark",

    # Authentication
    auth_backend=auth_backend,

    # Model views
    views=[UserAdmin, PostAdmin],
    auto_discover=True,

    # Rate limiting
    rate_limit_enabled=True,
    rate_limit_requests=100,
    rate_limit_window_seconds=60,

    # Session security
    session_cookie_secure=True,
    session_cookie_httponly=True,
    session_cookie_samesite="lax",

    # UI customization
    index_title="Dashboard",
)

# Create plugin
plugin = AdminPlugin(config=config)
```

## Environment Variables

You can load configuration from environment variables:

```python
import os

AdminConfig(
    title=os.getenv("ADMIN_TITLE", "Admin"),
    debug=os.getenv("DEBUG", "false").lower() == "true",
    rate_limit_requests=int(os.getenv("RATE_LIMIT_REQUESTS", "100")),
)
```

## Computed Properties

`AdminConfig` provides several computed properties:

### api_base_url

Returns the full API base URL (e.g., `/admin/api`).

```python
config = AdminConfig(base_url="/admin")
print(config.api_base_url)  # "/admin/api"
```

### static_base_url

Returns the full static files base URL (e.g., `/admin/static`).

```python
config = AdminConfig(base_url="/admin")
print(config.static_base_url)  # "/admin/static"
```

## Validation

`AdminConfig` validates settings on initialization:

```python
# This will raise ValueError
AdminConfig(base_url="admin")  # Must start with /

# This will raise ValueError
AdminConfig(rate_limit_requests=0)  # Must be at least 1
```
