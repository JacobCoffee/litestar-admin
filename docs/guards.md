# Guards & RBAC

litestar-admin provides a comprehensive Role-Based Access Control (RBAC) system with permissions and guards. This guide covers how to use and customize access control.

## Overview

The RBAC system consists of:

- **Permissions**: Fine-grained access controls (e.g., `models:read`, `models:write`)
- **Roles**: Collections of permissions (e.g., `viewer`, `editor`, `admin`)
- **Guards**: Litestar guards that enforce permissions and roles on routes

## Permissions

Permissions follow a `resource:action` naming pattern for clarity.

### Built-in Permissions

```python
from litestar_admin.guards import Permission

# Model operations
Permission.MODELS_READ      # "models:read" - View/list records
Permission.MODELS_WRITE     # "models:write" - Create/update records
Permission.MODELS_DELETE    # "models:delete" - Delete records
Permission.MODELS_EXPORT    # "models:export" - Export data

# Dashboard
Permission.DASHBOARD_VIEW   # "dashboard:view" - View dashboard

# Administration
Permission.USERS_MANAGE     # "users:manage" - Manage admin users
Permission.SETTINGS_MANAGE  # "settings:manage" - Manage settings
Permission.AUDIT_VIEW       # "audit:view" - View audit logs
```

### Checking Permissions

```python
from litestar_admin.guards import user_has_permission, Permission

if user_has_permission(user, Permission.MODELS_DELETE):
    # User can delete records
    ...
```

## Roles

Roles group related permissions together. Each role inherits its own permissions.

### Built-in Roles

```python
from litestar_admin.guards import Role

Role.VIEWER     # Read-only access
Role.EDITOR     # Create and update records
Role.ADMIN      # Full model management + user management
Role.SUPERADMIN # Complete access to all features
```

### Role Permission Mappings

| Role        | Permissions                                                          |
|-------------|----------------------------------------------------------------------|
| VIEWER      | `models:read`, `dashboard:view`                                     |
| EDITOR      | All viewer permissions + `models:write`                              |
| ADMIN       | All editor permissions + `models:delete`, `models:export`, `users:manage`, `audit:view` |
| SUPERADMIN  | All permissions including `settings:manage`                          |

### Checking Roles

```python
from litestar_admin.guards import user_has_role, Role

if user_has_role(user, Role.ADMIN):
    # User is an admin
    ...
```

### Getting Role Permissions

```python
from litestar_admin.guards import get_permissions_for_role, Role

permissions = get_permissions_for_role(Role.EDITOR)
# Returns: {Permission.MODELS_READ, Permission.DASHBOARD_VIEW, Permission.MODELS_WRITE}
```

## Guards

Guards enforce permissions and roles on Litestar route handlers.

### Permission Guards

Require specific permission(s) to access a route:

```python
from litestar import get, post, delete
from litestar_admin.guards import require_permission, Permission


@get("/admin/models/{model}/records")
@guards([require_permission(Permission.MODELS_READ)])
async def list_records(model: str) -> list:
    ...


@post("/admin/models/{model}/records")
@guards([require_permission(Permission.MODELS_WRITE)])
async def create_record(model: str, data: dict) -> dict:
    ...


@delete("/admin/models/{model}/records/{id}")
@guards([require_permission(Permission.MODELS_DELETE)])
async def delete_record(model: str, id: int) -> None:
    ...
```

### Multiple Permissions

Require ALL specified permissions (AND logic):

```python
from litestar_admin.guards import require_permission, Permission


@get("/admin/export")
@guards([require_permission(Permission.MODELS_READ, Permission.MODELS_EXPORT)])
async def export_data() -> bytes:
    # User must have BOTH permissions
    ...
```

### Role Guards

Require specific role(s) to access a route:

```python
from litestar import get
from litestar_admin.guards import require_role, Role


@get("/admin/settings")
@guards([require_role(Role.ADMIN)])
async def get_settings() -> dict:
    ...
```

### Multiple Roles

Require ANY of the specified roles (OR logic):

```python
from litestar_admin.guards import require_role, Role


@get("/admin/dashboard")
@guards([require_role(Role.ADMIN, Role.SUPERADMIN)])
async def admin_dashboard() -> dict:
    # User needs EITHER admin OR superadmin role
    ...
```

### Using Guard Classes Directly

For more control, use the guard classes directly:

```python
from litestar import get
from litestar_admin.guards import PermissionGuard, RoleGuard, Permission, Role


@get("/admin/data", guards=[PermissionGuard(Permission.MODELS_READ)])
async def get_data() -> dict:
    ...


@get("/admin/settings", guards=[RoleGuard(Role.SUPERADMIN)])
async def get_settings() -> dict:
    ...
```

## Guard Error Responses

When a guard denies access, it raises `NotAuthorizedException`:

**No authentication:**
```json
{
    "status_code": 401,
    "detail": "Authentication required"
}
```

**Missing permission:**
```json
{
    "status_code": 401,
    "detail": "Permission 'models:delete' required"
}
```

