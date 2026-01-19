# Custom Views and Embeds

Beyond model-based views, litestar-admin provides several specialized view types for building rich admin interfaces. This guide covers all non-model view types and when to use them.

## View Type Overview

litestar-admin supports six view types, each designed for specific use cases:

| View Type | Use Case | Has API Routes |
|-----------|----------|----------------|
| `ModelView` | CRUD operations on SQLAlchemy models | Yes |
| `CustomView` | Data from non-model sources (APIs, files, memory) | Yes |
| `ActionView` | One-off admin operations with forms | Yes |
| `PageView` | Static or dynamic content pages | Yes |
| `LinkView` | External navigation links | No |
| `EmbedView` | Embedded iframes or React components | Yes |

## BaseAdminView

All view types inherit from `BaseAdminView`, which provides common functionality for navigation, access control, and identification.

### Common Attributes

```python
from litestar_admin.views import BaseAdminView

class MyView(BaseAdminView):
    # Display name in sidebar
    name = "My View"

    # Plural display name (auto-generated if not set)
    name_plural = "My Views"

    # URL-safe identifier (auto-generated from name)
    identity = "my-view"

    # Icon name for sidebar (FontAwesome)
    icon = "file"

    # Category for sidebar grouping
    category = "Tools"

    # Sort order within category (lower = higher)
    order = 0

    # Whether to show in navigation
    is_visible = True

    # Default access control
    can_access = True

    # Permission/role requirements
    required_permission = "admin.view"
    required_role = "admin"
```

### Access Control

Override `is_accessible` for dynamic access control:

```python
from litestar.connection import ASGIConnection

class SecureView(BaseAdminView):
    @classmethod
    async def is_accessible(cls, connection: ASGIConnection) -> bool:
        user = getattr(connection, "user", None)
        return user is not None and user.is_admin
```

## CustomView

`CustomView` enables admin interfaces for data that doesn't come from SQLAlchemy models. Use it for external APIs, files, in-memory data, or any custom data source.

### Column Definitions

Unlike model views that introspect the database schema, custom views require explicit column definitions:

```python
from litestar_admin.views import CustomView, ColumnDefinition, ListResult

class ExternalUsersView(CustomView):
    name = "External Users"
    icon = "users"
    pk_field = "id"

    columns = [
        ColumnDefinition(
            name="id",
            label="ID",
            type="integer",
            sortable=True,
        ),
        ColumnDefinition(
            name="email",
            label="Email Address",
            type="email",
            searchable=True,
        ),
        ColumnDefinition(
            name="name",
            label="Full Name",
            type="string",
            sortable=True,
            searchable=True,
        ),
        ColumnDefinition(
            name="created_at",
            label="Created",
            type="datetime",
            sortable=True,
        ),
        ColumnDefinition(
            name="is_active",
            label="Active",
            type="boolean",
            filterable=True,
        ),
    ]
```

#### ColumnDefinition Options

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | Required | Internal field name |
| `label` | `str` | Auto from name | Display label |
| `type` | `str` | `"string"` | Data type (see below) |
| `sortable` | `bool` | `False` | Enable sorting |
| `searchable` | `bool` | `False` | Include in search |
| `filterable` | `bool` | `False` | Enable filtering |
| `visible` | `bool` | `True` | Show in list view |
| `format` | `str` | `None` | Display format |
| `render_template` | `str` | `None` | Custom render template |

#### Supported Column Types

- `string` - Plain text
- `text` - Long text
- `integer` - Whole numbers
- `float` - Decimal numbers
- `boolean` - True/false
- `datetime` - Date and time
- `date` - Date only
- `time` - Time only
- `email` - Email address
- `url` - Web URL
- `uuid` - UUID string
- `json` - JSON object

### Data Provider Methods

Custom views must implement at least `get_list` and `get_one`:

