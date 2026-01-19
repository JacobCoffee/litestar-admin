"""Example showing Litestar admin mounted in a Starlette application.

This example demonstrates how to embed a Litestar admin panel within a Starlette
application using ASGI mounting. This pattern is useful when you have an existing
Starlette application and want to add litestar-admin without migrating to Litestar.

Key concepts:
- ASGI sub-application mounting with Starlette's Mount
- Shared SQLAlchemy async engine between applications
- Proper lifecycle management for database connections

Requirements:
    pip install starlette litestar litestar-admin sqlalchemy[asyncio] aiosqlite uvicorn

Usage:
    uvicorn examples.framework_bridge.starlette_mount:app --reload

Note:
    While this pattern works well, the recommended approach is to use Litestar
    natively for new applications to take full advantage of the framework features.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from litestar import Litestar
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from litestar_admin import AdminConfig, AdminPlugin, ModelView

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

# =============================================================================
# Database Models (shared between both applications)
# =============================================================================


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


class Article(Base):
    """Article model for demonstration."""

    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    content = Column(String(5000), nullable=False)
    author = Column(String(100), nullable=False)


class Category(Base):
    """Category model for demonstration."""

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(500))


# =============================================================================
# Shared Database Configuration
# =============================================================================

DATABASE_URL = "sqlite+aiosqlite:///./starlette_admin_demo.db"

# Create async engine that will be shared between Starlette and Litestar
engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=True)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_database() -> None:
    """Initialize the database by creating all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_database() -> None:
    """Close the database engine."""
    await engine.dispose()


# =============================================================================
# Litestar Admin Application
# =============================================================================


class ArticleAdmin(ModelView, model=Article):
    """Admin view for Article model."""

    column_list = ["id", "title", "author"]
    column_searchable_list = ["title", "author"]
    column_sortable_list = ["id", "title", "author"]
    can_create = True
    can_edit = True
    can_delete = True


class CategoryAdmin(ModelView, model=Category):
    """Admin view for Category model."""

    column_list = ["id", "name", "description"]
    column_searchable_list = ["name"]
    can_create = True
    can_edit = True
    can_delete = True


def create_admin_app() -> Litestar:
    """Create the Litestar admin application.

    Returns:
        Configured Litestar application with admin panel.
    """
    return Litestar(
        plugins=[
            AdminPlugin(
                config=AdminConfig(
                    title="Starlette + Litestar Admin",
                    base_url="/",  # Root path since mounted at /admin
                    views=[ArticleAdmin, CategoryAdmin],
                    auto_discover=False,  # We register views explicitly
                )
            )
        ],
        # Disable Litestar's own lifecycle hooks since Starlette manages the lifecycle
        on_startup=[],
        on_shutdown=[],
    )


# Create the admin Litestar app as a sub-application
admin_app = create_admin_app()


# =============================================================================
# Starlette Application
# =============================================================================


async def homepage(request: Request) -> JSONResponse:
    """Homepage endpoint for the Starlette app.

    Args:
        request: The incoming Starlette request.

    Returns:
        JSON response with application info.
    """
    return JSONResponse(
        {
            "message": "Welcome to the Starlette application",
            "admin_url": "/admin",
            "api_endpoints": ["/api/articles", "/api/categories"],
        }
    )


async def list_articles(request: Request) -> JSONResponse:
    """List all articles via Starlette endpoint.

    Demonstrates that the Starlette app can use the same database
    as the admin panel.

    Args:
        request: The incoming Starlette request.

    Returns:
        JSON response with list of articles.
    """
    async with async_session_factory() as session:
        from sqlalchemy import select

        result = await session.execute(select(Article))
        articles = result.scalars().all()
        return JSONResponse({"articles": [{"id": a.id, "title": a.title, "author": a.author} for a in articles]})


async def list_categories(request: Request) -> JSONResponse:
    """List all categories via Starlette endpoint.

    Args:
        request: The incoming Starlette request.

    Returns:
        JSON response with list of categories.
    """
    async with async_session_factory() as session:
        from sqlalchemy import select

        result = await session.execute(select(Category))
        categories = result.scalars().all()
        return JSONResponse(
            {"categories": [{"id": c.id, "name": c.name, "description": c.description} for c in categories]}
        )


@asynccontextmanager
async def lifespan(app: Starlette) -> AsyncGenerator[None, None]:
    """Manage application lifespan for database initialization.

    This context manager handles startup and shutdown events for the
    Starlette application, including database initialization.

    Args:
        app: The Starlette application instance.

    Yields:
        None during the application's active lifespan.
    """
    # Startup: Initialize database
    await init_database()
    print("Database initialized")
    print("Admin panel available at: http://localhost:8000/admin")

    yield

    # Shutdown: Close database connections
    await close_database()
    print("Database connections closed")


# Define Starlette routes
routes = [
    Route("/", homepage),
    Route("/api/articles", list_articles),
    Route("/api/categories", list_categories),
    # Mount the Litestar admin app at /admin
    Mount("/admin", app=admin_app),
]

# Create the main Starlette application
app = Starlette(
    routes=routes,
    lifespan=lifespan,
)


# =============================================================================
# Alternative: Using a factory function for more control
# =============================================================================


def create_app_with_admin(admin_base_url: str = "/admin") -> Starlette:
    """Factory function to create Starlette app with mounted admin.

    This demonstrates a more configurable approach where the admin
    mount point can be customized.

    Args:
        admin_base_url: The URL path where admin will be mounted.

    Returns:
        Configured Starlette application with admin panel.
    """
    litestar_admin = Litestar(
        plugins=[
            AdminPlugin(
                config=AdminConfig(
                    title="Custom Admin",
                    base_url="/",
                    views=[ArticleAdmin, CategoryAdmin],
                    auto_discover=False,
                )
            )
        ],
    )

    return Starlette(
        routes=[
            Route("/", homepage),
            Route("/api/articles", list_articles),
            Route("/api/categories", list_categories),
            Mount(admin_base_url, app=litestar_admin),
        ],
        lifespan=lifespan,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
