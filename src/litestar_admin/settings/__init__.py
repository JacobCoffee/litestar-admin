"""Admin settings storage system.

This module provides a persistent settings storage system for the admin panel,
allowing runtime configuration of admin features through a key-value store
with JSON value support.

Components:
    - AdminSettings: SQLAlchemy model for settings storage
    - AdminSettingsBase: Base class for the settings model
    - SettingsService: Service class for CRUD operations
    - SettingsCategory: Enum of predefined settings categories

Example:
    Basic usage with SettingsService::

        from litestar_admin.settings import SettingsService, SettingsCategory
        from sqlalchemy.ext.asyncio import AsyncSession

        async def configure_admin(session: AsyncSession) -> None:
            service = SettingsService(session)

            # Set a setting
            await service.set(
                key="site_name",
                value="My Admin Panel",
                description="The name displayed in the header",
                category=SettingsCategory.GENERAL,
            )

            # Get a setting with default
            name = await service.get("site_name", default="Admin")

            # Get all settings in a category
            auth_settings = await service.get_by_category(SettingsCategory.AUTH)

    Using the settings model directly::

        from litestar_admin.settings import AdminSettings

        setting = AdminSettings(
            key="theme",
            value="dark",
            category="display",
        )
        session.add(setting)
        await session.commit()
"""

from __future__ import annotations

from litestar_admin.settings.models import AdminSettings, AdminSettingsBase, SettingsCategory
from litestar_admin.settings.service import SettingsService

__all__ = [
    # Models
    "AdminSettings",
    "AdminSettingsBase",
    # Service
    "SettingsService",
    # Enums
    "SettingsCategory",
]