```python
from typing import Any, Literal

class MyCustomView(CustomView):
    # ... column definitions ...

    async def get_list(
        self,
        page: int = 1,
        page_size: int = 25,
        filters: dict[str, Any] | None = None,
        sort_by: str | None = None,
        sort_order: Literal["asc", "desc"] = "asc",
        search: str | None = None,
    ) -> ListResult:
        """Fetch paginated list of items."""
        # Implement your data fetching logic
        items = await fetch_from_source()

        return ListResult(
            items=items,
            total=len(items),
            page=page,
            page_size=page_size,
        )

    async def get_one(self, item_id: str) -> dict[str, Any] | None:
        """Fetch a single item by ID."""
        # Implement your single-item fetch
        return await fetch_item(item_id)
```

### Optional CRUD Methods

Enable create, update, and delete by implementing these methods and setting the corresponding flags:

```python
class EditableCustomView(CustomView):
    can_create = True
    can_edit = True
    can_delete = True

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new item."""
        # Validate and create
        return created_item

    async def update(self, item_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing item."""
        # Validate and update
        return updated_item

    async def delete(self, item_id: str) -> bool:
        """Delete an item."""
        # Perform deletion
        return True
```

### Lifecycle Hooks

Custom views support hooks for preprocessing and side effects:

```python
class HookedCustomView(CustomView):
    async def on_before_create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Modify data before creating."""
        data["created_at"] = datetime.utcnow().isoformat()
        return data

    async def on_after_create(self, item: dict[str, Any]) -> None:
        """Side effects after creating."""
        await send_notification(f"Created: {item['id']}")

    async def on_before_update(
        self,
        item_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Modify data before updating."""
        data["updated_at"] = datetime.utcnow().isoformat()
        return data

    async def on_after_update(self, item: dict[str, Any]) -> None:
        """Side effects after updating."""
        await invalidate_cache(item["id"])

    async def on_before_delete(self, item_id: str) -> None:
        """Actions before deleting."""
        await backup_item(item_id)

    async def on_after_delete(self, item_id: str) -> None:
        """Cleanup after deleting."""
        await remove_from_search_index(item_id)
```

## Built-in Data Providers

litestar-admin includes three pre-built CustomView implementations for common data sources.

### InMemoryView

Stores data in memory. Useful for settings, caches, or testing.

```python
from litestar_admin.contrib.providers import InMemoryView
from litestar_admin.views import ColumnDefinition

class AppSettingsView(InMemoryView):
    name = "App Settings"
    icon = "cog"
    pk_field = "key"
    can_create = True
    can_edit = True
    can_delete = True

    columns = [
        ColumnDefinition(name="key", type="string", sortable=True),
        ColumnDefinition(name="value", type="string"),
        ColumnDefinition(name="description", type="text"),
    ]

    # Pre-populate with default settings
    _data = {
        "site_name": {
            "key": "site_name",
            "value": "My Application",
            "description": "Displayed in the header",
        },
        "maintenance_mode": {
            "key": "maintenance_mode",
            "value": "false",
            "description": "Enable maintenance mode",
        },
    }
```

#### InMemoryView Features

- **Auto-generate primary keys**: Set `auto_generate_pk = True` to auto-generate UUIDs
- **Seed data**: Use `seed_data()` class method to populate initial data
- **Clear data**: Use `clear_data()` class method to reset the store

```python
# Seed data at startup
AppSettingsView.seed_data([
    {"key": "theme", "value": "dark"},
    {"key": "language", "value": "en"},
])

# Clear all data
AppSettingsView.clear_data()
```

```{warning}
Data in `InMemoryView` is lost when the application restarts. Use `JSONFileView` or a database for persistence.
```

### JSONFileView

Stores data in a JSON file for simple persistence.

```python
from litestar_admin.contrib.providers import JSONFileView
from litestar_admin.views import ColumnDefinition

class BookmarksView(JSONFileView):
    name = "Bookmarks"
    icon = "bookmark"
    file_path = "/data/bookmarks.json"  # Required
    can_create = True
    can_edit = True
    can_delete = True

    columns = [
        ColumnDefinition(name="id", type="uuid"),
        ColumnDefinition(name="title", type="string", sortable=True, searchable=True),
        ColumnDefinition(name="url", type="url"),
        ColumnDefinition(name="tags", type="json"),
        ColumnDefinition(name="created_at", type="datetime"),
    ]

    # Optional configuration
    auto_generate_pk = True  # Auto-generate UUID for new items
    create_file_if_missing = True  # Create file if it doesn't exist
    indent = 2  # JSON indentation (None for compact)
```

