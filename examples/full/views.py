"""ModelView configurations for the full admin demo.

This module defines the admin views for all models in the demo application,
showcasing various configuration options including:
- Column display and search configuration
- Form customization
- Permission controls
- Category grouping
- Custom model change hooks

Views:
    - UserAdmin: User management with restricted delete
    - ArticleAdmin: Content management with status workflow
    - TagAdmin: Tag management with slug handling
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from examples.full.models import Article, ArticleStatus, Tag, User
from litestar_admin import ModelView

__all__ = ["ArticleAdmin", "TagAdmin", "UserAdmin"]

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