**Missing role:**
```json
{
    "status_code": 401,
    "detail": "One of roles 'admin', 'superadmin' required"
}
```

## User Assignment

Permissions and roles are assigned to users through the `AdminUser` protocol:

```python
class User:
    @property
    def roles(self) -> list[str]:
        """Return role names assigned to this user."""
        return ["editor"]  # User has editor role

    @property
    def permissions(self) -> list[str]:
        """Return direct permissions (in addition to role-based)."""
        return ["models:export"]  # Extra permission beyond role
```

### Role-Based Permissions

Users inherit all permissions from their assigned roles:

```python
class User:
    @property
    def roles(self) -> list[str]:
        return ["editor"]

    @property
    def permissions(self) -> list[str]:
        return []  # No direct permissions

# This user has:
# - models:read (from editor role)
# - dashboard:view (from editor role)
# - models:write (from editor role)
```

### Direct Permissions

Assign permissions directly for fine-grained control:

```python
class User:
    @property
    def roles(self) -> list[str]:
        return ["viewer"]

    @property
    def permissions(self) -> list[str]:
        return ["models:export"]  # Extra permission beyond viewer role

# This user has:
# - models:read (from viewer role)
# - dashboard:view (from viewer role)
# - models:export (direct permission)
```

### Multiple Roles

Users can have multiple roles:

```python
class User:
    @property
    def roles(self) -> list[str]:
        return ["viewer", "editor"]

    @property
    def permissions(self) -> list[str]:
        return []

# This user has union of all role permissions
```

## Custom Permission Checking

For complex authorization logic, implement custom checking:

```python
from litestar_admin.guards import Permission, user_has_permission


async def can_edit_record(user, record) -> bool:
    """Check if user can edit a specific record."""
    # Must have write permission
    if not user_has_permission(user, Permission.MODELS_WRITE):
        return False

    # Additional business logic
    if record.owner_id == user.id:
        return True

    # Admins can edit anything
    return "admin" in user.roles
```

## Combining Guards with Model Views

Use guards in conjunction with model view access control:

```python
from litestar_admin import ModelView
from litestar_admin.guards import Permission, user_has_permission


class OrderAdmin(ModelView, model=Order):
    # Static permissions
    can_create = True
    can_edit = True
    can_delete = False  # Disable delete for all

    @classmethod
    async def is_accessible(cls, connection) -> bool:
        """Only users with models:read can access."""
        user = getattr(connection, "user", None)
        if user is None:
            return False
        return user_has_permission(user, Permission.MODELS_READ)

    @classmethod
    async def can_delete_record(cls, connection, record) -> bool:
        """Only admins can delete cancelled orders."""
        user = getattr(connection, "user", None)
        if user is None:
            return False
        # Only allow deleting cancelled orders
        if record.status != "cancelled":
            return False
        return "admin" in user.roles
```

## Applying Guards to Admin Routes

Guards are automatically applied to admin API routes based on your auth configuration. You can also add custom guards:

```python
from litestar import Router
from litestar_admin.guards import require_role, Role


# Create a custom admin router with additional guards
admin_router = Router(
    path="/admin/custom",
    route_handlers=[...],
    guards=[require_role(Role.ADMIN)],  # Extra guard for this router
)
```

## Example: Multi-Tenant Authorization

Here's an example of implementing tenant-based authorization:

```python
from litestar_admin import ModelView
from litestar_admin.guards import Permission, user_has_permission


class TenantModelView(ModelView):
    """Base view with tenant isolation."""

    @classmethod
    async def is_accessible(cls, connection) -> bool:
        """Check tenant access."""
        user = getattr(connection, "user", None)
        if user is None:
            return False

        # Superadmins can access any tenant
        if "superadmin" in user.roles:
            return True

        # Regular users can only access their tenant
        tenant_id = connection.headers.get("X-Tenant-ID")
        return str(user.tenant_id) == tenant_id

    @classmethod
    async def can_delete_record(cls, connection, record) -> bool:
        """Only allow deleting own tenant's records."""
        user = getattr(connection, "user", None)
        if user is None:
            return False

        # Must have delete permission
        if not user_has_permission(user, Permission.MODELS_DELETE):
            return False

        # Check tenant ownership
        return record.tenant_id == user.tenant_id
```

## Best Practices

1. **Use Roles for General Access**
   Assign roles rather than individual permissions when possible.

2. **Use Permissions for Fine-Grained Control**
   Add direct permissions only when role-based access is insufficient.

3. **Implement Defense in Depth**
   Use guards on routes AND access control in model views.

4. **Log Access Denials**
   Use the audit system to track authorization failures.

5. **Test Authorization**
   Write tests for all permission scenarios.

```python
async def test_viewer_cannot_delete():
    """Test that viewers cannot delete records."""
    viewer_user = User(roles=["viewer"])

    with pytest.raises(NotAuthorizedException):
        await delete_record(user=viewer_user, record_id=1)
```
