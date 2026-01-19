"""Service layer for admin settings operations.

This module provides a service class for CRUD operations on admin settings,
abstracting the database operations and providing a clean API for settings
management.

Example:
    Using SettingsService::

        from litestar_admin.settings import SettingsService, SettingsCategory
        from sqlalchemy.ext.asyncio import AsyncSession

        async def configure_settings(session: AsyncSession) -> None:
            service = SettingsService(session)

            # Set multiple settings at once
            await service.bulk_update({
                "site_name": "My Admin",
                "items_per_page": 25,
                "enable_dark_mode": True,
            })

            # Get a setting with a default value
            items = await service.get("items_per_page", default=10)

            # Get all display settings
            display_settings = await service.get_by_category(SettingsCategory.DISPLAY)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import delete, select

from litestar_admin.settings.models import AdminSettings, SettingsCategory

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

__all__ = ["SettingsService"]


class SettingsService:
    """Service class for admin settings CRUD operations.

    Provides a clean API for managing admin settings, including getting,
    setting, updating, and deleting settings. Supports bulk operations
    and category-based filtering.

    The session is managed externally - the caller is responsible for
    committing transactions when appropriate.

    Attributes:
        session: The SQLAlchemy async session for database operations.

    Example:
        Using with Litestar dependency injection::

            from litestar import get
            from sqlalchemy.ext.asyncio import AsyncSession

            @get("/settings/{key}")
            async def get_setting(key: str, db_session: AsyncSession) -> dict:
                service = SettingsService(db_session)
                value = await service.get(key)
                return {"key": key, "value": value}
    """

    __slots__ = ("_session",)

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the settings service.

        Args:
            session: An async SQLAlchemy session for database operations.
        """
        self._session = session

    async def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value by key.

        Retrieves the value of a setting by its key. If the setting doesn't
        exist, returns the provided default value.

        Args:
            key: The setting key to retrieve.
            default: Value to return if the setting doesn't exist.

        Returns:
            The setting value, or the default if not found.

        Example:
            Get a setting with default::

                items_per_page = await service.get("items_per_page", default=10)
        """
        stmt = select(AdminSettings).where(AdminSettings.key == key)
        result = await self._session.execute(stmt)
        setting = result.scalar_one_or_none()

        if setting is None:
            return default

        return setting.value

    async def get_setting(self, key: str) -> AdminSettings | None:
        """Get a setting object by key.

        Retrieves the full AdminSettings object, including metadata like
        description, category, and timestamps.

        Args:
            key: The setting key to retrieve.

        Returns:
            The AdminSettings object, or None if not found.

        Example:
            Get setting with metadata::

                setting = await service.get_setting("site_name")
                if setting:
                    print(f"Description: {setting.description}")
        """
        stmt = select(AdminSettings).where(AdminSettings.key == key)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def set(
        self,
        key: str,
        value: Any,
        description: str | None = None,
        category: str | SettingsCategory = SettingsCategory.GENERAL,
        *,
        is_sensitive: bool = False,
    ) -> AdminSettings:
        """Set a setting value.

        Creates a new setting or updates an existing one. If the setting
        already exists, only the value and optionally description are updated.

        Args:
            key: The setting key.
            value: The value to store (JSON-serializable).
            description: Optional description of the setting.
            category: Category for the setting (default: "general").
            is_sensitive: Whether to mask the value in the UI.

        Returns:
            The created or updated AdminSettings object.

        Example:
            Set a new setting::

                setting = await service.set(
                    key="site_name",
                    value="My Admin Panel",
                    description="The name displayed in the header",
                )
        """
        # Convert enum to string if needed
        category_str = category.value if isinstance(category, SettingsCategory) else category

        # Check if setting exists
        stmt = select(AdminSettings).where(AdminSettings.key == key)
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is not None:
            # Update existing setting
            existing.value = value
            existing.updated_at = datetime.now(tz=timezone.utc)
            if description is not None:
                existing.description = description
            await self._session.flush()
            return existing

        # Create new setting
        setting = AdminSettings(
            key=key,
            value=value,
            description=description,
            category=category_str,
            is_sensitive=is_sensitive,
        )
        self._session.add(setting)
        await self._session.flush()
        return setting

    async def get_all(self, category: str | SettingsCategory | None = None) -> dict[str, Any]:
        """Get all settings as a key-value dictionary.

        Retrieves all settings, optionally filtered by category.
        Returns a simple dictionary mapping keys to values.

        Args:
            category: Optional category to filter by.

        Returns:
            Dictionary mapping setting keys to their values.

        Example:
            Get all settings::

                all_settings = await service.get_all()
                print(all_settings["site_name"])

            Get settings by category::

                display_settings = await service.get_all(category=SettingsCategory.DISPLAY)
        """
        stmt = select(AdminSettings)

        if category is not None:
            category_str = category.value if isinstance(category, SettingsCategory) else category
            stmt = stmt.where(AdminSettings.category == category_str)

        stmt = stmt.order_by(AdminSettings.key)
        result = await self._session.execute(stmt)
        settings = result.scalars().all()

        return {setting.key: setting.value for setting in settings}

    async def get_by_category(self, category: str | SettingsCategory) -> list[AdminSettings]:
        """Get all settings in a category.

        Retrieves all AdminSettings objects in a specific category,
        including all metadata.

        Args:
            category: The category to filter by.

        Returns:
            List of AdminSettings objects in the category.

        Example:
            Get all auth settings::

                auth_settings = await service.get_by_category(SettingsCategory.AUTH)
                for setting in auth_settings:
                    print(f"{setting.key}: {setting.description}")
        """
        category_str = category.value if isinstance(category, SettingsCategory) else category

        stmt = (
            select(AdminSettings)
            .where(AdminSettings.category == category_str)
            .order_by(AdminSettings.key)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_settings(
        self,
        category: str | SettingsCategory | None = None,
    ) -> list[AdminSettings]:
        """Get all settings as AdminSettings objects.

        Retrieves all settings with full metadata, optionally filtered
        by category. Each returned AdminSettings object has an `is_sensitive`
        flag that the caller can use to decide whether to mask values.

        Args:
            category: Optional category to filter by.

        Returns:
            List of AdminSettings objects.
        """
        stmt = select(AdminSettings)

        if category is not None:
            category_str = category.value if isinstance(category, SettingsCategory) else category
            stmt = stmt.where(AdminSettings.category == category_str)

        stmt = stmt.order_by(AdminSettings.category, AdminSettings.key)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, key: str) -> bool:
        """Delete a setting by key.

        Removes a setting from the database.

        Args:
            key: The setting key to delete.

        Returns:
            True if the setting was deleted, False if it didn't exist.

        Example:
            Delete a setting::

                deleted = await service.delete("old_setting")
                if deleted:
                    print("Setting removed")
        """
        stmt = delete(AdminSettings).where(AdminSettings.key == key)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount > 0

    async def bulk_update(
        self,
        settings: dict[str, Any],
        category: str | SettingsCategory = SettingsCategory.GENERAL,
    ) -> list[AdminSettings]:
        """Bulk update multiple settings at once.

        Creates or updates multiple settings in a single operation.
        All settings will be assigned to the specified category if they
        don't already exist.

        Args:
            settings: Dictionary mapping keys to values.
            category: Default category for new settings.

        Returns:
            List of created/updated AdminSettings objects.

        Example:
            Update multiple settings::

                await service.bulk_update({
                    "items_per_page": 25,
                    "enable_dark_mode": True,
                    "default_sort": "created_at",
                })
        """
        results: list[AdminSettings] = []

        for key, value in settings.items():
            setting = await self.set(key=key, value=value, category=category)
            results.append(setting)

        return results

    async def exists(self, key: str) -> bool:
        """Check if a setting exists.

        Args:
            key: The setting key to check.

        Returns:
            True if the setting exists, False otherwise.
        """
        stmt = select(AdminSettings.key).where(AdminSettings.key == key)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_categories(self) -> list[str]:
        """Get all unique categories that have settings.

        Returns:
            List of category names that have at least one setting.
        """
        from sqlalchemy import distinct

        stmt = select(distinct(AdminSettings.category)).order_by(AdminSettings.category)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
