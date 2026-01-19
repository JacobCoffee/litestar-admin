"""Raw ASGI example demonstrating low-level integration with litestar-admin.

This example shows how to wrap a Litestar application with AdminPlugin using
custom ASGI middleware. It demonstrates the ASGI interface directly and includes
proper lifespan event handling.

Litestar applications are fully ASGI-compatible, meaning they can be wrapped,
composed, or extended using standard ASGI patterns.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from litestar import Litestar, get
from sqlalchemy import Integer, String
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from litestar_admin import AdminConfig, AdminPlugin, BaseModelView

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable

    # ASGI types
    Scope = dict[str, Any]
    Receive = Callable[[], Awaitable[dict[str, Any]]]
    Send = Callable[[dict[str, Any]], Awaitable[None]]
    ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


# ==============================================================================
# Database Models
# ==============================================================================


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


class Task(Base):
    """A simple task model for demonstration."""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")


class Project(Base):
    """A project model to group tasks."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)


# ==============================================================================
# Admin Views
# ==============================================================================


class TaskAdmin(BaseModelView):
    """Admin view for Task model."""

    model = Task
    name = "Task"
    name_plural = "Tasks"
    icon = "check-square"
    column_list = ["id", "title", "description", "status"]
    column_searchable_list = ["title", "description"]
    column_sortable_list = ["id", "title", "status"]
    can_create = True
    can_edit = True
    can_delete = True


class ProjectAdmin(BaseModelView):
    """Admin view for Project model."""

    model = Project
    name = "Project"
    name_plural = "Projects"
    icon = "folder"
    column_list = ["id", "name", "code"]
    column_searchable_list = ["name", "code"]
    column_sortable_list = ["id", "name"]
    can_create = True
    can_edit = True
    can_delete = True


# ==============================================================================
# Database Setup
# ==============================================================================


# Create async engine with aiosqlite for in-memory database
engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    echo=False,
)

# Session factory for dependency injection
session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Provide database session for dependency injection."""
    async with session_factory() as session:
        yield session
        await session.commit()


# ==============================================================================
# ASGI Middleware
# ==============================================================================


class RequestLoggingMiddleware:
    """Simple ASGI middleware that logs incoming requests.

    This demonstrates how to wrap a Litestar app (or any ASGI app) with
    custom middleware at the ASGI level.

    The ASGI interface consists of three components:
    - scope: A dict containing request metadata (type, path, headers, etc.)
    - receive: An async callable to receive incoming messages
    - send: An async callable to send outgoing messages
    """

    def __init__(self, app: ASGIApp) -> None:
        """Initialize the middleware.

        Args:
            app: The ASGI application to wrap.
        """
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle the ASGI request.

        Args:
            scope: Request scope containing metadata.
            receive: Async callable to receive messages.
            send: Async callable to send messages.
        """
        if scope["type"] == "http":
            method = scope.get("method", "UNKNOWN")
            path = scope.get("path", "/")
            print(f"[ASGI] {method} {path}")

        await self.app(scope, receive, send)


