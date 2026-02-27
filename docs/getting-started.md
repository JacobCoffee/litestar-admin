# Getting Started

## Prerequisites

- Python 3.10+
- SQLAlchemy 2.x models with an async driver (`aiosqlite`, `asyncpg`, etc.)
- A Litestar application (or a new one — we'll build one here)

## Installation

```bash
pip install litestar-admin
```

Or with uv:

```bash
uv add litestar-admin
```

Optional extras:

```bash
pip install "litestar-admin[jwt]"     # JWT authentication
pip install "litestar-admin[oauth]"   # OAuth integration
pip install "litestar-admin[sqladmin]" # sqladmin compatibility layer
pip install "litestar-admin[all]"     # Everything
```

## The Fastest Path: Auto-Discovery

Define your SQLAlchemy models. Add the plugin. Done.

```python
# app.py
from litestar import Litestar
from litestar_admin import AdminPlugin, AdminConfig
from advanced_alchemy.extensions.litestar import SQLAlchemyAsyncConfig, SQLAlchemyPlugin
from sqlalchemy import String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(100))


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)


db_config = SQLAlchemyAsyncConfig(
    connection_string="sqlite+aiosqlite:///app.db",
    metadata=Base.metadata,
    create_all=True,
)

app = Litestar(
    plugins=[
        SQLAlchemyPlugin(config=db_config),
        AdminPlugin(config=AdminConfig(title="My Admin")),
    ],
)
```

Run it:

```bash
uvicorn app:app --reload
```

Open `http://localhost:8000/admin`. Both `User` and `Post` show up with full CRUD — columns derived from the table schema, string columns searchable, everything sortable.

No `ModelView` subclasses. No column lists. The plugin finds your `DeclarativeBase`, walks the model registry, and generates sensible defaults.

## Customizing Specific Models

Auto-discovery is great for getting started, but most apps need some customization. Create a `ModelView` subclass for any model where you want to control what's shown, who can do what, or how forms behave.

```python
from litestar_admin import ModelView


class UserAdmin(ModelView, model=User):
    column_list = ["id", "email", "name"]
    column_searchable_list = ["email", "name"]
    column_default_sort = ("id", "desc")

    can_create = True
    can_edit = True
    can_delete = False  # no accidental deletions
```

Register it in the config:

```python
AdminConfig(
    title="My Admin",
    views=[UserAdmin],
)
```

Auto-discovery still runs for everything else. `Post` gets a generated view; `User` uses your custom one.

## Turning Off Auto-Discovery

If you want full control and only want models you've explicitly registered:

```python
AdminConfig(
    title="My Admin",
    views=[UserAdmin, PostAdmin],
    auto_discover=False,
)
```

## How Auto-Discovery Finds Your Models

The plugin looks for `DeclarativeBase` subclasses in a few places, in order:

1. `app.state` — common attribute names like `db_base`, `base`, `Base`
2. Advanced-Alchemy plugin config (if you're using `SQLAlchemyPlugin`)
3. SQLAlchemy plugin config
4. Fallback: scans all `DeclarativeBase` subclasses in the Python runtime

From each base, it pulls every mapped model that has a `__tablename__` and isn't abstract. For each model without an explicit `ModelView`, it generates one with:

- All columns visible and sortable
- String/text columns marked searchable
- Auto-increment primary keys and managed timestamps excluded from forms
- Default sort on `id` descending
- Smart icons for common model names (User → user icon, Product → package icon, etc.)
- Advanced-Alchemy model detection for UUID primary keys and audit columns

## What's Next

- {doc}`configuration` — All `AdminConfig` options
- {doc}`model-views` — Full `ModelView` API (column config, form widgets, lifecycle hooks, file uploads)
- {doc}`authentication` — JWT and session auth backends
- {doc}`guards` — RBAC and permission guards
- {doc}`deployment` — Production deployment

## Troubleshooting

### Admin panel shows a blank page

The frontend static files might be missing. If you installed from source, run `make frontend` to build them.

### Database errors

The connection string needs an async driver:

```python
# Right
"sqlite+aiosqlite:///app.db"
"postgresql+asyncpg://user:pass@localhost/db"

# Wrong — sync drivers won't work
"sqlite:///app.db"
"postgresql://user:pass@localhost/db"
```

### Import errors

Make sure the async driver is installed:

```bash
pip install aiosqlite   # for SQLite
pip install asyncpg     # for PostgreSQL
```
