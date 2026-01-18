# litestar-admin

[![CI](https://github.com/JacobCoffee/litestar-admin/actions/workflows/ci.yml/badge.svg)](https://github.com/JacobCoffee/litestar-admin/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/litestar-admin.svg)](https://badge.fury.io/py/litestar-admin)
[![Python versions](https://img.shields.io/pypi/pyversions/litestar-admin.svg)](https://pypi.org/project/litestar-admin/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Modern admin panel framework for Litestar applications with a Cloudflare-inspired UI.**

litestar-admin provides a production-ready admin interface for managing SQLAlchemy models in Litestar applications, featuring:

- **Cloudflare Dashboard-inspired UI** - Modern dark theme with clean card layouts
- **Full CRUD Operations** - Create, read, update, delete with bulk actions
- **RBAC Authorization** - Role-based access control with granular permissions
- **Audit Logging** - Track all admin actions for compliance
- **SQLAlchemy Integration** - Works with SQLAlchemy 2.x and Advanced-Alchemy
- **Auto-discovery** - Automatically discovers and registers models
- **JWT & OAuth2 Authentication** - Flexible, pluggable auth backends
- **Static Export Frontend** - Next.js frontend with no runtime Node.js required

## Installation

```bash
# Basic installation
pip install litestar-admin

# With JWT authentication
pip install litestar-admin[jwt]

# With OAuth support
pip install litestar-admin[oauth]

# With sqladmin bridge
pip install litestar-admin[sqladmin]

# All extras
pip install litestar-admin[all]
```

## Quick Start

```python
from litestar import Litestar
from litestar_admin import AdminPlugin, AdminConfig, ModelView
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Define your models
class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]

# Create admin views
class UserAdmin(ModelView, model=User):
    column_list = ["id", "email", "name"]
    column_searchable_list = ["email", "name"]
    can_delete = False  # Disable deletion

# Create the app
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

## Configuration

```python
from litestar_admin import AdminConfig
from litestar_admin.auth import JWTAuthBackend

config = AdminConfig(
    # Basic settings
    title="My Admin Panel",
    base_url="/admin",
    theme="dark",  # or "light"

    # Authentication
    auth_backend=JWTAuthBackend(
        secret_key="your-secret-key",
        algorithm="HS256",
    ),

    # Model views
    views=[UserAdmin, PostAdmin],
    auto_discover=True,  # Auto-discover models

    # Rate limiting
    rate_limit_enabled=True,
    rate_limit_requests=100,
    rate_limit_window_seconds=60,
)
```

## Model Views

```python
from litestar_admin import ModelView

class UserAdmin(ModelView, model=User):
    # Display settings
    name = "User"
    name_plural = "Users"
    icon = "user"
    category = "User Management"

    # Column configuration
    column_list = ["id", "email", "name", "created_at"]
    column_exclude_list = ["password_hash"]
    column_searchable_list = ["email", "name"]
    column_sortable_list = ["id", "email", "created_at"]
    column_default_sort = ("created_at", "desc")

    # Form configuration
    form_columns = ["email", "name"]
    form_excluded_columns = ["id", "created_at"]

    # Permissions
    can_create = True
    can_edit = True
    can_delete = False
    can_export = True

    # Pagination
    page_size = 25
    page_size_options = [10, 25, 50, 100]

    # Custom access control
    async def is_accessible(self, connection) -> bool:
        user = connection.user
        return user and user.is_admin
```

## RBAC Guards

```python
from litestar_admin.guards import require_permission, Permission

@get("/admin/users", guards=[require_permission(Permission.MODELS_READ)])
async def list_users() -> list[User]:
    ...

@post("/admin/users", guards=[require_permission(Permission.MODELS_WRITE)])
async def create_user(data: UserCreate) -> User:
    ...
```

## Development

```bash
# Clone the repository
git clone https://github.com/JacobCoffee/litestar-admin.git
cd litestar-admin

# Install development dependencies
make dev

# Run tests
make test

# Run linting
make lint

# Build frontend
make frontend

# Build documentation
make docs
```

## Documentation

Full documentation is available at [jacobcoffee.github.io/litestar-admin](https://jacobcoffee.github.io/litestar-admin).

## Related Projects

- [litestar](https://github.com/litestar-org/litestar) - The ASGI framework
- [advanced-alchemy](https://github.com/jolt-org/advanced-alchemy) - SQLAlchemy toolkit
- [sqladmin-litestar-plugin](https://github.com/peterschutt/sqladmin-litestar-plugin) - SQLAdmin bridge

## License

MIT License - see [LICENSE](LICENSE) for details.
