"""SettingsController for admin settings management.

This module provides REST API endpoints for managing admin panel settings,
including CRUD operations and bulk updates.

Example:
    The controller is automatically registered by AdminPlugin.
    Access endpoints at:
    - GET /admin/api/settings - List all settings
    - GET /admin/api/settings/{key} - Get a single setting
    - POST /admin/api/settings - Create a new setting
    - PUT /admin/api/settings/{key} - Update a setting
    - DELETE /admin/api/settings/{key} - Delete a setting
    - PUT /admin/api/settings/bulk - Bulk update settings
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from litestar import Controller, delete, get, post, put
from litestar.exceptions import NotFoundException
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT

# Litestar requires these imports at runtime for dependency injection type resolution
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from litestar_admin.settings.models import SettingsCategory
from litestar_admin.settings.service import SettingsService

__all__ = [
    "BulkSettingsRequest",
    "CreateSettingRequest",
    "SettingResponse",
    "SettingsController",
    "SettingsListResponse",
    "UpdateSettingRequest",
]


@dataclass
class SettingResponse:
    """Response for a single setting.

    Attributes:
        key: The setting key.
        value: The setting value (JSON-serializable).
        description: Optional description of the setting.
        category: The setting category.
        is_sensitive: Whether the value is sensitive.
        created_at: ISO format timestamp of creation.
        updated_at: ISO format timestamp of last update.
    """

    key: str
    value: Any
    description: str | None = None
    category: str = "general"
    is_sensitive: bool = False
    created_at: str | None = None
    updated_at: str | None = None


@dataclass
class SettingsListResponse:
    """Response for listing settings.

    Attributes:
        items: List of settings.
        total: Total number of settings.
        categories: List of available categories.
    """

    items: list[SettingResponse]
    total: int
    categories: list[str] = field(default_factory=list)


@dataclass
class CreateSettingRequest:
    """Request to create a new setting.

    Attributes:
        key: The setting key (required).
        value: The setting value (JSON-serializable).
        description: Optional description.
        category: Category for the setting.
        is_sensitive: Whether to mask the value in the UI.
    """

    key: str
    value: Any
    description: str | None = None
    category: str = "general"
    is_sensitive: bool = False


@dataclass
class UpdateSettingRequest:
    """Request to update an existing setting.

    Attributes:
        value: The new value (JSON-serializable).
        description: Optional new description.
    """

    value: Any
    description: str | None = None


@dataclass
class BulkSettingsRequest:
    """Request to bulk update settings.

    Attributes:
        settings: Dictionary mapping keys to values.
        category: Default category for new settings.
    """

    settings: dict[str, Any]
    category: str = "general"


class SettingsController(Controller):
    """Controller for admin settings management.

    Provides REST API endpoints for managing admin panel settings.
    Settings are stored as key-value pairs with JSON value support.

    All endpoints require proper authentication and authorization when
    configured via guards.

    Example:
        The controller is automatically registered by AdminPlugin.
        Access endpoints at:
        - GET /admin/api/settings - List all settings
        - GET /admin/api/settings/categories - List all categories
        - GET /admin/api/settings/{key} - Get a single setting
        - POST /admin/api/settings - Create a new setting
        - PUT /admin/api/settings/{key} - Update a setting
        - DELETE /admin/api/settings/{key} - Delete a setting
        - PUT /admin/api/settings/bulk - Bulk update settings
    """

    path = "/api/settings"
    tags: ClassVar[list[str]] = ["Settings"]

    @get(
        "/",
        status_code=HTTP_200_OK,
        summary="List all settings",
        description="Returns all settings, optionally filtered by category.",
    )
    async def list_settings(
        self,
        db_session: AsyncSession,
        category: str | None = None,
    ) -> SettingsListResponse:
        """List all settings with optional category filter.

        Args:
            db_session: The database session.
            category: Optional category to filter by.

        Returns:
            List of settings with metadata.
        """
        service = SettingsService(db_session)

        settings = await service.get_all_settings(category=category)
        categories = await service.get_categories()

        return SettingsListResponse(
            items=[
                SettingResponse(
                    key=s.key,
                    value=s.value if not s.is_sensitive else "***",
                    description=s.description,
                    category=s.category,
                    is_sensitive=s.is_sensitive,
                    created_at=s.created_at.isoformat() if s.created_at else None,
                    updated_at=s.updated_at.isoformat() if s.updated_at else None,
                )
                for s in settings
            ],
            total=len(settings),
            categories=categories,
        )

    @get(
        "/categories",
        status_code=HTTP_200_OK,
        summary="List all categories",
        description="Returns all available setting categories.",
    )
    async def list_categories(
        self,
        db_session: AsyncSession,
    ) -> dict[str, Any]:
        """List all available categories.

        Returns both predefined categories and any custom categories
        that have been used.

        Args:
            db_session: The database session.

        Returns:
            Dictionary with predefined and used categories.
        """
        service = SettingsService(db_session)
        used_categories = await service.get_categories()

        # Include all predefined categories
        predefined = [c.value for c in SettingsCategory]

        return {
            "predefined": predefined,
            "used": used_categories,
            "all": sorted(set(predefined + used_categories)),
        }

    @get(
        "/{key:str}",
        status_code=HTTP_200_OK,
        summary="Get a single setting",
        description="Returns a single setting by its key.",
    )
    async def get_setting(
        self,
        key: str,
        db_session: AsyncSession,
    ) -> SettingResponse:
        """Get a single setting by key.

        Args:
            key: The setting key.
            db_session: The database session.

        Returns:
            The setting with metadata.

        Raises:
            NotFoundException: If the setting doesn't exist.
        """
        service = SettingsService(db_session)
        setting = await service.get_setting(key)

        if setting is None:
            raise NotFoundException(f"Setting '{key}' not found")

        return SettingResponse(
            key=setting.key,
            value=setting.value if not setting.is_sensitive else "***",
            description=setting.description,
            category=setting.category,
            is_sensitive=setting.is_sensitive,
            created_at=setting.created_at.isoformat() if setting.created_at else None,
            updated_at=setting.updated_at.isoformat() if setting.updated_at else None,
        )

    @post(
        "/",
        status_code=HTTP_201_CREATED,
        summary="Create a new setting",
        description="Creates a new setting with the provided key and value.",
    )
    async def create_setting(
        self,
        data: CreateSettingRequest,
        db_session: AsyncSession,
    ) -> SettingResponse:
        """Create a new setting.

        Args:
            data: The setting data.
            db_session: The database session.

        Returns:
            The created setting.
        """
        service = SettingsService(db_session)

        setting = await service.set(
            key=data.key,
            value=data.value,
            description=data.description,
            category=data.category,
            is_sensitive=data.is_sensitive,
        )
        await db_session.commit()

        return SettingResponse(
            key=setting.key,
            value=setting.value if not setting.is_sensitive else "***",
            description=setting.description,
            category=setting.category,
            is_sensitive=setting.is_sensitive,
            created_at=setting.created_at.isoformat() if setting.created_at else None,
            updated_at=setting.updated_at.isoformat() if setting.updated_at else None,
        )

    @put(
        "/{key:str}",
        status_code=HTTP_200_OK,
        summary="Update a setting",
        description="Updates an existing setting's value.",
    )
    async def update_setting(
        self,
        key: str,
        data: UpdateSettingRequest,
        db_session: AsyncSession,
    ) -> SettingResponse:
        """Update an existing setting.

        Args:
            key: The setting key.
            data: The update data.
            db_session: The database session.

        Returns:
            The updated setting.

        Raises:
            NotFoundException: If the setting doesn't exist.
        """
        service = SettingsService(db_session)

        # Check if setting exists
        existing = await service.get_setting(key)
        if existing is None:
            raise NotFoundException(f"Setting '{key}' not found")

        # Update the setting
        setting = await service.set(
            key=key,
            value=data.value,
            description=data.description,
            category=existing.category,  # Keep existing category
            is_sensitive=existing.is_sensitive,  # Keep existing sensitivity
        )
        await db_session.commit()

        return SettingResponse(
            key=setting.key,
            value=setting.value if not setting.is_sensitive else "***",
            description=setting.description,
            category=setting.category,
            is_sensitive=setting.is_sensitive,
            created_at=setting.created_at.isoformat() if setting.created_at else None,
            updated_at=setting.updated_at.isoformat() if setting.updated_at else None,
        )

    @delete(
        "/{key:str}",
        status_code=HTTP_204_NO_CONTENT,
        summary="Delete a setting",
        description="Deletes a setting by its key.",
    )
    async def delete_setting(
        self,
        key: str,
        db_session: AsyncSession,
    ) -> None:
        """Delete a setting by key.

        Args:
            key: The setting key.
            db_session: The database session.

        Raises:
            NotFoundException: If the setting doesn't exist.
        """
        service = SettingsService(db_session)

        deleted = await service.delete(key)
        if not deleted:
            raise NotFoundException(f"Setting '{key}' not found")

        await db_session.commit()

    @put(
        "/bulk",
        status_code=HTTP_200_OK,
        summary="Bulk update settings",
        description="Creates or updates multiple settings at once.",
    )
    async def bulk_update_settings(
        self,
        data: BulkSettingsRequest,
        db_session: AsyncSession,
    ) -> SettingsListResponse:
        """Bulk update multiple settings.

        Creates or updates multiple settings in a single request.
        Existing settings keep their category and sensitivity.

        Args:
            data: The bulk update data.
            db_session: The database session.

        Returns:
            List of created/updated settings.
        """
        service = SettingsService(db_session)

        settings = await service.bulk_update(
            settings=data.settings,
            category=data.category,
        )
        await db_session.commit()

        categories = await service.get_categories()

        return SettingsListResponse(
            items=[
                SettingResponse(
                    key=s.key,
                    value=s.value if not s.is_sensitive else "***",
                    description=s.description,
                    category=s.category,
                    is_sensitive=s.is_sensitive,
                    created_at=s.created_at.isoformat() if s.created_at else None,
                    updated_at=s.updated_at.isoformat() if s.updated_at else None,
                )
                for s in settings
            ],
            total=len(settings),
            categories=categories,
        )
