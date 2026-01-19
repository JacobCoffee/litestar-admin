"""Full admin demo application for litestar-admin.

This module provides a complete Litestar application demonstrating all features
of litestar-admin including:
- SQLAlchemy async integration with aiosqlite
- JWT authentication with role-based access control (default)
- OAuth authentication with GitHub (optional, see below)
- Multiple model views with custom configurations
- Rate limiting (with optional Redis backend)
- Startup seeding with demo data
- Structured logging with structlog integration
- Optional Redis integration for:
  - Rate limit storage (shared across workers)
  - Session/token storage (persistent sessions)
  - General-purpose caching

Usage:
    Run directly with litestar CLI:
        litestar --app examples.full.app:app run --reload

    Or with uvicorn:
        uvicorn examples.full.app:app --reload

    With Redis (optional):
        REDIS_URL=redis://localhost:6379/0 litestar --app examples.full.app:app run --reload

Default credentials (JWT auth):
    Email: admin@example.com
    Password: admin

Redis Integration (Optional):
    To enable Redis support for rate limiting, sessions, and caching:

    1. Install Redis and start the server:
       - macOS: brew install redis && brew services start redis
       - Linux: apt-get install redis-server && systemctl start redis
       - Docker: docker run -d -p 6379:6379 redis:alpine

    2. Install the redis Python package:
       pip install redis[hiredis]  # hiredis is optional but recommended

    3. Set the REDIS_URL environment variable:
       export REDIS_URL="redis://localhost:6379/0"

    4. Run the application - it will automatically use Redis for:
       - Rate limiting: Shared across all workers/processes
       - Session storage: Tokens persist across restarts
       - Caching: Reduce database load for expensive queries

    If Redis is not available, the application gracefully falls back to
    in-memory storage (suitable for development and single-worker deployments).

    Redis URL Format:
        redis://[[username]:[password]@]host[:port][/database]

        Examples:
        - redis://localhost:6379/0         (local, database 0)
        - redis://redis.example.com:6379/1 (remote, database 1)
        - redis://:password@localhost:6379 (with password)

OAuth Authentication (GitHub):
    To enable GitHub OAuth instead of JWT authentication:

    1. Create a GitHub OAuth App:
       - Go to https://github.com/settings/developers
       - Click "New OAuth App"
       - Set "Authorization callback URL" to:
         http://localhost:8000/admin/auth/oauth/github/callback
       - Note the Client ID and generate a Client Secret

    2. Set environment variables:
       export GITHUB_CLIENT_ID="your-client-id"
       export GITHUB_CLIENT_SECRET="your-client-secret"

    3. Uncomment the OAuth backend configuration below and comment out
       the JWT backend configuration.

    4. Install OAuth dependencies:
       pip install 'litestar-admin[oauth]'

    5. Run the app - users can now login via GitHub OAuth.
       New users are automatically created on first login with VIEWER role.

Demo OAuth Authentication (No External Credentials):
    To test the OAuth flow without real GitHub credentials:

    1. Set the OAUTH_DEMO_MODE environment variable:
       export OAUTH_DEMO_MODE=true

    2. Optionally configure the demo user:
       export DEMO_OAUTH_EMAIL="test@example.com"
       export DEMO_OAUTH_NAME="Test User"

    3. Run the app:
       OAUTH_DEMO_MODE=true litestar --app examples.full.app:app run --reload

    The demo OAuth provider will:
    - Accept any authorization code
    - Return a configurable demo user (default: demo@example.com)
    - Skip all external OAuth API calls
    - Create a real user in the database on first login

    This is useful for:
    - Local development without GitHub OAuth setup
    - CI/CD pipeline testing
    - Demonstrating the admin panel to stakeholders
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from advanced_alchemy.extensions.litestar import AsyncSessionConfig, SQLAlchemyAsyncConfig, SQLAlchemyPlugin
from litestar import Litestar, get
from litestar.di import Provide
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from examples.full.auth import get_auth_backend, hash_password
from examples.full.models import Article, ArticleStatus, Base, Tag, User, UserRole
from examples.full.views import AppSettingsAdmin, ArticleAdmin, SystemInfoAdmin, TagAdmin, UserAdmin
from litestar_admin import AdminConfig, AdminPlugin, get_logger

# =============================================================================
# Optional: SQLAdmin Bridge for Migration
# =============================================================================
# If you're migrating from sqladmin to litestar-admin, you can use the bridge
# to convert your existing sqladmin ModelView classes. This allows you to
# gradually migrate without rewriting all your view configurations.
#
# When to use the bridge:
#   - You have an existing application using sqladmin
#   - You want to migrate to litestar-admin incrementally
#   - You have complex sqladmin views you don't want to rewrite immediately
#
# Note: Some sqladmin-specific features (like column_formatters, form_args,
# and modal editing) cannot be converted and will be skipped with warnings.
#
# Uncomment the following to enable sqladmin bridge:
#
# from litestar_admin.contrib.sqladmin import SQLAdminBridge, convert_sqladmin_view
#
# # Example: If you have existing sqladmin views like this:
# # from sqladmin import ModelView as SQLAdminModelView
# #
# # class LegacyUserAdmin(SQLAdminModelView, model=User):
# #     column_list = ["id", "email", "name", "role", "is_active"]
# #     column_searchable_list = ["email", "name"]
# #     column_sortable_list = ["email", "created_at"]
# #     can_delete = False
# #
# # class LegacyArticleAdmin(SQLAdminModelView, model=Article):
# #     column_list = ["id", "title", "status", "author_id"]
# #     column_default_sort = ("created_at", True)  # Sort by created_at desc
#
# # Option 1: Convert a single view
# # ConvertedUserAdmin = convert_sqladmin_view(LegacyUserAdmin)
#
# # Option 2: Use the bridge for multiple views
# # bridge = SQLAdminBridge(strict=False)  # strict=True raises errors for unsupported features
# # bridge.register(LegacyUserAdmin)
# # bridge.register(LegacyArticleAdmin)
# # converted_views = bridge.convert_all()
# #
# # # Check for any conversion warnings
# # for warning in bridge.warnings:
# #     logger.warning(f"SQLAdmin bridge: {warning}")
# #
# # # Use converted views in AdminConfig
# # # views=[*converted_views, TagAdmin]  # Mix converted and native views
# =============================================================================

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

__all__ = ["app"]

# Get a structlog-compatible logger via litestar-admin's logging abstraction
# This automatically uses structlog when available, with fallback to stdlib
logger = get_logger(__name__)

# =============================================================================
# Redis Configuration (Optional)
# =============================================================================
# Redis enables distributed rate limiting, persistent sessions, and caching.
# Without Redis, the application uses in-memory storage (single-process only).
#
# Set REDIS_URL environment variable to enable:
#   export REDIS_URL="redis://localhost:6379/0"
#
# Benefits of Redis:
# - Rate limiting works correctly with multiple workers (uvicorn -w 4)
# - Sessions persist across application restarts
# - Cache is shared across all workers
# =============================================================================
REDIS_URL: str | None = os.environ.get("REDIS_URL")

# These will be initialized at startup if Redis is available
redis_rate_limit_store: Any = None
redis_session_store: Any = None
redis_cache: Any = None

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

        # Flush to get IDs assigned
        await session.flush()

        # Associate tags with articles using direct insert into association table
        # This avoids async lazy loading issues
        from examples.full.models import ArticleTag

        await session.execute(
            ArticleTag.insert().values(
                [
                    # Article 1 (Getting Started): Python, Litestar, Tutorial
                    {"article_id": articles[0].id, "tag_id": tags[0].id},
                    {"article_id": articles[0].id, "tag_id": tags[1].id},
                    {"article_id": articles[0].id, "tag_id": tags[2].id},
                    # Article 2 (Advanced Auth): Litestar, Admin
                    {"article_id": articles[1].id, "tag_id": tags[1].id},
                    {"article_id": articles[1].id, "tag_id": tags[3].id},
                ]
            )
        )

        await session.commit()
        logger.info("Demo data seeded successfully")
        logger.info("Default admin credentials: admin@example.com / admin")


async def initialize_redis_stores() -> None:
    """Initialize Redis-backed stores if Redis is available.

    This function attempts to connect to Redis and create stores for:
    - Rate limiting: Shared across all workers
    - Session storage: Persistent tokens across restarts
    - Caching: Reduce database load

    If Redis is not available (not installed, not running, or REDIS_URL not set),
    this function logs a message and returns without error. The application
    will use in-memory storage instead.

    The initialized stores are stored in module-level variables for access
    by other parts of the application.
    """
    global redis_rate_limit_store, redis_session_store, redis_cache

    if not REDIS_URL:
        logger.info(
            "Redis not configured (REDIS_URL not set). Using in-memory storage.",
            hint="Set REDIS_URL=redis://localhost:6379/0 for distributed rate limiting",
        )
        return

    try:
        from examples.full.redis_store import (
            create_redis_cache,
            create_redis_rate_limit_store,
            create_redis_session_store,
        )

        # Create Redis stores - these return None if Redis is unavailable
        redis_rate_limit_store = await create_redis_rate_limit_store(REDIS_URL)
        redis_session_store = await create_redis_session_store(REDIS_URL)
        redis_cache = await create_redis_cache(REDIS_URL)

        if redis_rate_limit_store:
            logger.info(
                "Redis stores initialized successfully",
                rate_limit="enabled",
                sessions="enabled",
                cache="enabled",
            )
        else:
            logger.warning(
                "Redis connection failed. Using in-memory storage.",
                url=REDIS_URL.split("@")[-1] if REDIS_URL else None,
            )

    except ImportError:
        logger.warning(
            "redis package not installed. Using in-memory storage.",
            hint="Install with: pip install redis[hiredis]",
        )
    except Exception as e:
        logger.warning(
            "Failed to initialize Redis stores. Using in-memory storage.",
            error=str(e),
        )


async def startup_handler(app: Litestar) -> None:
    """Application startup handler.

    Creates database tables, seeds demo data, and initializes Redis stores.

    Args:
        app: The Litestar application instance.
    """
    logger.info("Starting application...")

    # Initialize Redis stores (optional - falls back to in-memory)
    await initialize_redis_stores()

    # Create database tables and seed data
    await create_tables()
    await seed_demo_data()

    # Log Redis status
    if redis_rate_limit_store:
        logger.info("Rate limiting: Redis (distributed)")
    else:
        logger.info("Rate limiting: In-memory (single process only)")

    # Log authentication mode
    if OAUTH_DEMO_MODE:
        demo_email = os.environ.get("DEMO_OAUTH_EMAIL", "demo@example.com")
        logger.info(
            "Authentication: Demo OAuth mode",
            demo_user=demo_email,
            hint="Use the 'demo' provider to login - any code accepted",
        )
    elif GITHUB_OAUTH_CONFIGURED:
        logger.info(
            "Authentication: GitHub OAuth",
            hint="Login via GitHub - new users auto-created with VIEWER role",
        )
    else:
        logger.info(
            "Authentication: JWT (username/password)",
            credentials="admin@example.com / admin",
        )

    logger.info("Application startup complete")


async def shutdown_handler(app: Litestar) -> None:
    """Application shutdown handler.

    Cleans up resources including database connections and Redis clients.

    Args:
        app: The Litestar application instance.
    """
    logger.info("Shutting down application...")

    # Close Redis connections if they exist
    if redis_rate_limit_store:
        try:
            await redis_rate_limit_store.close()
            logger.debug("Redis rate limit store closed")
        except Exception as e:
            logger.warning("Error closing Redis rate limit store", error=str(e))

    if redis_session_store:
        try:
            await redis_session_store.close()
            logger.debug("Redis session store closed")
        except Exception as e:
            logger.warning("Error closing Redis session store", error=str(e))

    if redis_cache:
        try:
            await redis_cache.close()
            logger.debug("Redis cache closed")
        except Exception as e:
            logger.warning("Error closing Redis cache", error=str(e))

    # Close database connection
    await engine.dispose()
    logger.info("Application shutdown complete")


# =============================================================================
# Authentication Backend Configuration
# =============================================================================
# Choose ONE of the following authentication backends:
#
# Option 1: JWT Authentication (default)
# - Username/password login with JWT tokens
# - Demo users are seeded on startup
# - Use credentials: admin@example.com / admin
#
# Option 2: OAuth Authentication (GitHub)
# - Login with GitHub OAuth
# - Requires GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET env vars
# - New users are auto-created on first login
#
# Option 3: Demo OAuth Authentication (no external credentials)
# - Simulates OAuth flow without external API calls
# - Enabled via OAUTH_DEMO_MODE=true environment variable
# - Demo user created in database on first login
# - Perfect for local development and testing
# =============================================================================

# Check for OAuth demo mode first (Option 3)
OAUTH_DEMO_MODE = os.environ.get("OAUTH_DEMO_MODE", "").lower() in ("true", "1", "yes")

# Check for GitHub OAuth credentials (Option 2)
GITHUB_OAUTH_CONFIGURED = bool(os.environ.get("GITHUB_CLIENT_ID") and os.environ.get("GITHUB_CLIENT_SECRET"))

if OAUTH_DEMO_MODE:
    # Option 3: Demo OAuth Authentication
    # No external credentials needed - simulates OAuth flow for testing
    from examples.full.auth import get_demo_oauth_backend

    auth_backend = get_demo_oauth_backend(get_session)
    logger.info(
        "Using Demo OAuth authentication",
        demo_email=os.environ.get("DEMO_OAUTH_EMAIL", "demo@example.com"),
        hint="Login via the 'demo' OAuth provider - accepts any code",
    )
elif GITHUB_OAUTH_CONFIGURED:
    # Option 2: OAuth Authentication (GitHub)
    # Requires GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET env vars
    from examples.full.auth import get_oauth_backend

    auth_backend = get_oauth_backend(get_session)
    logger.info(
        "Using GitHub OAuth authentication",
        hint="Login via GitHub - new users auto-created with VIEWER role",
    )
else:
    # Option 1: JWT Authentication (DEFAULT)
    # Username/password login with JWT tokens
    auth_backend = get_auth_backend(get_session)
    # Note: logger.info moved to startup to avoid logging before app is ready

# Legacy manual configuration (for reference):
# To explicitly use a specific backend, uncomment one of these and comment out
# the automatic detection above:
#
# auth_backend = get_auth_backend(get_session)  # JWT
# auth_backend = get_oauth_backend(get_session)  # GitHub OAuth
# auth_backend = get_demo_oauth_backend(get_session)  # Demo OAuth

# Configure admin plugin
admin_plugin = AdminPlugin(
    config=AdminConfig(
        title="Full Admin Demo",
        base_url="/admin",
        theme="dark",
        auth_backend=auth_backend,
        views=[UserAdmin, ArticleAdmin, TagAdmin, AppSettingsAdmin, SystemInfoAdmin],
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


@get("/")
async def index() -> dict[str, Any]:
    """Root endpoint with API information.

    Returns:
        API information and links including storage backend status.
    """
    # Determine authentication mode and credentials info
    if OAUTH_DEMO_MODE:
        auth_mode = "demo_oauth"
        credentials_info = {
            "demo_oauth": {
                "provider": "demo",
                "email": os.environ.get("DEMO_OAUTH_EMAIL", "demo@example.com"),
                "hint": "Use the 'demo' OAuth provider - any authorization code accepted",
            },
        }
    elif GITHUB_OAUTH_CONFIGURED:
        auth_mode = "github_oauth"
        credentials_info = {
            "github_oauth": {
                "provider": "github",
                "hint": "Login via GitHub - new users auto-created with VIEWER role",
            },
        }
    else:
        auth_mode = "jwt"
        credentials_info = {
            "admin": {"email": "admin@example.com", "password": "admin"},
            "editor": {"email": "editor@example.com", "password": "editor"},
            "viewer": {"email": "viewer@example.com", "password": "viewer"},
        }

    return {
        "app": "litestar-admin Full Demo",
        "version": "0.1.0",
        "admin_url": "/admin",
        "api_docs": "/schema",
        "authentication": {
            "mode": auth_mode,
            "credentials": credentials_info,
        },
        "storage": {
            "rate_limit": "redis" if redis_rate_limit_store else "in-memory",
            "sessions": "redis" if redis_session_store else "in-memory",
            "cache": "redis" if redis_cache else "disabled",
            "redis_url_configured": REDIS_URL is not None,
        },
    }


@get("/health")
async def health() -> dict[str, Any]:
    """Health check endpoint with storage backend status.

    Returns:
        Health status including Redis connectivity.
    """
    redis_healthy = False

    if redis_rate_limit_store:
        redis_healthy = await redis_rate_limit_store.ping()

    return {
        "status": "healthy",
        "storage": {
            "database": "connected",
            "redis": "connected" if redis_healthy else ("not configured" if not REDIS_URL else "disconnected"),
        },
    }


# Create the application
# litestar-admin's get_logger() automatically uses structlog when available
app = Litestar(
    route_handlers=[index, health],
    plugins=[admin_plugin, sqlalchemy_plugin],
    on_startup=[startup_handler],
    on_shutdown=[shutdown_handler],
    dependencies={"session_factory": Provide(provide_session_factory, sync_to_thread=False)},
    debug=True,
)