#### JSONFileView Options

| Attribute | Default | Description |
|-----------|---------|-------------|
| `file_path` | Required | Path to JSON file |
| `auto_generate_pk` | `True` | Auto-generate UUIDs for new items |
| `create_file_if_missing` | `True` | Create file if it doesn't exist |
| `indent` | `2` | JSON indentation |

```{note}
`JSONFileView` uses synchronous file I/O. For high-concurrency scenarios, consider using a proper database or implementing async file operations with `aiofiles`.
```

### HTTPAPIView

Fetches data from external REST APIs.

```python
from litestar_admin.contrib.providers import HTTPAPIView
from litestar_admin.views import ColumnDefinition

class GitHubReposView(HTTPAPIView):
    name = "GitHub Repositories"
    icon = "github"

    # API configuration
    api_base_url = "https://api.github.com"
    api_headers = {"Accept": "application/vnd.github.v3+json"}
    api_timeout = 30.0

    # Endpoint paths
    list_endpoint = "/users/octocat/repos"
    detail_endpoint = "/repos/octocat/{id}"

    # Response parsing
    items_key = None  # Response is a list directly
    total_key = None  # Use len(items) for total

    # Request parameter names
    page_param = "page"
    page_size_param = "per_page"

    columns = [
        ColumnDefinition(name="id", type="integer"),
        ColumnDefinition(name="name", type="string", sortable=True),
        ColumnDefinition(name="full_name", type="string"),
        ColumnDefinition(name="description", type="text", searchable=True),
        ColumnDefinition(name="stargazers_count", type="integer", sortable=True),
        ColumnDefinition(name="html_url", type="url"),
    ]
```

#### HTTPAPIView Options

| Attribute | Default | Description |
|-----------|---------|-------------|
| `api_base_url` | Required | Base URL for API |
| `api_headers` | `{}` | Default request headers |
| `api_timeout` | `30.0` | Request timeout (seconds) |
| `list_endpoint` | `""` | Endpoint for listing |
| `detail_endpoint` | `"/{id}"` | Endpoint for single item |
| `create_endpoint` | `""` | Endpoint for creating |
| `update_endpoint` | `"/{id}"` | Endpoint for updating |
| `delete_endpoint` | `"/{id}"` | Endpoint for deleting |
| `items_key` | `"items"` | Response key for items list |
| `total_key` | `"total"` | Response key for total count |
| `page_param` | `"page"` | Query param for page |
| `page_size_param` | `"page_size"` | Query param for page size |
| `search_param` | `"search"` | Query param for search |
| `sort_param` | `"sort_by"` | Query param for sort field |
| `order_param` | `"sort_order"` | Query param for sort order |

#### Custom Request Handling

Override methods for custom API interactions:

```python
class CustomAPIView(HTTPAPIView):
    username = "octocat"  # Custom parameter

    async def get_list(self, **kwargs) -> ListResult:
        # Build custom endpoint
        endpoint = f"/users/{self.username}/repos"
        return await self._fetch_list(endpoint, **kwargs)

    async def get_one(self, item_id: str) -> dict[str, Any] | None:
        endpoint = f"/repos/{self.username}/{item_id}"
        return await self._fetch_one(endpoint)
```

```{note}
`HTTPAPIView` requires the `httpx` package. Install with: `pip install httpx`
```

## ActionView

`ActionView` creates standalone admin actions with optional form inputs. Use it for one-off operations like cache clearing, data imports, or maintenance tasks.

### Basic Action

