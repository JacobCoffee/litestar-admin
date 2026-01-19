# litestar-admin

**Modern admin panel framework for Litestar applications.**

litestar-admin provides a production-ready admin interface for managing SQLAlchemy models in Litestar applications, featuring a Cloudflare-inspired UI with full CRUD operations, RBAC authorization, and audit logging.

## Features

- **Cloudflare Dashboard-inspired UI** - Modern dark theme with clean card layouts
- **Full CRUD Operations** - Create, read, update, delete with bulk actions
- **RBAC Authorization** - Role-based access control with granular permissions
- **Audit Logging** - Track all admin actions for compliance
- **SQLAlchemy Integration** - Works with SQLAlchemy 2.x and Advanced-Alchemy
- **Auto-discovery** - Automatically discovers and registers models
- **JWT & OAuth2 Authentication** - Flexible, pluggable auth backends
- **Static Export Frontend** - Next.js frontend with no runtime Node.js required

## Quick Start

```python
from litestar import Litestar
from litestar_admin import AdminPlugin, AdminConfig, ModelView


class UserAdmin(ModelView, model=User):
    column_list = ["id", "email", "name"]


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

## Installation

```bash
pip install litestar-admin
```

Or with uv:

```bash
uv add litestar-admin
```

For additional features:

```bash
# JWT authentication
pip install "litestar-admin[jwt]"

# All optional dependencies
pip install "litestar-admin[all]"
```

## Documentation

```{toctree}
:maxdepth: 2
:caption: User Guide

getting-started
configuration
model-views
authentication
guards
deployment
```

```{toctree}
:maxdepth: 2
:caption: Reference

api/index
changelog
```

## Indices and tables

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`
