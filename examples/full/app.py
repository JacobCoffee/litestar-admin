"""Full admin demo application for litestar-admin.

This module provides a complete Litestar application demonstrating all features
of litestar-admin including:
- SQLAlchemy async integration with aiosqlite
- JWT authentication with role-based access control
- Multiple model views with custom configurations
- Rate limiting
- Startup seeding with demo data

Usage:
    Run directly with litestar CLI:
        litestar --app examples.full.app:app run --reload

    Or with uvicorn:
        uvicorn examples.full.app:app --reload

Default credentials:
    Email: admin@example.com
    Password: admin
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from advanced_alchemy.extensions.litestar import AsyncSessionConfig, SQLAlchemyAsyncConfig, SQLAlchemyPlugin
from litestar import Litestar, get
from litestar.di import Provide
from litestar.logging import LoggingConfig
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from examples.full.auth import get_auth_backend, hash_password
from examples.full.models import Article, ArticleStatus, Base, Tag, User, UserRole
from examples.full.views import ArticleAdmin, TagAdmin, UserAdmin
from litestar_admin import AdminConfig, AdminPlugin

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

__all__ = ["app"]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Database configuration
# Use an in-memory SQLite database with aiosqlite for the demo
# In production, use PostgreSQL, MySQL, or a persistent SQLite file
DATABASE_URL = "sqlite+aiosqlite:///./demo.db"

# Create async engine and session factory
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
    future=True,
)

# Create session factory using async_sessionmaker
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


def provide_session_factory() -> async_sessionmaker[AsyncSession]:
    """Provide the async session factory for dependency injection."""
    return async_session_factory


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Context manager for getting database sessions."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def create_tables() -> None:
    """Create all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")


async def seed_demo_data() -> None:
    """Seed the database with demo data.

    Creates:
    - Admin user (admin@example.com / admin)
    - Editor user (editor@example.com / editor)
    - Sample articles with different statuses
    - Sample tags
    """
    from sqlalchemy import select

    async with async_session_factory() as session:
        # Check if data already exists
        result = await session.execute(select(User).limit(1))
        if result.scalar_one_or_none() is not None:
            logger.info("Demo data already exists, skipping seed")
            return

        # Create admin user
        admin_user = User(
            email="admin@example.com",
            name="Admin User",
            password_hash=hash_password("admin"),
            role=UserRole.ADMIN,
            is_active=True,
        )
        session.add(admin_user)

        # Create editor user
        editor_user = User(
            email="editor@example.com",
            name="Editor User",
            password_hash=hash_password("editor"),
            role=UserRole.EDITOR,
            is_active=True,
        )
        session.add(editor_user)

        # Create viewer user
        viewer_user = User(
            email="viewer@example.com",
            name="Viewer User",
            password_hash=hash_password("viewer"),
            role=UserRole.VIEWER,
            is_active=True,
        )
        session.add(viewer_user)

        # Flush to get user IDs
        await session.flush()

        # Create tags
        tags = [
            Tag(name="Python", slug="python"),
            Tag(name="Litestar", slug="litestar"),
            Tag(name="Tutorial", slug="tutorial"),
            Tag(name="Admin", slug="admin"),
            Tag(name="SQLAlchemy", slug="sqlalchemy"),
        ]
        for tag in tags:
            session.add(tag)

        # Flush to get tag IDs
        await session.flush()

        # Create articles
        articles = [
            Article(
                title="Getting Started with Litestar Admin",
                content="""# Getting Started with Litestar Admin

Welcome to litestar-admin! This guide will help you get started with building
admin panels for your Litestar applications.

## Installation

```bash
pip install litestar-admin
```

## Basic Setup

Create a simple admin panel with just a few lines of code...
""",
                status=ArticleStatus.PUBLISHED,
                author_id=admin_user.id,
            ),
            Article(
                title="Advanced RBAC Configuration",
                content="""# Advanced RBAC Configuration

Learn how to configure role-based access control in litestar-admin.

## Understanding Roles

litestar-admin comes with four built-in roles:
- Viewer: Read-only access
- Editor: Can create and edit
- Admin: Full model management
- Superadmin: Complete system access

## Custom Permissions

You can also define custom permissions...
""",
                status=ArticleStatus.PUBLISHED,
                author_id=admin_user.id,
            ),
            Article(
                title="Draft: Upcoming Features",
                content="""# Upcoming Features (Draft)

This article is still being written...

## Planned Features

- Enhanced filtering
- Bulk actions
- Custom dashboards
""",
                status=ArticleStatus.DRAFT,
                author_id=editor_user.id,
            ),
            Article(
                title="Review: Best Practices",
                content="""# Best Practices for Admin Panels

This article is under review...

## Security Considerations

- Always use HTTPS in production
- Implement rate limiting
- Audit log all changes
""",
                status=ArticleStatus.REVIEW,
                author_id=editor_user.id,
            ),
        ]

        for article in articles:
            session.add(article)

        # Associate tags with articles
        await session.flush()

        # Add tags to articles (first two articles get some tags)
        articles[0].tags.extend([tags[0], tags[1], tags[2]])  # Python, Litestar, Tutorial
        articles[1].tags.extend([tags[1], tags[3]])  # Litestar, Admin

        await session.commit()
        logger.info("Demo data seeded successfully")
        logger.info("Default admin credentials: admin@example.com / admin")