class TimingMiddleware:
    """ASGI middleware that measures request processing time.

    This is another example of raw ASGI middleware that can be composed
    with any ASGI application including Litestar.
    """

    def __init__(self, app: ASGIApp) -> None:
        """Initialize the middleware.

        Args:
            app: The ASGI application to wrap.
        """
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle the ASGI request with timing.

        Args:
            scope: Request scope containing metadata.
            receive: Async callable to receive messages.
            send: Async callable to send messages.
        """
        import time

        if scope["type"] == "http":
            start_time = time.perf_counter()

            async def send_with_timing(message: dict[str, Any]) -> None:
                if message["type"] == "http.response.start":
                    elapsed = (time.perf_counter() - start_time) * 1000
                    print(f"[ASGI] Request processed in {elapsed:.2f}ms")
                await send(message)

            await self.app(scope, receive, send_with_timing)
        else:
            await self.app(scope, receive, send)


# ==============================================================================
# Litestar Application
# ==============================================================================


@get("/")
async def index() -> dict[str, str]:
    """Root endpoint returning API info."""
    return {
        "message": "Welcome to the Raw ASGI Example",
        "admin_url": "/admin",
        "docs_url": "/schema",
    }


@get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


# Create the Litestar app with AdminPlugin
admin_plugin = AdminPlugin(
    config=AdminConfig(
        title="Raw ASGI Admin",
        base_url="/admin",
        views=[TaskAdmin, ProjectAdmin],
        auto_discover=False,
        debug=True,
    )
)


@asynccontextmanager
async def lifespan(app: Litestar) -> AsyncIterator[None]:
    """Handle application lifespan events.

    This context manager is called when the ASGI server starts and stops.
    It's the modern replacement for on_startup/on_shutdown hooks.

    Args:
        app: The Litestar application instance.

    Yields:
        None after startup completes.
    """
    # Startup
    print("[Lifespan] Starting application...")
    await init_db()
    print("[Lifespan] Database initialized")

    yield

    # Shutdown
    print("[Lifespan] Shutting down application...")
    await close_db()
    print("[Lifespan] Database connections closed")


# Create the Litestar application
litestar_app = Litestar(
    route_handlers=[index, health_check],
    plugins=[admin_plugin],
    dependencies={"db_session": get_db_session},
    lifespan=[lifespan],
    debug=True,
)


# ==============================================================================
# Wrapped ASGI Application
# ==============================================================================


def create_wrapped_app() -> ASGIApp:
    """Create the ASGI application with middleware stack.

    This demonstrates composing multiple ASGI middleware layers around
    the Litestar application. The middleware stack is applied in order:
    1. TimingMiddleware (outermost)
    2. RequestLoggingMiddleware
    3. Litestar app (innermost)

    Returns:
        The fully wrapped ASGI application.
    """
    # Start with the Litestar app (which is ASGI-compatible)
    app: ASGIApp = litestar_app

    # Wrap with logging middleware
    app = RequestLoggingMiddleware(app)

    # Wrap with timing middleware (outermost)
    app = TimingMiddleware(app)

    return app


# The final ASGI application to be served
app = create_wrapped_app()


# ==============================================================================
# Direct ASGI Wrapper Example
# ==============================================================================


class DirectASGIWrapper:
    """Example of a more complex ASGI wrapper.

    This class demonstrates how to create a custom ASGI application that
    wraps Litestar and adds custom behavior. This pattern is useful when you
    need fine-grained control over the ASGI lifecycle.
    """

    def __init__(self, inner_app: ASGIApp) -> None:
        """Initialize the wrapper.

        Args:
            inner_app: The ASGI application to wrap.
        """
        self.inner_app = inner_app
        self._startup_complete = False

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle ASGI requests.

        Args:
            scope: Request scope containing metadata.
            receive: Async callable to receive messages.
            send: Async callable to send messages.
        """
        if scope["type"] == "lifespan":
            await self._handle_lifespan(scope, receive, send)
        else:
            await self.inner_app(scope, receive, send)

    async def _handle_lifespan(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle lifespan events with custom logic.

        Args:
            scope: Lifespan scope.
            receive: Async callable to receive lifespan messages.
            send: Async callable to send lifespan messages.
        """
        while True:
            message = await receive()

            if message["type"] == "lifespan.startup":
                try:
                    # Forward startup to inner app
                    # Custom pre-startup logic could go here
                    print("[DirectASGIWrapper] Pre-startup hook")

                    # Create a wrapper to capture inner app's startup
                    await self._forward_lifespan_startup(scope, receive, send)

                    print("[DirectASGIWrapper] Post-startup hook")
                    self._startup_complete = True

                except Exception as e:
                    await send({"type": "lifespan.startup.failed", "message": str(e)})
                    return

            elif message["type"] == "lifespan.shutdown":
                try:
                    print("[DirectASGIWrapper] Pre-shutdown hook")
                    await self._forward_lifespan_shutdown(scope, receive, send)
                    print("[DirectASGIWrapper] Post-shutdown hook")
                except Exception as e:
                    await send({"type": "lifespan.shutdown.failed", "message": str(e)})
                return

    async def _forward_lifespan_startup(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Forward startup to inner app."""
        # For simplicity, we just send the startup complete message
        # In a real implementation, you would forward to the inner app
        await send({"type": "lifespan.startup.complete"})

    async def _forward_lifespan_shutdown(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Forward shutdown to inner app."""
        await send({"type": "lifespan.shutdown.complete"})


# Alternative app using the direct wrapper pattern
# app_direct = DirectASGIWrapper(litestar_app)


# ==============================================================================
# Entry Point
# ==============================================================================


if __name__ == "__main__":
    import uvicorn

    print("Starting Raw ASGI Example...")
    print("Admin panel available at: http://127.0.0.1:8000/admin")
    print("API docs available at: http://127.0.0.1:8000/schema")

    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
    )
