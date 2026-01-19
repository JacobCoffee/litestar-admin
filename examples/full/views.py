"""ModelView configurations for the full admin demo.

This module defines the admin views for all models in the demo application,
showcasing various configuration options including:
- Column display and search configuration
- Form customization
- Permission controls
- Category grouping
- Custom model change hooks
- CustomView examples with data providers
- ActionView examples for one-off operations
- PageView examples for static/dynamic content pages
- LinkView examples for external navigation
- EmbedView examples for embedded content

Views:
    ModelViews:
        - UserAdmin: User management with restricted delete
        - ArticleAdmin: Content management with status workflow
        - TagAdmin: Tag management with slug handling

    CustomViews:
        - AppSettingsAdmin: In-memory settings store
        - SystemInfoAdmin: System information view (read-only)

    ActionViews:
        - ClearCacheAction: Simulated cache clear with confirmation
        - SendNotificationAction: Send notifications with form fields

    PageViews:
        - AboutPage: Static markdown about page
        - ChangelogPage: Dynamic changelog loading

    LinkViews:
        - DocsLink: Link to documentation
        - GitHubLink: Link to GitHub repository

    EmbedViews:
        - MetricsEmbed: Placeholder for metrics dashboard embedding
"""

from __future__ import annotations

import logging
import platform
import sys
from datetime import datetime, timezone
from typing import Any, ClassVar, Literal

from examples.full.models import Article, ArticleStatus, Tag, User
from litestar_admin import ModelView
from litestar_admin.contrib.providers import ColumnDefinition, InMemoryView, ListResult
from litestar_admin.views import ActionResult, ActionView, EmbedView, FormField, LinkView, PageView

__all__ = [
    # ModelViews
    "ArticleAdmin",
    "TagAdmin",
    "UserAdmin",
    # CustomViews
    "AppSettingsAdmin",
    "SystemInfoAdmin",
    # ActionViews
    "ClearCacheAction",
    "SendNotificationAction",
    # PageViews
    "AboutPage",
    "ChangelogPage",
    # LinkViews
    "DocsLink",
    "GitHubLink",
    # EmbedViews
    "MetricsEmbed",
]

logger = logging.getLogger(__name__)


class UserAdmin(ModelView, model=User):
    """Admin view for User model.

    Provides user management with the following features:
    - Email and name searchable
    - Sortable by created_at and email
    - Password hash excluded from forms (security)
    - Virtual 'password' field for user creation
    - Delete disabled for safety (use deactivation instead)
    """

    # Display configuration
    name = "User"
    name_plural = "Users"
    icon = "users"
    category = "Administration"

    # Column configuration
    column_list = ["id", "email", "name", "role", "is_active", "created_at"]
    column_searchable_list = ["email", "name"]
    column_sortable_list = ["id", "email", "created_at", "role", "is_active"]
    column_default_sort = ("created_at", "desc")

    # Form configuration - exclude sensitive/auto fields
    form_excluded_columns = ["password_hash", "articles", "created_at", "updated_at"]

    # Permission controls
    can_create = True
    can_edit = True
    can_delete = False  # Disable delete for safety - use is_active instead
    can_view_details = True
    can_export = True

    # Pagination
    page_size = 25
    page_size_options = [10, 25, 50, 100]

    @classmethod
    def get_form_extra_fields(cls, *, is_create: bool = False) -> dict[str, dict[str, Any]]:
        """Get extra virtual fields for user forms.

        Args:
            is_create: Whether this is for a create form.

        Returns:
            Dictionary with password field configuration.
        """
        return {
            "password": {
                "type": "string",
                "format": "password",
                "title": "Password",
                "description": "Enter password" + (" (required)" if is_create else " (leave empty to keep unchanged)"),
                "minLength": 8,
                "required": is_create,  # Required on create, optional on edit
            },
        }

    @classmethod
    async def on_model_change(
        cls,
        data: dict[str, Any],
        record: Any | None,
        *,
        is_create: bool,
    ) -> dict[str, Any]:
        """Handle user creation/update with password hashing.

        Args:
            data: The data being saved.
            record: The existing record (None for create).
            is_create: Whether this is a create operation.

        Returns:
            The modified data to save.
        """
        from examples.full.auth import hash_password

        # Hash password if provided
        if data.get("password"):
            data["password_hash"] = hash_password(data["password"])
            del data["password"]

        # Set default password for new users if none provided
        if is_create and "password_hash" not in data:
            data["password_hash"] = hash_password("changeme123")
            logger.warning("Created user with default password - should be changed immediately")

        return data