async def startup_handler(app: Litestar) -> None:
    """Application startup handler.

    Creates database tables and seeds demo data.

    Args:
        app: The Litestar application instance.
    """
    logger.info("Starting application...")
    await create_tables()
    await seed_demo_data()
    logger.info("Application startup complete")


async def shutdown_handler(app: Litestar) -> None:
    """Application shutdown handler.

    Cleans up resources.

    Args:
        app: The Litestar application instance.
    """
    logger.info("Shutting down application...")
    await engine.dispose()
    logger.info("Application shutdown complete")


# Configure auth backend
auth_backend = get_auth_backend(get_session)

# Configure admin plugin
admin_plugin = AdminPlugin(
    config=AdminConfig(
        title="Full Admin Demo",
        base_url="/admin",
        theme="dark",
        auth_backend=auth_backend,
        views=[UserAdmin, ArticleAdmin, TagAdmin],
        auto_discover=False,  # We're explicitly registering views
        rate_limit_enabled=True,
        rate_limit_requests=100,
        rate_limit_window_seconds=60,
        debug=True,
    )
)

# Configure SQLAlchemy plugin
sqlalchemy_config = SQLAlchemyAsyncConfig(
    connection_string=DATABASE_URL,
    session_config=AsyncSessionConfig(expire_on_commit=False),
    create_all=False,  # We handle this in startup
)
sqlalchemy_plugin = SQLAlchemyPlugin(config=sqlalchemy_config)

# Configure logging
logging_config = LoggingConfig(
    root={"level": "INFO", "handlers": ["console"]},
    loggers={
        "litestar_admin": {"level": "DEBUG"},
        "examples.full": {"level": "DEBUG"},
        "sqlalchemy.engine": {"level": "WARNING"},
    },
)


@get("/")
async def index() -> dict[str, Any]:
    """Root endpoint with API information.

    Returns:
        API information and links.
    """
    return {
        "app": "litestar-admin Full Demo",
        "version": "0.1.0",
        "admin_url": "/admin",
        "api_docs": "/schema",
        "credentials": {
            "admin": {"email": "admin@example.com", "password": "admin"},
            "editor": {"email": "editor@example.com", "password": "editor"},
            "viewer": {"email": "viewer@example.com", "password": "viewer"},
        },
    }


@get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint.

    Returns:
        Health status.
    """
    return {"status": "healthy"}


# Create the application
app = Litestar(
    route_handlers=[index, health],
    plugins=[admin_plugin, sqlalchemy_plugin],
    on_startup=[startup_handler],
    on_shutdown=[shutdown_handler],
    dependencies={"session_factory": Provide(provide_session_factory, sync_to_thread=False)},
    logging_config=logging_config,
    debug=True,
)