```python
from litestar_admin.views import ActionView, ActionResult

class ClearCacheAction(ActionView):
    name = "Clear Cache"
    icon = "trash"
    category = "Maintenance"
    confirmation_message = "Are you sure you want to clear the cache?"

    async def execute(self, data: dict[str, Any]) -> ActionResult:
        await cache_service.clear_all()
        return ActionResult(
            success=True,
            message="Cache cleared successfully!",
        )
```

### Form Fields

Add input fields to collect data before execution:

```python
from litestar_admin.views import ActionView, ActionResult, FormField

class SendNewsletterAction(ActionView):
    name = "Send Newsletter"
    icon = "envelope"
    category = "Marketing"
    submit_label = "Send Now"
    dangerous = True  # Shows warning styling

    form_fields = [
        FormField(
            name="subject",
            label="Email Subject",
            field_type="text",
            required=True,
            placeholder="Enter subject line...",
        ),
        FormField(
            name="template",
            label="Template",
            field_type="select",
            required=True,
            options=[
                {"value": "weekly", "label": "Weekly Digest"},
                {"value": "promo", "label": "Promotional"},
                {"value": "announcement", "label": "Announcement"},
            ],
        ),
        FormField(
            name="audience",
            label="Target Audience",
            field_type="multiselect",
            options=[
                {"value": "all", "label": "All Subscribers"},
                {"value": "active", "label": "Active Users Only"},
                {"value": "premium", "label": "Premium Members"},
            ],
        ),
        FormField(
            name="schedule",
            label="Send Time",
            field_type="datetime",
            help_text="Leave empty to send immediately",
        ),
        FormField(
            name="confirm",
            label="I understand this will send emails to real users",
            field_type="checkbox",
            required=True,
        ),
    ]

    async def execute(self, data: dict[str, Any]) -> ActionResult:
        count = await newsletter_service.send(
            subject=data["subject"],
            template=data["template"],
            audience=data.get("audience", ["all"]),
            scheduled_for=data.get("schedule"),
        )
        return ActionResult(
            success=True,
            message=f"Newsletter queued for {count} recipients!",
            data={"recipient_count": count},
        )
```

#### FormField Types

| Type | Description |
|------|-------------|
| `text` | Single-line text input |
| `textarea` | Multi-line text input |
| `number` | Numeric input |
| `email` | Email input with validation |
| `password` | Password input (masked) |
| `select` | Single-select dropdown |
| `multiselect` | Multi-select dropdown |
| `checkbox` | Boolean checkbox |
| `radio` | Radio button group |
| `date` | Date picker |
| `datetime` | Date and time picker |
| `file` | File upload |
| `hidden` | Hidden field |

#### FormField Options

```python
FormField(
    name="field_name",           # Required: field identifier
    label="Display Label",       # Required: display text
    field_type="text",          # Input type
    required=False,             # Is field required?
    default=None,               # Default value
    placeholder="",             # Placeholder text
    help_text="",               # Help text below field
    options=[],                 # Options for select/radio
    validation={                # Validation rules
        "min": 0,
        "max": 100,
        "pattern": r"^\d+$",
    },
)
```

### ActionResult

The `execute` method must return an `ActionResult`:

```python
ActionResult(
    success=True,                           # Success or failure
    message="Operation completed",          # User-facing message
    redirect="/admin/users",                # Optional redirect URL
    data={"key": "value"},                  # Optional response data
    refresh=True,                           # Refresh current view?
)
```

### Action Configuration

```python
class MyAction(ActionView):
    # Confirmation
    confirmation_message = "Are you sure?"  # Optional confirmation
    requires_confirmation = True            # Show confirmation dialog

    # UI
    submit_label = "Execute"                # Submit button text
    dangerous = False                       # Dangerous action styling

    # Execution
    success_redirect = "/admin/logs"        # Redirect on success
    run_in_background = False               # Run asynchronously
    timeout_seconds = 60                    # Execution timeout
```

### Custom Validation

Override `validate_data` for complex validation:

