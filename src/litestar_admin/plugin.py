"""AdminPlugin implementing Litestar's InitPluginProtocol."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from litestar import Response, get
from litestar.plugins import InitPluginProtocol

from litestar_admin.config import AdminConfig
from litestar_admin.registry import ViewRegistry

if TYPE_CHECKING:
    from collections.abc import Callable

    from litestar import Litestar, Router
    from litestar.config.app import AppConfig
    from litestar.di import Provide

__all__ = ["AdminPlugin"]

# Cache durations for static assets (in seconds)
_CACHE_IMMUTABLE_MAX_AGE = 31536000  # 1 year for immutable assets (hashed filenames)
_CACHE_HTML_MAX_AGE = 0  # No caching for HTML (always revalidate)


class AdminPlugin(InitPluginProtocol):
    """Litestar plugin for the admin panel.

    This plugin provides a complete admin panel interface for managing
    SQLAlchemy models in Litestar applications.

    Example::

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
    """

    __slots__ = ("_app", "_config", "_registry")

    def __init__(self, config: AdminConfig | None = None) -> None:
        """Initialize the admin plugin.

        Args:
            config: Admin configuration. If not provided, uses defaults.
        """
        self._config = config or AdminConfig()
        self._registry = ViewRegistry()
        self._app: Litestar | None = None

    @property
    def config(self) -> AdminConfig:
        """Return the admin configuration."""
        return self._config

    @property
    def registry(self) -> ViewRegistry:
        """Return the view registry.

        The registry manages all registered admin views, including model-based
        views (ModelView) and non-model views (CustomView, ActionView, PageView,
        LinkView, EmbedView).

        Returns:
            The ViewRegistry instance.
        """
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

        # Add route handlers (API router with controllers)
        app_config.route_handlers = [
            *list(app_config.route_handlers or []),
            self._get_api_router(),
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

    def _get_api_router(self) -> Router:
        """Get admin API router with all controllers.

        Creates a Router mounted at the admin base_url that contains all
        API controllers. The controllers define their own paths (e.g., /api/models)
        which become relative to the router's path.

        Returns:
            A Router containing all admin API controllers.
        """
        from litestar import Router

        # Import controllers lazily to avoid circular imports
        from litestar_admin.controllers import (
            AuthController,
            BulkActionsController,
            ConfigController,
            DashboardController,
            ExportController,
            ModelsController,
        )

        # Create a router at the admin base URL for all API endpoints
        # Controllers define paths like /api/models, so final paths become
        # /admin/api/models (when base_url is /admin)
        return Router(
            path=self._config.base_url,
            route_handlers=[
                AuthController,
                BulkActionsController,
                ConfigController,
                DashboardController,
                ExportController,
                ModelsController,
            ],
        )

    def _configure_static_files(self, app_config: AppConfig) -> None:
        """Configure static file serving for the admin panel frontend.

        Sets up a static files router to serve the Next.js static export at the
        admin base URL. Configuration includes:
        - SPA routing with catch-all fallback to index.html
        - Cache headers for optimal performance (immutable assets get long cache)
        - Proper base path handling for the frontend

        Note: API routes are registered separately and take precedence over static
        file serving due to their more specific paths (/admin/api/* vs /admin/*).
        """
        from litestar.static_files import create_static_files_router

        # Determine static files path
        static_path = Path(self._config.static_path) if self._config.static_path else Path(__file__).parent / "static"

        if not static_path.exists():
            return

        index_html_path = static_path / "index.html"
        models_html_path = static_path / "models" / "index.html"

        # Create static router for actual static files (_next/*, login/, etc.)
        static_router = create_static_files_router(
            path=self._config.base_url,
            directories=[static_path],
            html_mode=True,
            name="admin_static",
            after_request=_add_cache_headers,
        )

        # SPA catch-all route - serves models/index.html for model routes
        # This enables client-side routing for paths like /admin/models/User
        # IMPORTANT: We only handle routes that are NOT static assets
        @get(
            path=[
                f"{self._config.base_url}/models/",
                f"{self._config.base_url}/models/{{path:path}}",
            ],
            name="admin_spa_fallback",
            include_in_schema=False,
        )
        async def spa_fallback(path: str = "") -> Response[bytes]:  # noqa: ARG001
            """Serve models/index.html for SPA client-side routing."""
            # Serve the models page HTML for all /models/* routes
            html_path = models_html_path if models_html_path.exists() else index_html_path
            if html_path.exists():
                content = html_path.read_bytes()
                return Response(
                    content=content,
                    media_type="text/html",
                    headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
                )
            return Response(content=b"Not Found", status_code=404)

        app_config.route_handlers = [
            *list(app_config.route_handlers or []),
            static_router,
            spa_fallback,
        ]

    async def _startup(self, app: Litestar) -> None:
        """Run startup tasks for the admin plugin.

        Args:
            app: The Litestar application instance.
        """
        from litestar_admin.logging import configure_logging

        self._app = app

        # Configure logging if a logging config is provided
        if self._config.logging_config is not None:
            configure_logging(self._config.logging_config)

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
        from litestar_admin.discovery import (
            create_default_view,
            discover_models,
            get_declarative_bases,
        )
        from litestar_admin.logging import get_logger

        logger = get_logger("litestar_admin.discovery")

        # Get already-registered models to skip
        registered_models: set[type[Any]] = {view_class.model for view_class in self._registry}

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


def _add_cache_headers(response: Any) -> Any:
    """Add appropriate cache headers to static file responses.

    Implements a caching strategy optimized for Next.js static exports:
    - Hashed assets (_next/static/*): Cache for 1 year with immutable flag
    - HTML files: No caching (must revalidate every request)
    - Other assets: Short cache with must-revalidate

    Args:
        response: The Litestar response object.

    Returns:
        The response with updated cache headers.
    """
    from litestar.datastructures import CacheControlHeader
    from litestar.response import Response

    if not isinstance(response, Response):
        return response

    # Get the media type to determine caching strategy
    # The media_type attribute contains the content type (e.g., "text/html")
    media_type = getattr(response, "media_type", "") or ""

    if "text/html" in media_type:
        # HTML files: no caching, always revalidate
        # This ensures users always get the latest version of the SPA
        response.headers["Cache-Control"] = CacheControlHeader(
            no_cache=True,
            no_store=True,
            must_revalidate=True,
        ).to_header()
    else:
        # Static assets (JS, CSS, images): cache with immutable for hashed assets
        # Next.js uses content hashing for cache busting, so we can safely
        # apply long-term caching to all non-HTML assets
        response.headers["Cache-Control"] = CacheControlHeader(
            max_age=_CACHE_IMMUTABLE_MAX_AGE,
            public=True,
            immutable=True,
        ).to_header()

    return response
