# Getting Started

This guide will get you up and running with litestar-admin in just a few minutes.

## Prerequisites

Before you begin, make sure you have:

- Python 3.10 or higher
- An existing Litestar application (or you can create a new one)
- SQLAlchemy 2.x models (async support required)

## Installation

Install litestar-admin using pip:

```bash
pip install litestar-admin
```

Or with uv (recommended):

```bash
uv add litestar-admin
```

### Optional Dependencies

litestar-admin has several optional dependencies for additional features:

```bash
# JWT authentication support
pip install "litestar-admin[jwt]"

# OAuth integration (requires litestar-oauth)
pip install "litestar-admin[oauth]"

# sqladmin compatibility layer
pip install "litestar-admin[sqladmin]"

# All optional dependencies
pip install "litestar-admin[all]"
```

## Quick Start

Here's a minimal example to get an admin panel running with your Litestar application.

### Step 1: Define Your SQLAlchemy Models

If you don't already have models, create them:

```python
# models.py
from __future__ import annotations

from datetime import datetime
from typing import Optional

from advanced_alchemy.base import CommonTableAttributes, orm_registry
from sqlalchemy import String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(CommonTableAttributes, DeclarativeBase):
    """Base class for all models."""
    registry = orm_registry


class User(Base):
    """User model."""

    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
```

### Step 2: Create Model Views

Model views define how your models appear in the admin panel:

```python
# admin.py
from litestar_admin import ModelView
from models import User


class UserAdmin(ModelView, model=User):
    """Admin view for User model."""

    # Columns to display in the list view
    column_list = ["id", "email", "name", "is_active", "created_at"]

    # Columns that can be searched
    column_searchable_list = ["email", "name"]

    # Columns that can be sorted
    column_sortable_list = ["id", "email", "created_at"]

    # Default sort order
    column_default_sort = ("created_at", "desc")

    # Permissions
    can_create = True
    can_edit = True
    can_delete = True
```

### Step 3: Configure the Admin Plugin

Add the admin plugin to your Litestar application:

```python
# app.py
from litestar import Litestar
from litestar.plugins.sqlalchemy import SQLAlchemyPlugin, SQLAlchemyConfig
from litestar_admin import AdminPlugin, AdminConfig

from models import Base
from admin import UserAdmin


# Database configuration
db_config = SQLAlchemyConfig(
    connection_string="sqlite+aiosqlite:///app.db",
    create_all=True,
)


# Admin configuration
admin_config = AdminConfig(
    title="My Admin Panel",
    base_url="/admin",
    views=[UserAdmin],
)


# Create the application
app = Litestar(
    route_handlers=[],  # Your route handlers here
    plugins=[
        SQLAlchemyPlugin(config=db_config),
        AdminPlugin(config=admin_config),
    ],
)
```

### Step 4: Run Your Application

Start your application with uvicorn:

```bash
uvicorn app:app --reload
```

Navigate to `http://localhost:8000/admin` in your browser to see your admin panel.

## What's Next?

Now that you have a basic admin panel running, explore these topics:

- {doc}`configuration` - Customize your admin panel settings
- {doc}`model-views` - Learn all the ways to customize model views
- {doc}`authentication` - Secure your admin panel with authentication
- {doc}`guards` - Implement role-based access control
- {doc}`deployment` - Deploy to production

## Complete Example

Here's a complete, working example you can copy and run:

```python
"""Complete litestar-admin example."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from advanced_alchemy.base import CommonTableAttributes, orm_registry
from litestar import Litestar
from litestar.plugins.sqlalchemy import SQLAlchemyConfig, SQLAlchemyPlugin
from sqlalchemy import String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from litestar_admin import AdminConfig, AdminPlugin, ModelView


# Models
class Base(CommonTableAttributes, DeclarativeBase):
    registry = orm_registry


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class Post(Base):
    __tablename__ = "post"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    published: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


# Admin Views
class UserAdmin(ModelView, model=User):
    column_list = ["id", "email", "name", "is_active", "created_at"]
    column_searchable_list = ["email", "name"]
    column_sortable_list = ["id", "email", "created_at"]
    can_delete = False  # Prevent accidental deletion


class PostAdmin(ModelView, model=Post):
    column_list = ["id", "title", "published", "created_at"]
    column_searchable_list = ["title", "content"]
    column_sortable_list = ["id", "title", "created_at"]
    column_default_sort = ("created_at", "desc")


# Application
app = Litestar(
    plugins=[
        SQLAlchemyPlugin(
            config=SQLAlchemyConfig(
                connection_string="sqlite+aiosqlite:///example.db",
                create_all=True,
            ),
        ),
        AdminPlugin(
            config=AdminConfig(
                title="Blog Admin",
                views=[UserAdmin, PostAdmin],
            ),
        ),
    ],
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
```

Save this as `app.py` and run it with `python app.py` or `uvicorn app:app --reload`.

## Troubleshooting

### Admin panel shows blank page

Make sure the frontend static files are included in your installation. If you installed from source, run `make frontend` to build the frontend.

### Models not appearing

Check that your model views are registered in the `AdminConfig.views` list, or enable `auto_discover=True` in the config.

### Database errors

Ensure your database connection string uses an async driver (e.g., `aiosqlite` for SQLite, `asyncpg` for PostgreSQL).

```python
# Correct - uses async driver
connection_string="sqlite+aiosqlite:///app.db"
connection_string="postgresql+asyncpg://user:pass@localhost/db"

# Incorrect - sync drivers won't work
connection_string="sqlite:///app.db"
connection_string="postgresql://user:pass@localhost/db"
```

### Import errors

Make sure all dependencies are installed:

```bash
pip install litestar advanced-alchemy sqlalchemy[asyncio] aiosqlite
```