```python
class DateRangeAction(ActionView):
    form_fields = [
        FormField(name="start_date", field_type="date", required=True),
        FormField(name="end_date", field_type="date", required=True),
    ]

    @classmethod
    async def validate_data(cls, data: dict[str, Any]) -> tuple[bool, str | None]:
        # First run default validation
        is_valid, error = await super().validate_data(data)
        if not is_valid:
            return is_valid, error

        # Custom validation
        if data["start_date"] > data["end_date"]:
            return False, "Start date must be before end date"

        return True, None
```

### Authorization

Control who can execute actions:

```python
class AdminOnlyAction(ActionView):
    @classmethod
    async def can_execute(cls, connection: ASGIConnection) -> bool:
        user = getattr(connection, "user", None)
        return user is not None and "admin" in user.roles
```

## PageView

`PageView` creates content pages within the admin panel. Use it for documentation, dashboards, help pages, or any custom content.

### Static Content

For simple static pages, set the content directly:

```python
from litestar_admin.views import PageView

class AboutPage(PageView):
    name = "About"
    icon = "info-circle"
    content_type = "markdown"
    content = """
# About This Admin Panel

Welcome to the administration interface for MyApp.

## Features

- User management with role-based access
- Content editing and publishing
- Analytics and reporting dashboard
- Audit logging for compliance

## Getting Help

Contact support at support@example.com
"""
```

#### Content Types

| Type | Description |
|------|-------------|
| `markdown` | Markdown content (rendered to HTML) |
| `html` | Raw HTML content |
| `text` | Plain text |
| `dynamic` | Content fetched via `get_content()` |
| `template` | Server-side template rendering |

### Dynamic Content

For pages with dynamic data, use `content_type = "dynamic"` and override `get_content`:

```python
class AnalyticsDashboard(PageView):
    name = "Analytics"
    icon = "chart-bar"
    content_type = "dynamic"
    refresh_interval = 60  # Auto-refresh every 60 seconds

    async def get_content(self) -> dict[str, Any]:
        users_count = await User.count()
        orders_today = await Order.count_today()
        revenue = await Order.total_revenue_today()

        return {
            "type": "dashboard",
            "widgets": [
                {
                    "type": "stat",
                    "title": "Total Users",
                    "value": users_count,
                    "icon": "users",
                },
                {
                    "type": "stat",
                    "title": "Orders Today",
                    "value": orders_today,
                    "icon": "shopping-cart",
                    "change": "+12%",
                },
                {
                    "type": "stat",
                    "title": "Revenue Today",
                    "value": f"${revenue:,.2f}",
                    "icon": "dollar-sign",
                },
                {
                    "type": "chart",
                    "title": "Weekly Signups",
                    "chart_type": "line",
                    "data": await get_signup_chart_data(),
                },
            ],
        }
```

### Template-Based Pages

For complex layouts, use templates:

```python
class SettingsPage(PageView):
    name = "Settings"
    icon = "cog"
    content_type = "template"
    template = "admin/settings.html"
    template_context = {
        "show_advanced": False,
    }

    async def get_template_context(
        self,
        connection: ASGIConnection,
    ) -> dict[str, Any]:
        context = await super().get_template_context(connection)
        context["current_user"] = connection.user
        context["settings"] = await Settings.get_all()
        return context
```

### Page Layout Options

```python
class WideContentPage(PageView):
    layout = "full-width"  # "default", "full-width", or "sidebar"
```

## LinkView

`LinkView` adds external links to the admin navigation without any associated routes.

```python
from litestar_admin.views import LinkView

class DocumentationLink(LinkView):
    name = "Documentation"
    icon = "book"
    url = "https://docs.example.com"
    target = "_blank"  # Open in new tab

class APIDocsLink(LinkView):
    name = "API Reference"
    icon = "code"
    category = "Developer"
    url = "/api/docs"
    target = "_self"  # Open in same tab
```

### Dynamic URLs

Override `get_url` for dynamic link generation:

```python
class EnvironmentDocsLink(LinkView):
    name = "Environment Docs"
    icon = "external-link"

    def get_url(self) -> str:
        if settings.ENV == "production":
            return "https://docs.prod.example.com"
        return "https://docs.dev.example.com"
```

