"""SQLAlchemy models for admin settings storage.

This module provides database models for persistent admin settings storage,
designed for use with Advanced-Alchemy and SQLAlchemy 2.x.

Example:
    Using the AdminSettings model::

        from litestar_admin.settings.models import AdminSettings, SettingsCategory
        from sqlalchemy.ext.asyncio import AsyncSession

        async def create_setting(session: AsyncSession) -> None:
            setting = AdminSettings(
                key="site_name",
                value="My Admin Panel",
                description="The name displayed in the header",
                category=SettingsCategory.GENERAL,
            )
            session.add(setting)
            await session.commit()
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from sqlalchemy import Boolean, DateTime, Index, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON

__all__ = ["AdminSettings", "AdminSettingsBase", "SettingsCategory"]


class SettingsCategory(StrEnum):
    """Predefined settings categories.

    These categories help organize settings in the admin panel UI
    and make it easier to group related configuration options.

    Attributes:
        GENERAL: General admin panel settings.
        AUTH: Authentication and authorization settings.
        DISPLAY: UI display preferences and theme settings.
        NOTIFICATIONS: Notification and alert settings.
        SECURITY: Security-related configuration.
        ADVANCED: Advanced/experimental settings.
    """

    GENERAL = "general"
    AUTH = "auth"
    DISPLAY = "display"
    NOTIFICATIONS = "notifications"
    SECURITY = "security"
    ADVANCED = "advanced"


class AdminSettingsBase(DeclarativeBase):
    """Base class for admin settings models.

    Use this as the base for the AdminSettings model if you need a separate
    metadata/base from your main application models.
    """



class AdminSettings(AdminSettingsBase):
    """SQLAlchemy model for storing admin panel settings.

    This model stores configuration settings as key-value pairs with JSON
    value support, allowing for complex configuration objects.

    Attributes:
        key: Unique identifier for the setting (primary key).
        value: The setting value, stored as JSON (supports dict, list, str, int, bool, None).
        description: Optional human-readable description of the setting.
        category: Category for grouping settings (default: "general").
        is_sensitive: Whether the value should be hidden in the UI (e.g., API keys).
        created_at: When the setting was first created (UTC).
        updated_at: When the setting was last modified (UTC).

    Example:
        Query settings by category::

            from sqlalchemy import select

            stmt = (
                select(AdminSettings)
                .where(AdminSettings.category == SettingsCategory.DISPLAY)
                .order_by(AdminSettings.key)
            )
            result = await session.execute(stmt)
            settings = result.scalars().all()
    """

    __tablename__ = "admin_settings"

    # Primary key - the setting key
    key: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
    )

    # Value stored as JSON for flexibility
    # Supports: dict, list, str, int, float, bool, None
    value: Mapped[dict[str, Any] | list[Any] | str | int | float | bool | None] = mapped_column(
        JSON,
        nullable=True,
    )

    # Human-readable description
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Category for grouping settings
    category: Mapped[str] = mapped_column(
        String(100),
        default=SettingsCategory.GENERAL,
        index=True,
    )

    # Whether the value should be masked in the UI (e.g., passwords, API keys)
    is_sensitive: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=timezone.utc),
        onupdate=lambda: datetime.now(tz=timezone.utc),
        nullable=False,
    )

    # Indexes for common queries
    __table_args__ = (
        Index("ix_admin_settings_category_key", "category", "key"),
    )

    def __repr__(self) -> str:
        """Return string representation of the setting."""
        value_display = "***" if self.is_sensitive else repr(self.value)
        return f"<AdminSettings(key={self.key!r}, value={value_display}, category={self.category!r})>"

    def to_dict(self, *, include_sensitive: bool = False) -> dict[str, Any]:
        """Convert the setting to a dictionary.

        Args:
            include_sensitive: Whether to include sensitive values.
                If False, sensitive values are masked.

        Returns:
            Dictionary representation of the setting.
        """
        return {
            "key": self.key,
            "value": self.value if (include_sensitive or not self.is_sensitive) else "***",
            "description": self.description,
            "category": self.category,
            "is_sensitive": self.is_sensitive,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
