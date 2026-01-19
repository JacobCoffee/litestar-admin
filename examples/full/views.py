"""ModelView configurations for the full admin demo.

This module defines the admin views for all models in the demo application,
showcasing various configuration options including:
- Column display and search configuration
- Form customization
- Permission controls
- Category grouping
- Custom model change hooks
- CustomView examples with data providers

Views:
    - UserAdmin: User management with restricted delete
    - ArticleAdmin: Content management with status workflow
    - TagAdmin: Tag management with slug handling
    - AppSettingsAdmin: In-memory settings store (CustomView example)
    - SystemInfoAdmin: System information view (read-only CustomView example)
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

__all__ = ["AppSettingsAdmin", "ArticleAdmin", "SystemInfoAdmin", "TagAdmin", "UserAdmin"]

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
        logger.info("Article %s: %s (id=%d, status=%s)", action, record.title, record.id, record.status.value)


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
