# litestar-admin

Modern admin panel framework for Litestar applications with a Cloudflare-inspired UI.

**litestar-admin** provides a production-ready admin interface for managing SQLAlchemy models in Litestar applications, featuring full CRUD operations, RBAC authorization, audit logging, and a sleek dark theme.

## Installation

`````{tab-set}
````{tab-item} uv
```bash
# Base installation
uv add litestar-admin

# With JWT authentication
uv add litestar-admin[jwt]

# With OAuth2 support
uv add litestar-admin[oauth]

# Everything
uv add litestar-admin[all]
```
````

````{tab-item} pip
```bash
# Base installation
pip install litestar-admin

# With JWT authentication
pip install "litestar-admin[jwt]"

# With OAuth2 support
pip install "litestar-admin[oauth]"

# Everything
pip install "litestar-admin[all]"
```
````

````{tab-item} pdm
```bash
# Base installation
pdm add litestar-admin

# With JWT authentication
pdm add litestar-admin[jwt]

# With OAuth2 support
pdm add litestar-admin[oauth]

# Everything
pdm add litestar-admin[all]
```
````

````{tab-item} poetry
```bash
# Base installation
poetry add litestar-admin

# With JWT authentication
poetry add litestar-admin[jwt]

# With OAuth2 support
poetry add litestar-admin[oauth]

# Everything
poetry add litestar-admin[all]
```
````
`````

---

::::{grid} 1 2 2 3
:gutter: 3

:::{grid-item-card} Getting Started
:link: getting-started
:link-type: doc

New to litestar-admin? Start here for installation and your first admin panel.
:::

:::{grid-item-card} Configuration
:link: configuration
:link-type: doc

Learn how to configure themes, branding, authentication, and behavior.
:::

:::{grid-item-card} Model Views
:link: model-views
:link-type: doc

Customize how your models appear with column lists, filters, and form options.
:::

:::{grid-item-card} Custom Views & Embeds
:link: user-guide/custom-views
:link-type: doc

Create custom views, actions, pages, and embed external dashboards.
:::

:::{grid-item-card} File Uploads
:link: user-guide/file-uploads
:link-type: doc

Add file upload support with drag-drop, previews, and thumbnails.
:::

:::{grid-item-card} User Management
:link: user-guide/user-management
:link-type: doc

Manage admin users, roles, passwords, and account status.
:::

:::{grid-item-card} Authentication
:link: authentication
:link-type: doc

Set up JWT, OAuth2, or custom authentication backends for your admin panel.
:::

:::{grid-item-card} Guards & RBAC
:link: guards
:link-type: doc

Implement role-based access control with granular permissions.
:::

:::{grid-item-card} API Reference
:link: api/index
:link-type: doc

Complete API documentation for all public classes and functions.
:::
::::

## Quick Start

```python
from litestar import Litestar
from litestar_admin import AdminPlugin, AdminConfig, ModelView
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]


class UserAdmin(ModelView, model=User):
    column_list = ["id", "email", "name"]
    column_searchable_list = ["email", "name"]
    can_create = True
    can_edit = True
    can_delete = True


app = Litestar(
    plugins=[
        AdminPlugin(
            config=AdminConfig(
                title="My Admin",
                views=[UserAdmin],
            )
        )
    ]
)
```

## Features

- **Cloudflare Dashboard-inspired UI** - Modern dark theme with clean card layouts
- **Full CRUD Operations** - Create, read, update, delete with bulk actions
- **RBAC Authorization** - Role-based access control with granular permissions
- **Audit Logging** - Track all admin actions for compliance
- **SQLAlchemy Integration** - Works with SQLAlchemy 2.x and Advanced-Alchemy
- **Auto-discovery** - Automatically discovers and registers models
- **JWT & OAuth2 Authentication** - Flexible, pluggable auth backends
- **Static Export Frontend** - Next.js frontend with no runtime Node.js required

```{toctree}
:maxdepth: 2
:hidden:
:caption: Learn

getting-started
configuration
model-views
user-guide/custom-views
user-guide/file-uploads
user-guide/storage
user-guide/user-management
authentication
guards
deployment
```

```{toctree}
:maxdepth: 2
:hidden:
:caption: Reference

api/index
changelog
```

```{toctree}
:hidden:
:caption: Project

GitHub <https://github.com/JacobCoffee/litestar-admin>
Discord <https://discord.gg/litestar-919193495116337154>
```

## Indices and tables

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`
