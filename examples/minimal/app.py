"""Minimal litestar-admin example with default configuration.

This example demonstrates the simplest possible setup for litestar-admin:
- A single SQLAlchemy model (User)
- Basic ModelView with column configuration
- AdminPlugin with minimal configuration
- In-memory SQLite database for easy testing

Run with:
    uvicorn examples.minimal.app:app --reload

Then visit: http://localhost:8000/admin
"""

from __future__ import annotations

from datetime import datetime

from advanced_alchemy.extensions.litestar import SQLAlchemyAsyncConfig, SQLAlchemyPlugin
from litestar import Litestar
from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from litestar_admin import AdminConfig, AdminPlugin, ModelView

# =============================================================================
# Database Models
# =============================================================================


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


class User(Base):
    """Simple user model for demonstration.

    Attributes:
        id: Primary key, auto-generated.
        email: User's email address, must be unique.
        name: User's display name.
        created_at: Timestamp when the user was created.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


# =============================================================================
# Admin Views
# =============================================================================


class UserAdmin(ModelView, model=User):
    """Admin view for the User model.

    This view configures how Users are displayed and managed
    in the admin panel.
    """

    # Columns to display in the list view
    column_list = ["id", "email", "name", "created_at"]

    # Columns that can be searched
    column_searchable_list = ["email", "name"]

    # Columns that can be sorted
    column_sortable_list = ["id", "email", "name", "created_at"]

    # Default sort order
    column_default_sort = ("created_at", "desc")

    # Permissions
    can_create = True
    can_edit = True
    can_delete = True
    can_export = True


# =============================================================================
# Database Configuration
# =============================================================================

# Use aiosqlite for async SQLite with in-memory database
db_config = SQLAlchemyAsyncConfig(
    connection_string="sqlite+aiosqlite:///:memory:",
    metadata=Base.metadata,
    create_all=True,  # Auto-create tables on startup
)


# =============================================================================
# Application Setup
# =============================================================================

# Configure the admin plugin
admin_config = AdminConfig(
    title="Minimal Admin",
    base_url="/admin",
    views=[UserAdmin],
    auto_discover=False,  # Disable auto-discovery since we explicitly register views
)

# Create the Litestar application
app = Litestar(
    route_handlers=[],
    plugins=[
        SQLAlchemyPlugin(config=db_config),
        AdminPlugin(config=admin_config),
    ],
    debug=True,
)