class ArticleAdmin(ModelView, model=Article):
    """Admin view for Article model.

    Provides content management with the following features:
    - Title searchable
    - Status-based filtering
    - Automatic published_at timestamp on publish
    - Category grouping with Tag admin
    """

    # Display configuration
    name = "Article"
    name_plural = "Articles"
    icon = "file-text"
    category = "Content"

    # Column configuration
    column_list = ["id", "title", "status", "author_id", "created_at", "published_at"]
    column_searchable_list = ["title", "content"]
    column_sortable_list = ["id", "title", "status", "created_at", "published_at"]
    column_default_sort = ("created_at", "desc")

    # Form configuration
    form_excluded_columns = ["tags"]  # Many-to-many handled separately

    # Permission controls
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    can_export = True

    # Pagination
    page_size = 25
    page_size_options = [10, 25, 50, 100]

    @classmethod
    async def on_model_change(
        cls,
        data: dict[str, Any],
        record: Any | None,
        *,
        is_create: bool,
    ) -> dict[str, Any]:
        """Handle article creation/update with automatic published_at.

        Sets published_at timestamp when status changes to PUBLISHED.

        Args:
            data: The data being saved.
            record: The existing record (None for create).
            is_create: Whether this is a create operation.

        Returns:
            The modified data to save.
        """
        new_status = data.get("status")

        # Check if status is being changed to PUBLISHED
        if new_status == ArticleStatus.PUBLISHED or new_status == ArticleStatus.PUBLISHED.value:
            # Only set published_at if it's not already set
            was_published = False
            if record is not None:
                was_published = record.status == ArticleStatus.PUBLISHED

            if not was_published and "published_at" not in data:
                data["published_at"] = datetime.now(timezone.utc)
                logger.info("Article published, setting published_at timestamp")

        # Clear published_at if changing away from PUBLISHED
        elif record is not None and record.status == ArticleStatus.PUBLISHED:
            if new_status and new_status != ArticleStatus.PUBLISHED and new_status != ArticleStatus.PUBLISHED.value:
                data["published_at"] = None
                logger.info("Article unpublished, clearing published_at timestamp")

        return data

    @classmethod
    async def after_model_change(
        cls,
        record: Any,
        *,
        is_create: bool,
    ) -> None:
        """Hook called after article creation/update.

        Args:
            record: The saved article record.
            is_create: Whether this was a create operation.
        """
        action = "created" if is_create else "updated"
        # Handle status being either an enum or a string
        status_value = record.status.value if hasattr(record.status, "value") else record.status
        logger.info("Article %s: %s (id=%d, status=%s)", action, record.title, record.id, status_value)


class TagAdmin(ModelView, model=Tag):
    """Admin view for Tag model.

    Provides tag management with the following features:
    - Name searchable
    - Slug auto-generation support
    - Grouped with Article admin under Content
    """

    # Display configuration
    name = "Tag"
    name_plural = "Tags"
    icon = "tag"
    category = "Content"

    # Column configuration
    column_list = ["id", "name", "slug"]
    column_searchable_list = ["name", "slug"]
    column_sortable_list = ["id", "name", "slug"]
    column_default_sort = ("name", "asc")

    # Form configuration
    form_excluded_columns = ["articles"]  # Many-to-many handled separately

    # Permission controls
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    can_export = True

    # Pagination
    page_size = 50
    page_size_options = [25, 50, 100, 200]

    @classmethod
    async def on_model_change(
        cls,
        data: dict[str, Any],
        record: Any | None,
        *,
        is_create: bool,
    ) -> dict[str, Any]:
        """Handle tag creation/update with slug auto-generation.

        Generates a URL-friendly slug from the name if not provided.

        Args:
            data: The data being saved.
            record: The existing record (None for create).
            is_create: Whether this is a create operation.

        Returns:
            The modified data to save.
        """
        import re

        # Auto-generate slug from name if not provided
        if "name" in data and (is_create or "slug" not in data or not data.get("slug")):
            name = data["name"]
            # Convert to lowercase, replace spaces with hyphens, remove special chars
            slug = name.lower().strip()
            slug = re.sub(r"[^\w\s-]", "", slug)
            slug = re.sub(r"[-\s]+", "-", slug)
            data["slug"] = slug
            logger.debug("Auto-generated slug for tag: %s -> %s", name, slug)

        return data


