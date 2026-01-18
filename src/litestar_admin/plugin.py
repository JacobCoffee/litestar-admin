"""AdminPlugin implementing Litestar's InitPluginProtocol."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from litestar.plugins import InitPluginProtocol

from litestar_admin.config import AdminConfig
from litestar_admin.registry import ModelRegistry

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from litestar import Litestar
    from litestar.config.app import AppConfig
    from litestar.di import Provide

__all__ = ["AdminPlugin"]


class AdminPlugin(InitPluginProtocol):
    """Litestar plugin for the admin panel.

    This plugin provides a complete admin panel interface for managing
    SQLAlchemy models in Litestar applications.

    Example:
        ```python
        from litestar import Litestar
        from litestar_admin import AdminPlugin, AdminConfig

        app = Litestar(
            plugins=[
                AdminPlugin(
                    config=AdminConfig(
                        title="My Admin",
                        base_url="/admin",
                    )
                )
            ]
        )
        ```
    """

    __slots__ = ("_app", "_config", "_registry")

    def __init__(self, config: AdminConfig | None = None) -> None:
        """Initialize the admin plugin.

        Args:
            config: Admin configuration. If not provided, uses defaults.
        """
        self._config = config or AdminConfig()
        self._registry = ModelRegistry()
        self._app: Litestar | None = None

    @property
    def config(self) -> AdminConfig:
        """Return the admin configuration."""
        return self._config

    @property
    def registry(self) -> ModelRegistry:
        """Return the model registry."""
        return self._registry

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        """Initialize the plugin when the Litestar app is created.

        This method is called by Litestar during app initialization.
        It registers controllers, dependencies, and configures static files.

        Args:
            app_config: The Litestar application configuration.

        Returns:
            The modified application configuration.
        """
        # Register views from config
        for view_class in self._config.views:
            self._registry.register(view_class)

        # Add dependencies
        existing_deps: dict[str, Provide | Callable[..., Any]] = dict(app_config.dependencies or {})
        app_config.dependencies = {**existing_deps, **self._get_dependencies()}

        # Add route handlers (controllers)
        app_config.route_handlers = [
            *list(app_config.route_handlers or []),
            *self._get_controllers(),
        ]

        # Add lifecycle hooks
        app_config.on_startup = [
            *list(app_config.on_startup or []),
            self._startup,
        ]
        app_config.on_shutdown = [
            *list(app_config.on_shutdown or []),
            self._shutdown,
        ]

        # Configure static files
        self._configure_static_files(app_config)

        return app_config

    def _get_dependencies(self) -> dict[str, Provide]:
        """Get plugin dependencies for injection."""
        from litestar.di import Provide

        return {
            "admin_config": Provide(lambda: self._config, sync_to_thread=False),
            "admin_registry": Provide(lambda: self._registry, sync_to_thread=False),
        }

    def _get_controllers(self) -> list[type]:
        """Get admin controllers to register."""
        # Import controllers lazily to avoid circular imports
        from litestar_admin.controllers import (
            AuthController,
            BulkActionsController,
            DashboardController,
            ExportController,
            ModelsController,
        )

        return [AuthController, BulkActionsController, DashboardController, ExportController, ModelsController]

    def _configure_static_files(self, app_config: AppConfig) -> None:
        """Configure static file serving for the admin panel."""
        from litestar.static_files import create_static_files_router

        # Determine static files path
        static_path = (
            Path(self._config.static_path)
            if self._config.static_path
            else Path(__file__).parent / "static"
        )

        if static_path.exists():
            static_router = create_static_files_router(
                path=self._config.static_base_url,
                directories=[static_path],
                html_mode=True,  # SPA routing support
            )
            app_config.route_handlers = [
                *list(app_config.route_handlers or []),
                static_router,
            ]

    async def _startup(self, app: Litestar) -> None:
        """Run startup tasks for the admin plugin.

        Args:
            app: The Litestar application instance.
        """
        self._app = app

        # Auto-discover models if enabled
        if self._config.auto_discover:
            await self._auto_discover_models(app)

    async def _shutdown(self, app: Litestar) -> None:  # noqa: ARG002
        """Run shutdown tasks for the admin plugin.

        Args:
            app: The Litestar application instance.
        """
        self._app = None

    async def _auto_discover_models(self, app: Litestar) -> None:
        """Auto-discover SQLAlchemy models from the application.

        This method scans for SQLAlchemy DeclarativeBase subclasses and their
        registered models. For each model that hasn't been explicitly registered
        with a custom view, a default view is created automatically.

        The discovery process:
        1. Find all DeclarativeBase classes from app state or plugins
        2. Extract all model classes from their registries
        3. Skip models that already have registered views
        4. Create default views for remaining models

        Args:
            app: The Litestar application instance.
        """
        import logging

        from litestar_admin.discovery import (
            create_default_view,
            discover_models,
            get_declarative_bases,
        )

        logger = logging.getLogger("litestar_admin.discovery")

        # Get already-registered models to skip
        registered_models: set[type[Any]] = {
            view_class.model for view_class in self._registry
        }

        # Find all DeclarativeBase classes in the application
        bases = get_declarative_bases(app)

        if not bases:
            logger.debug("No DeclarativeBase classes found for auto-discovery")
            return

        logger.debug("Found %d DeclarativeBase class(es) for auto-discovery", len(bases))

        # Discover models from bases, excluding already-registered ones
        models = discover_models(bases, exclude_models=registered_models)

        if not models:
            logger.debug("No new models discovered for auto-registration")
            return

        logger.info("Auto-discovered %d model(s)", len(models))

        # Create and register default views for discovered models
        for model in models:
            if self._registry.has_model(model):
                # Double-check in case of race conditions
                continue

            try:
                view_class = create_default_view(model, auto_columns=True)
                self._registry.register(view_class)
                logger.debug("Registered auto-discovered view for: %s", model.__name__)
            except Exception:
                logger.exception("Failed to create view for model: %s", model.__name__)