### Conditional Links

Control link visibility based on user permissions:

```python
class AdminDocsLink(LinkView):
    name = "Admin Guide"
    url = "https://internal.example.com/admin-guide"

    @classmethod
    async def is_accessible(cls, connection: ASGIConnection) -> bool:
        user = getattr(connection, "user", None)
        return user is not None and user.is_staff
```

## EmbedView

`EmbedView` embeds external content or custom React components within the admin panel.

### Iframe Embeds

Embed external dashboards, tools, or documentation:

```python
from litestar_admin.views import EmbedView

class GrafanaMetrics(EmbedView):
    name = "Metrics"
    icon = "chart-line"
    category = "Monitoring"

    embed_type = "iframe"
    embed_url = "https://grafana.example.com/d/abc123?orgId=1"

    # Dimensions
    height = "800px"
    width = "100%"
    min_height = "400px"

    # Security
    sandbox = "allow-scripts allow-same-origin"
    allow = "fullscreen"
    referrer_policy = "strict-origin-when-cross-origin"

    # Behavior
    loading = "lazy"  # "eager" or "lazy"
    show_toolbar = True  # Show refresh/fullscreen buttons
    refresh_interval = 300  # Auto-refresh every 5 minutes
```

### Dynamic Iframe URLs

Generate URLs dynamically, for example to include auth tokens:

```python
class UserSpecificDashboard(EmbedView):
    name = "My Dashboard"
    embed_type = "iframe"
    embed_url = "https://dashboard.example.com"

    async def get_embed_url(self, connection: ASGIConnection) -> str:
        user = connection.user
        token = await generate_dashboard_token(user.id)
        return f"{self.embed_url}?user={user.id}&token={token}&theme=dark"
```

### Component Embeds

Embed registered React components:

```python
class ActivityFeed(EmbedView):
    name = "Activity Feed"
    icon = "activity"

    embed_type = "component"
    component_name = "ActivityFeed"  # Must be registered in frontend

    # Static props
    props = {
        "limit": 20,
        "showTimestamps": True,
    }

    # Layout
    layout = "sidebar"  # "full", "sidebar", or "card"

    async def get_props(self, connection: ASGIConnection) -> dict[str, Any]:
        """Dynamic props based on current user."""
        user = connection.user
        return {
            "userId": user.id if user else None,
            "limit": 20,
            "showTimestamps": True,
            "theme": user.preferences.get("theme", "dark") if user else "dark",
        }
```

### Iframe Security Options

| Attribute | Default | Description |
|-----------|---------|-------------|
| `sandbox` | `"allow-scripts allow-same-origin allow-forms allow-popups"` | Iframe sandbox restrictions |
| `allow` | `""` | Feature policy permissions |
| `referrer_policy` | `"strict-origin-when-cross-origin"` | Referrer policy |
| `loading` | `"lazy"` | Loading strategy |

### Layout Options

| Layout | Description |
|--------|-------------|
| `full` | Full-page embed (default) |
| `sidebar` | Sidebar panel embed |
| `card` | Card within dashboard |

## Registering Views

Register all view types in your `AdminConfig`:

```python
from litestar import Litestar
from litestar_admin import AdminPlugin, AdminConfig, ModelView

# Model views
class UserAdmin(ModelView, model=User):
    column_list = ["id", "email", "name"]

class PostAdmin(ModelView, model=Post):
    column_list = ["id", "title"]

# Custom views
class SettingsView(InMemoryView):
    name = "Settings"
    # ...

# Actions
class ClearCacheAction(ActionView):
    name = "Clear Cache"
    # ...

# Pages
class AboutPage(PageView):
    name = "About"
    # ...

# Links
class DocsLink(LinkView):
    name = "Documentation"
    url = "https://docs.example.com"

# Embeds
class MetricsEmbed(EmbedView):
    name = "Metrics"
    embed_url = "https://grafana.example.com"

# Register all views
app = Litestar(
    plugins=[
        AdminPlugin(
            config=AdminConfig(
                title="My Admin",
                views=[
                    # Model views
                    UserAdmin,
                    PostAdmin,
                    # Custom views
                    SettingsView,
                    # Actions
                    ClearCacheAction,
                    # Pages
                    AboutPage,
                    # Links
                    DocsLink,
                    # Embeds
                    MetricsEmbed,
                ],
            )
        )
    ]
)
```