# =============================================================================
# CustomView Examples
# =============================================================================
# The following views demonstrate using CustomView with data providers
# for non-model data sources.


class AppSettingsAdmin(InMemoryView):
    """In-memory application settings store.

    Demonstrates using InMemoryView for a key-value settings store.
    Settings are stored in memory and persist for the application lifetime.

    This is useful for:
    - Runtime configuration that doesn't need database persistence
    - Feature flags and toggles
    - Cached settings from external sources
    """

    # Display configuration
    name = "App Settings"
    name_plural = "App Settings"
    identity = "app-settings"
    icon = "settings"
    category = "System"

    # Primary key configuration
    pk_field = "key"
    auto_generate_pk = False  # We use the key as the identifier

    # Columns
    columns: ClassVar[list[ColumnDefinition]] = [
        ColumnDefinition(name="key", label="Setting Key", type="string", sortable=True, searchable=True),
        ColumnDefinition(name="value", label="Value", type="string", searchable=True),
        ColumnDefinition(name="type", label="Type", type="string", filterable=True),
        ColumnDefinition(name="description", label="Description", type="text"),
    ]

    # Enable full CRUD
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    can_export = True

    # Pre-populate with default settings
    _data: ClassVar[dict[str, dict[str, Any]]] = {
        "site_name": {
            "key": "site_name",
            "value": "Litestar Admin Demo",
            "type": "string",
            "description": "The application name displayed in the header",
        },
        "maintenance_mode": {
            "key": "maintenance_mode",
            "value": "false",
            "type": "boolean",
            "description": "Enable maintenance mode to block user access",
        },
        "max_upload_size": {
            "key": "max_upload_size",
            "value": "10485760",
            "type": "integer",
            "description": "Maximum file upload size in bytes (default: 10MB)",
        },
        "allowed_origins": {
            "key": "allowed_origins",
            "value": "http://localhost:3000,http://localhost:8000",
            "type": "list",
            "description": "Comma-separated list of allowed CORS origins",
        },
        "feature_dark_mode": {
            "key": "feature_dark_mode",
            "value": "true",
            "type": "boolean",
            "description": "Enable dark mode toggle in the UI",
        },
        "cache_ttl": {
            "key": "cache_ttl",
            "value": "3600",
            "type": "integer",
            "description": "Default cache TTL in seconds",
        },
    }

    async def on_after_update(self, item: dict[str, Any]) -> None:
        """Log setting changes for audit purposes.

        Args:
            item: The updated item data.
        """
        logger.info("Setting updated: %s = %s", item.get("key"), item.get("value"))


