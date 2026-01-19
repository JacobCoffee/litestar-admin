"""Dashboard controller for admin panel statistics and activity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar

from litestar import Controller, get
from litestar.status_codes import HTTP_200_OK

# Litestar requires these imports at runtime for dependency injection type resolution
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from litestar_admin.config import AdminConfig  # noqa: TC001
from litestar_admin.registry import ModelRegistry  # noqa: TC001

__all__ = [
    "ActivityEntry",
    "DashboardController",
    "DashboardStats",
    "ModelStats",
    "WidgetData",
]


@dataclass
class ModelStats:
    """Statistics for a single registered model.

    Attributes:
        name: The display name of the model.
        model_name: The underlying model class name.
        count: Total number of records in the model.
        icon: Icon identifier for the model.
        category: Category grouping for the model.
    """

    name: str
    model_name: str
    count: int
    icon: str = "table"
    category: str | None = None


@dataclass
class WidgetData:
    """Data for a custom dashboard widget.

    Attributes:
        id: Unique identifier for the widget.
        type: Widget type (e.g., "chart", "metric", "list").
        title: Display title for the widget.
        data: Widget-specific data payload.
        config: Optional configuration for widget rendering.
    """

    id: str
    type: str
    title: str
    data: dict[str, Any] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class DashboardStats:
    """Complete dashboard statistics response.

    Attributes:
        models: Statistics for each registered model.
        total_records: Sum of all records across all models.
        total_models: Number of registered models.
        widgets: List of custom widget data.
    """

    models: list[ModelStats]
    total_records: int
    total_models: int
    widgets: list[WidgetData] = field(default_factory=list)


@dataclass
class ActivityEntry:
    """A single activity log entry.

    Attributes:
        action: The action performed (create, update, delete, etc.).
        model: The model name the action was performed on.
        record_id: Identifier of the affected record.
        timestamp: When the action occurred.
        user: Username or identifier of who performed the action.
        details: Additional action-specific details.
    """

    action: str
    model: str
    record_id: str | int | None
    timestamp: datetime
    user: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


class DashboardController(Controller):
    """Controller for dashboard data and statistics.

    Provides endpoints for retrieving admin dashboard information including
    model statistics, recent activity, and custom widget data.

    Example:
        The controller is automatically registered by AdminPlugin.
        Access endpoints at:
        - GET /admin/api/dashboard/stats
        - GET /admin/api/dashboard/activity
        - GET /admin/api/dashboard/widgets
    """

    path = "/api/dashboard"
    tags: ClassVar[list[str]] = ["Dashboard"]

    @get(
        "/stats",
        status_code=HTTP_200_OK,
        summary="Get dashboard statistics",
        description="Returns statistics for all registered models including record counts.",
    )
    async def get_stats(
        self,
        admin_config: AdminConfig,
        admin_registry: ModelRegistry,
        db_session: AsyncSession | None = None,
    ) -> DashboardStats:
        """Get dashboard statistics including model counts.

        Args:
            admin_config: The admin panel configuration.
            admin_registry: The model registry containing all registered views.
            db_session: Optional database session for fetching record counts.

        Returns:
            Dashboard statistics with model information and record counts.
        """
        model_stats: list[ModelStats] = []
        total_records = 0

        for view_class in admin_registry:
            # Skip views that don't have a model (custom views, settings, etc.)
            if not hasattr(view_class, "model") or view_class.model is None:
                continue

            count = 0

            # Attempt to get record count if session is available
            if db_session is not None:
                count = await self._get_model_count(db_session, view_class.model)

            total_records += count

            model_stats.append(
                ModelStats(
                    name=view_class.name,
                    model_name=view_class.identity,  # Use identity for URL routing
                    count=count,
                    icon=view_class.icon,
                    category=view_class.category,
                )
            )

        # Get custom widgets from config extras
        widgets = self._get_custom_widgets(admin_config)

        return DashboardStats(
            models=model_stats,
            total_records=total_records,
            total_models=len(model_stats),
            widgets=widgets,
        )

    @get(
        "/activity",
        status_code=HTTP_200_OK,
        summary="Get recent activity",
        description="Returns recent admin activity from the audit log.",
    )
    async def get_activity(
        self,
        admin_config: AdminConfig,  # noqa: ARG002
        admin_registry: ModelRegistry,  # noqa: ARG002
        db_session: AsyncSession | None = None,
        limit: int = 50,
        model_name: str | None = None,
        record_id: str | None = None,
    ) -> list[ActivityEntry]:
        """Get recent activity from the audit log.

        This endpoint returns recent changes made through the admin panel.

        Args:
            admin_config: The admin panel configuration.
            admin_registry: The model registry.
            db_session: Optional database session for fetching audit logs.
            limit: Maximum number of activity entries to return.
            model_name: Optional filter by model name.
            record_id: Optional filter by record ID.

        Returns:
            List of recent activity entries, or empty list if audit logging
            is not configured or no session is available.
        """
        if db_session is None:
            return []

        try:
            from litestar_admin.audit import AuditQueryFilters
            from litestar_admin.audit.database import DatabaseAuditLogger

            logger = DatabaseAuditLogger(db_session)
            filters = AuditQueryFilters(limit=limit, model_name=model_name, record_id=record_id)
            entries = await logger.query(filters)

            return [
                ActivityEntry(
                    action=entry.action.value,
                    model=entry.model_name or "System",
                    record_id=entry.record_id,
                    timestamp=entry.timestamp,
                    user=entry.actor_email,
                    details=entry.changes or {},
                )
                for entry in entries
            ]
        except Exception:
            # Table might not exist yet or other database errors
            return []

    @get(
        "/widgets",
        status_code=HTTP_200_OK,
        summary="Get custom widgets",
        description="Returns custom dashboard widget configurations.",
    )
    async def get_widgets(
        self,
        admin_config: AdminConfig,
    ) -> list[WidgetData]:
        """Get custom dashboard widgets.

        Custom widgets can be configured via AdminConfig.extra["widgets"].

        Args:
            admin_config: The admin panel configuration.

        Returns:
            List of custom widget data.
        """
        return self._get_custom_widgets(admin_config)

    @staticmethod
    async def _get_model_count(session: AsyncSession, model: type[Any]) -> int:
        """Get the record count for a model.

        Args:
            session: The database session.
            model: The SQLAlchemy model class.

        Returns:
            Number of records in the model's table.
        """
        from sqlalchemy import func, select

        try:
            stmt = select(func.count()).select_from(model)
            result = await session.execute(stmt)
            count = result.scalar()
            return count if count is not None else 0
        except Exception:
            # Model might not have a table or session might be invalid
            return 0

    @staticmethod
    def _get_custom_widgets(config: AdminConfig) -> list[WidgetData]:
        """Extract custom widget configurations from admin config.

        Widgets are configured via AdminConfig.extra["widgets"] as a list
        of dictionaries with the following structure:
        {
            "id": "unique-widget-id",
            "type": "metric|chart|list|custom",
            "title": "Widget Title",
            "data": {...},
            "config": {...}
        }

        Args:
            config: The admin configuration.

        Returns:
            List of WidgetData instances.
        """
        widgets_config = config.extra.get("widgets", [])

        if not isinstance(widgets_config, list):
            return []

        widgets: list[WidgetData] = []
        for widget_dict in widgets_config:
            if not isinstance(widget_dict, dict):
                continue

            # Validate required fields
            widget_id = widget_dict.get("id")
            widget_type = widget_dict.get("type")
            widget_title = widget_dict.get("title")

            if not all([widget_id, widget_type, widget_title]):
                continue

            widgets.append(
                WidgetData(
                    id=str(widget_id),
                    type=str(widget_type),
                    title=str(widget_title),
                    data=widget_dict.get("data", {}),
                    config=widget_dict.get("config", {}),
                )
            )

        return widgets