### View Ordering

Control the order of views in the sidebar:

```python
class FirstView(PageView):
    name = "First"
    order = 1  # Lower numbers appear first

class SecondView(PageView):
    name = "Second"
    order = 2

class LastView(PageView):
    name = "Last"
    order = 100
```

### Grouping with Categories

Group views in the sidebar using categories:

```python
class UserAdmin(ModelView, model=User):
    category = "Users & Access"

class RoleAdmin(ModelView, model=Role):
    category = "Users & Access"

class ProductAdmin(ModelView, model=Product):
    category = "Store"

class ClearCacheAction(ActionView):
    category = "Maintenance"

class BackupAction(ActionView):
    category = "Maintenance"
```

## Complete Example

Here's a comprehensive example combining multiple view types:

```python
from __future__ import annotations

from typing import Any

from litestar import Litestar
from litestar.connection import ASGIConnection

from litestar_admin import AdminPlugin, AdminConfig, ModelView
from litestar_admin.views import (
    ActionView,
    ActionResult,
    ColumnDefinition,
    EmbedView,
    FormField,
    LinkView,
    PageView,
)
from litestar_admin.contrib.providers import InMemoryView, HTTPAPIView

from myapp.models import User, Post, AuditLog


# Model Views
class UserAdmin(ModelView, model=User):
    name = "Users"
    icon = "users"
    category = "User Management"
    column_list = ["id", "email", "name", "is_active", "created_at"]
    column_searchable_list = ["email", "name"]
    can_delete = False


class PostAdmin(ModelView, model=Post):
    name = "Posts"
    icon = "file-text"
    category = "Content"
    column_list = ["id", "title", "author", "status", "published_at"]


class AuditLogAdmin(ModelView, model=AuditLog):
    name = "Audit Logs"
    icon = "list"
    category = "System"
    can_create = False
    can_edit = False
    can_delete = False


# Custom View for App Settings
class AppSettingsView(InMemoryView):
    name = "App Settings"
    icon = "cog"
    category = "Configuration"
    pk_field = "key"

    columns = [
        ColumnDefinition(name="key", type="string", sortable=True),
        ColumnDefinition(name="value", type="string"),
        ColumnDefinition(name="description", type="text"),
    ]

    _data = {
        "site_name": {
            "key": "site_name",
            "value": "My Application",
            "description": "Site name shown in header",
        },
        "maintenance_mode": {
            "key": "maintenance_mode",
            "value": "false",
            "description": "Enable site-wide maintenance mode",
        },
    }


# External API View
class GitHubIssuesView(HTTPAPIView):
    name = "GitHub Issues"
    icon = "github"
    category = "Integrations"

    api_base_url = "https://api.github.com"
    api_headers = {"Accept": "application/vnd.github.v3+json"}
    list_endpoint = "/repos/owner/repo/issues"
    items_key = None

    columns = [
        ColumnDefinition(name="number", type="integer", sortable=True),
        ColumnDefinition(name="title", type="string", searchable=True),
        ColumnDefinition(name="state", type="string", filterable=True),
        ColumnDefinition(name="created_at", type="datetime", sortable=True),
    ]


# Admin Actions
class ClearCacheAction(ActionView):
    name = "Clear Cache"
    icon = "trash"
    category = "Maintenance"
    confirmation_message = "This will clear all cached data. Continue?"

    form_fields = [
        FormField(
            name="cache_type",
            label="Cache Type",
            field_type="select",
            required=True,
            options=[
                {"value": "all", "label": "All Caches"},
                {"value": "user", "label": "User Cache"},
                {"value": "session", "label": "Session Cache"},
            ],
        ),
    ]

    async def execute(self, data: dict[str, Any]) -> ActionResult:
        cache_type = data.get("cache_type", "all")
        # await cache_service.clear(cache_type)
        return ActionResult(
            success=True,
            message=f"Successfully cleared {cache_type} cache!",
            refresh=True,
        )


class ExportDataAction(ActionView):
    name = "Export Data"
    icon = "download"
    category = "Data"
    submit_label = "Generate Export"

    form_fields = [
        FormField(
            name="format",
            label="Export Format",
            field_type="select",
            required=True,
            default="csv",
            options=[
                {"value": "csv", "label": "CSV"},
                {"value": "json", "label": "JSON"},
                {"value": "xlsx", "label": "Excel"},
            ],
        ),
        FormField(
            name="include_deleted",
            label="Include deleted records",
            field_type="checkbox",
        ),
    ]

    async def execute(self, data: dict[str, Any]) -> ActionResult:
        export_format = data.get("format", "csv")
        # Generate export and get download URL
        download_url = f"/admin/exports/download/123.{export_format}"
        return ActionResult(
            success=True,
            message="Export generated successfully!",
            redirect=download_url,
        )


# Content Pages
class AboutPage(PageView):
    name = "About"
    icon = "info-circle"
    content_type = "markdown"
    content = """
# Admin Panel

Welcome to the administration interface.

## Quick Links

- [User Guide](/docs/user-guide)
- [API Documentation](/api/docs)
- [Support](mailto:support@example.com)
"""


class DashboardPage(PageView):
    name = "Dashboard"
    icon = "tachometer-alt"
    content_type = "dynamic"
    refresh_interval = 60

    async def get_content(self) -> dict[str, Any]:
        return {
            "type": "dashboard",
            "widgets": [
                {"type": "stat", "title": "Users", "value": 1234},
                {"type": "stat", "title": "Posts", "value": 567},
                {"type": "stat", "title": "Revenue", "value": "$12,345"},
            ],
        }


# External Links
class DocsLink(LinkView):
    name = "Documentation"
    icon = "book"
    category = "Resources"
    url = "https://docs.example.com"
    target = "_blank"


class SupportLink(LinkView):
    name = "Get Support"
    icon = "life-ring"
    category = "Resources"
    url = "https://support.example.com"
    target = "_blank"


# Embedded Dashboards
class MetricsEmbed(EmbedView):
    name = "Server Metrics"
    icon = "chart-line"
    category = "Monitoring"

    embed_type = "iframe"
    embed_url = "https://grafana.example.com/d/server-metrics"
    height = "600px"
    sandbox = "allow-scripts allow-same-origin"
    refresh_interval = 60


# Create the application
app = Litestar(
    plugins=[
        AdminPlugin(
            config=AdminConfig(
                title="MyApp Admin",
                views=[
                    # High-priority pages first
                    DashboardPage,
                    # Model management
                    UserAdmin,
                    PostAdmin,
                    AuditLogAdmin,
                    # Custom data
                    AppSettingsView,
                    GitHubIssuesView,
                    # Actions
                    ClearCacheAction,
                    ExportDataAction,
                    # Info pages
                    AboutPage,
                    # Links
                    DocsLink,
                    SupportLink,
                    # Embeds
                    MetricsEmbed,
                ],
            )
        )
    ]
)
```

## API Reference

For complete API documentation, see:

- {class}`~litestar_admin.views.BaseAdminView`
- {class}`~litestar_admin.views.CustomView`
- {class}`~litestar_admin.views.ActionView`
- {class}`~litestar_admin.views.PageView`
- {class}`~litestar_admin.views.LinkView`
- {class}`~litestar_admin.views.EmbedView`
- {class}`~litestar_admin.contrib.providers.InMemoryView`
- {class}`~litestar_admin.contrib.providers.JSONFileView`
- {class}`~litestar_admin.contrib.providers.HTTPAPIView`