class SystemInfoAdmin(InMemoryView):
    """Read-only system information view.

    Demonstrates using InMemoryView for displaying dynamic system information
    without database persistence. Data is refreshed on each request.

    This is useful for:
    - Displaying runtime environment information
    - Monitoring dashboards
    - Debug information panels
    """

    # Display configuration
    name = "System Info"
    name_plural = "System Information"
    identity = "system-info"
    icon = "cpu"
    category = "System"

    # Primary key configuration
    pk_field = "name"

    # Columns
    columns: ClassVar[list[ColumnDefinition]] = [
        ColumnDefinition(name="name", label="Property", type="string", sortable=True, searchable=True),
        ColumnDefinition(name="value", label="Value", type="string"),
        ColumnDefinition(name="category", label="Category", type="string", filterable=True),
    ]

    # Read-only view
    can_create = False
    can_edit = False
    can_delete = False
    can_view_details = True
    can_export = True

    # Override to provide dynamic data
    async def get_list(
        self,
        page: int = 1,
        page_size: int = 25,
        filters: dict[str, Any] | None = None,
        sort_by: str | None = None,
        sort_order: Literal["asc", "desc"] = "asc",
        search: str | None = None,
    ) -> ListResult:
        """Get dynamic system information.

        Generates fresh system information on each request rather than
        using static stored data.

        Args:
            page: Page number (1-indexed).
            page_size: Number of items per page.
            filters: Dictionary of filter field names to values.
            sort_by: Field name to sort by.
            sort_order: Sort direction ("asc" or "desc").
            search: Search query string.

        Returns:
            ListResult containing system info items.
        """
        # Build system info dynamically
        items = self._get_system_info()

        # Apply search filter
        if search:
            search_lower = search.lower()
            items = [
                item
                for item in items
                if search_lower in item["name"].lower() or search_lower in str(item["value"]).lower()
            ]

        # Apply filters
        if filters:
            for field, value in filters.items():
                items = [item for item in items if item.get(field) == value]

        # Sort items
        if sort_by:
            reverse = sort_order == "desc"
            items = sorted(
                items,
                key=lambda x: (x.get(sort_by) is None, x.get(sort_by, "")),
                reverse=reverse,
            )

        # Calculate pagination
        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_items = items[start:end]

        return ListResult(
            items=paginated_items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_one(self, item_id: str) -> dict[str, Any] | None:
        """Get a single system info item by name.

        Args:
            item_id: The property name.

        Returns:
            The system info item or None.
        """
        items = self._get_system_info()
        for item in items:
            if item["name"] == item_id:
                return item
        return None

    @staticmethod
    def _get_system_info() -> list[dict[str, Any]]:
        """Generate current system information.

        Returns:
            List of system info dictionaries.
        """
        import os
        from pathlib import Path

        try:
            import psutil

            has_psutil = True
        except ImportError:
            has_psutil = False

        info: list[dict[str, Any]] = [
            # Python info
            {"name": "python_version", "value": sys.version.split()[0], "category": "Python"},
            {"name": "python_implementation", "value": platform.python_implementation(), "category": "Python"},
            {"name": "python_path", "value": sys.executable, "category": "Python"},
            # Platform info
            {"name": "platform", "value": platform.platform(), "category": "Platform"},
            {"name": "system", "value": platform.system(), "category": "Platform"},
            {"name": "release", "value": platform.release(), "category": "Platform"},
            {"name": "machine", "value": platform.machine(), "category": "Platform"},
            {"name": "processor", "value": platform.processor() or "Unknown", "category": "Platform"},
            # Process info
            {"name": "pid", "value": str(os.getpid()), "category": "Process"},
            {"name": "cwd", "value": str(Path.cwd()), "category": "Process"},
            # Timestamp
            {"name": "server_time", "value": datetime.now(timezone.utc).isoformat(), "category": "Runtime"},
        ]

        # Add memory info if psutil is available
        if has_psutil:
            memory = psutil.virtual_memory()
            process = psutil.Process()
            info.extend(
                [
                    {
                        "name": "memory_total",
                        "value": f"{memory.total / (1024**3):.2f} GB",
                        "category": "Memory",
                    },
                    {
                        "name": "memory_available",
                        "value": f"{memory.available / (1024**3):.2f} GB",
                        "category": "Memory",
                    },
                    {
                        "name": "memory_percent",
                        "value": f"{memory.percent}%",
                        "category": "Memory",
                    },
                    {
                        "name": "process_memory",
                        "value": f"{process.memory_info().rss / (1024**2):.2f} MB",
                        "category": "Process",
                    },
                    {
                        "name": "cpu_count",
                        "value": str(psutil.cpu_count()),
                        "category": "CPU",
                    },
                    {
                        "name": "cpu_percent",
                        "value": f"{psutil.cpu_percent(interval=0.1)}%",
                        "category": "CPU",
                    },
                ]
            )

        return info


# =============================================================================
# ActionView Examples
# =============================================================================
# ActionViews are for one-off operations that don't map to model CRUD.


class ClearCacheAction(ActionView):
    """Simulated cache clear action with confirmation.

    Demonstrates using ActionView for maintenance operations with:
    - Confirmation dialog before execution
    - Form fields for configuration options
    - Dangerous action styling (red button)
    """

    name = "Clear Cache"
    icon = "trash-2"
    category = "Maintenance"

    # Confirmation settings
    confirmation_message = "Are you sure you want to clear the cache? This action cannot be undone."
    requires_confirmation = True
    dangerous = True

    # Form configuration
    form_fields: ClassVar[list[FormField]] = [
        FormField(
            name="cache_type",
            label="Cache Type",
            field_type="select",
            required=True,
            default="all",
            help_text="Select which cache to clear",
            options=[
                {"value": "all", "label": "All Caches"},
                {"value": "user", "label": "User Cache Only"},
                {"value": "session", "label": "Session Cache Only"},
                {"value": "query", "label": "Query Cache Only"},
            ],
        ),
        FormField(
            name="force",
            label="Force clear (ignore active sessions)",
            field_type="checkbox",
            required=False,
            default=False,
            help_text="Check to force clear even if there are active sessions",
        ),
    ]

    async def execute(self, data: dict[str, Any]) -> ActionResult:
        """Execute the cache clear operation.

        Args:
            data: Form field values from the user.

        Returns:
            ActionResult indicating success or failure.
        """
        import asyncio
        import random

        cache_type = data.get("cache_type", "all")
        force = data.get("force", False)

        # Simulate cache clearing operation
        await asyncio.sleep(0.5)  # Simulate work

        # Simulate random cache entry counts
        cleared_entries = random.randint(100, 5000)  # noqa: S311

        logger.info(
            "Cache cleared: type=%s, force=%s, entries=%d",
            cache_type,
            force,
            cleared_entries,
        )

        return ActionResult(
            success=True,
            message=f"Successfully cleared {cleared_entries} entries from {cache_type} cache.",
            data={
                "cache_type": cache_type,
                "cleared_entries": cleared_entries,
                "forced": force,
            },
            refresh=True,
        )


class SendNotificationAction(ActionView):
    """Send notification to users action.

    Demonstrates using ActionView for user-facing operations with:
    - Multiple form field types
    - Textarea for message content
    - Select for recipient groups
    - No dangerous styling (normal button)
    """

    name = "Send Notification"
    icon = "bell"
    category = "Communication"

    # Confirmation settings
    confirmation_message = "Send this notification to the selected recipients?"
    requires_confirmation = True
    dangerous = False

    submit_label = "Send Notification"

    # Form configuration
    form_fields: ClassVar[list[FormField]] = [
        FormField(
            name="recipients",
            label="Recipients",
            field_type="select",
            required=True,
            default="all",
            help_text="Select who should receive this notification",
            options=[
                {"value": "all", "label": "All Users"},
                {"value": "admins", "label": "Administrators Only"},
                {"value": "editors", "label": "Editors Only"},
                {"value": "active", "label": "Active Users Only"},
            ],
        ),
        FormField(
            name="subject",
            label="Subject",
            field_type="text",
            required=True,
            placeholder="Enter notification subject...",
            help_text="Brief subject line for the notification",
            validation={"minLength": 5, "maxLength": 100},
        ),
        FormField(
            name="message",
            label="Message",
            field_type="textarea",
            required=True,
            placeholder="Enter your notification message...",
            help_text="The full notification message to send",
            validation={"minLength": 10, "maxLength": 1000},
        ),
        FormField(
            name="priority",
            label="Priority",
            field_type="radio",
            required=True,
            default="normal",
            options=[
                {"value": "low", "label": "Low"},
                {"value": "normal", "label": "Normal"},
                {"value": "high", "label": "High"},
                {"value": "urgent", "label": "Urgent"},
            ],
        ),
        FormField(
            name="send_email",
            label="Also send via email",
            field_type="checkbox",
            required=False,
            default=False,
            help_text="Send an email copy in addition to in-app notification",
        ),
    ]

    async def execute(self, data: dict[str, Any]) -> ActionResult:
        """Execute the notification send operation.

        Args:
            data: Form field values from the user.

        Returns:
            ActionResult indicating success or failure.
        """
        import asyncio
        import random

        recipients = data.get("recipients", "all")
        subject = data.get("subject", "")
        message = data.get("message", "")
        priority = data.get("priority", "normal")
        send_email = data.get("send_email", False)

        # Simulate sending notifications
        await asyncio.sleep(0.3)

        # Simulate recipient counts based on selection
        recipient_counts = {
            "all": random.randint(50, 200),  # noqa: S311
            "admins": random.randint(2, 10),  # noqa: S311
            "editors": random.randint(5, 25),  # noqa: S311
            "active": random.randint(20, 100),  # noqa: S311
        }
        sent_count = recipient_counts.get(recipients, 0)

        logger.info(
            "Notification sent: recipients=%s, subject=%s, message_length=%d, priority=%s, email=%s, count=%d",
            recipients,
            subject,
            len(message),
            priority,
            send_email,
            sent_count,
        )

        email_note = " (email copies also sent)" if send_email else ""

        return ActionResult(
            success=True,
            message=f"Notification sent to {sent_count} {recipients} users{email_note}.",
            data={
                "recipients": recipients,
                "sent_count": sent_count,
                "priority": priority,
                "email_sent": send_email,
            },
        )


# =============================================================================
# PageView Examples
# =============================================================================
# PageViews are for static or dynamic content pages in the admin.


class AboutPage(PageView):
    """Static markdown about page.

    Demonstrates using PageView for static content with:
    - Markdown content rendering
    - Full-width layout
    - No dynamic data loading
    """

    name = "About"
    icon = "info"
    category = "Help"

    content_type = "markdown"
    layout = "full-width"

    content: ClassVar[str] = """
# About Litestar Admin Demo

This is a full-featured demonstration of **litestar-admin**, a modern admin panel
framework for Litestar applications.

## Features Demonstrated

### Model Views
- **User Management**: Full CRUD with password hashing and role assignment
- **Article Management**: Content workflow with draft/review/published states
- **Tag Management**: Simple tag CRUD with slug auto-generation

### Custom Views
- **App Settings**: In-memory key-value store for runtime configuration
- **System Info**: Dynamic system information display

### Action Views
- **Clear Cache**: Maintenance action with confirmation dialog
- **Send Notification**: User communication with form validation

### Page Views
- **About Page**: This static markdown page
- **Changelog**: Dynamic content loading

### Link Views
- External links to documentation and GitHub

### Embed Views
- Placeholder for embedded dashboards and metrics

## Authentication

This demo supports multiple authentication modes:
- **JWT Authentication**: Username/password login (default)
- **GitHub OAuth**: Login via GitHub account
- **Demo OAuth**: Simulated OAuth for testing

## Getting Started

1. Run the application:
   ```bash
   litestar --app examples.full.app:app run --reload
   ```

2. Login with default credentials:
   - Email: `admin@example.com`
   - Password: `admin`

---

*Built with [Litestar](https://litestar.dev) and [litestar-admin](https://github.com/litestar-org/litestar-admin)*
"""


class ChangelogPage(PageView):
    """Dynamic changelog page.

    Demonstrates using PageView for dynamic content with:
    - Dynamic content loading via get_content()
    - Auto-refresh capability
    - Default layout
    """

    name = "Changelog"
    icon = "clock"
    category = "Help"

    content_type = "dynamic"  # Fetches content via get_content()
    layout = "default"
    refresh_interval = 300  # Refresh every 5 minutes

    async def get_content(self) -> dict[str, Any]:
        """Get dynamic changelog content.

        In a real application, this might fetch from a database,
        GitHub releases API, or a changelog file.

        Returns:
            Dictionary with changelog data for the frontend.
        """
        # Simulated changelog entries
        changelog_entries = [
            {
                "version": "0.5.0",
                "date": "2024-01-15",
                "type": "feature",
                "title": "ActionView Support",
                "description": "Added ActionView for one-off admin operations with form inputs.",
                "changes": [
                    "New ActionView base class with form field support",
                    "Confirmation dialogs for dangerous actions",
                    "Background execution support for long-running actions",
                ],
            },
            {
                "version": "0.4.0",
                "date": "2024-01-10",
                "type": "feature",
                "title": "PageView and LinkView",
                "description": "Added PageView for custom content pages and LinkView for navigation.",
                "changes": [
                    "PageView with markdown, HTML, and dynamic content support",
                    "LinkView for external navigation links",
                    "Category grouping for sidebar organization",
                ],
            },
            {
                "version": "0.3.0",
                "date": "2024-01-05",
                "type": "enhancement",
                "title": "CustomView Improvements",
                "description": "Enhanced CustomView with InMemoryView provider.",
                "changes": [
                    "InMemoryView for non-database data sources",
                    "Dynamic system info display",
                    "Settings management without database",
                ],
            },
            {
                "version": "0.2.0",
                "date": "2023-12-20",
                "type": "feature",
                "title": "OAuth Authentication",
                "description": "Added OAuth authentication support with GitHub provider.",
                "changes": [
                    "GitHub OAuth authentication backend",
                    "Demo OAuth mode for testing",
                    "Automatic user creation on first login",
                ],
            },
            {
                "version": "0.1.0",
                "date": "2023-12-01",
                "type": "release",
                "title": "Initial Release",
                "description": "First release of litestar-admin with core functionality.",
                "changes": [
                    "ModelView for SQLAlchemy models",
                    "JWT authentication",
                    "Dark theme Cloudflare-inspired UI",
                    "Rate limiting",
                ],
            },
        ]

        # Build markdown content from changelog entries
        lines = ["# Litestar Admin Changelog\n"]
        for entry in changelog_entries:
            type_badge = f"**[{entry['type'].upper()}]**"
            lines.append(f"\n## {entry['version']} - {entry['date']} {type_badge}\n")
            lines.append(f"\n### {entry['title']}\n")
            lines.append(f"\n{entry['description']}\n")
            if entry.get("changes"):
                lines.append("\n**Changes:**\n")
                for change in entry["changes"]:
                    lines.append(f"- {change}\n")

        content_str = "".join(lines)

        return {
            "content": content_str,
            "title": "Litestar Admin Changelog",
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }


# =============================================================================
# LinkView Examples
# =============================================================================
# LinkViews are for external navigation links in the sidebar.


class DocsLink(LinkView):
    """Link to documentation.

    Demonstrates using LinkView for external documentation links with:
    - External URL opening in new tab
    - Category grouping
    """

    name = "Documentation"
    icon = "book-open"
    category = "Resources"

    url = "https://litestar.dev/latest"
    target = "_blank"


class GitHubLink(LinkView):
    """Link to GitHub repository.

    Demonstrates using LinkView for repository links with:
    - External URL opening in new tab
    - Same category as docs for grouping
    """

    name = "GitHub"
    icon = "github"
    category = "Resources"

    url = "https://github.com/litestar-org/litestar-admin"
    target = "_blank"


# =============================================================================
# EmbedView Examples
# =============================================================================
# EmbedViews are for embedding external content or custom components.


class MetricsEmbed(EmbedView):
    """Placeholder metrics dashboard embed.

    Demonstrates using EmbedView for embedded dashboards with:
    - Iframe embedding of external URL
    - Custom dimensions
    - Security sandbox configuration

    Note: This uses a placeholder URL. In production, replace with
    an actual metrics dashboard URL (Grafana, Metabase, etc.).
    """

    name = "Metrics Dashboard"
    icon = "bar-chart-2"
    category = "Monitoring"

    embed_type = "iframe"
    # Placeholder URL - in production this would be a real dashboard
    embed_url = "about:blank"  # Replace with actual dashboard URL

    # Dimensions
    height = "600px"
    min_height = "400px"
    layout = "full"

    # Security settings
    sandbox = "allow-scripts allow-same-origin"
    show_toolbar = True
    refresh_interval = 60  # Auto-refresh every minute
