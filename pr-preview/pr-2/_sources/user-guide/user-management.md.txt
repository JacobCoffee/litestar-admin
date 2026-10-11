# User Management

litestar-admin includes a built-in user management system for managing admin panel users, including user creation, role assignment, password management, and account activation.

## Overview

The user management system provides:

- **User CRUD**: Create, read, update, and delete admin users
- **Role Assignment**: Assign roles for RBAC (Viewer, Editor, Admin, Superadmin)
- **Password Management**: Secure password hashing, change, and reset
- **Account Status**: Activate and deactivate user accounts
- **Audit Logging**: Track all user management actions

## AdminUser Model

litestar-admin provides a base `AdminUser` model that you can use directly or extend:

```python
from litestar_admin.auth.models import AdminUser

# AdminUser includes:
# - id: Primary key
# - email: Unique email address
# - name: Display name
# - password_hash: Secure password hash
# - role: User role (viewer, editor, admin, superadmin)
# - is_active: Account status
# - created_at: Creation timestamp
# - updated_at: Last update timestamp
```

### Using Your Own User Model

If you have an existing user model, implement the `AdminUserProtocol`:

```python
from litestar_admin.auth import AdminUserProtocol

class User:
    """Your user model implementing AdminUserProtocol."""

    @property
    def id(self) -> int | str:
        return self._id

    @property
    def email(self) -> str:
        return self._email

    @property
    def roles(self) -> list[str]:
        """Return list of role names."""
        return [self.role.value]

    @property
    def permissions(self) -> list[str]:
        """Return list of permission strings."""
        return self._get_permissions_for_role(self.role)

    def verify_password(self, password: str) -> bool:
        """Verify a password against the stored hash."""
        return verify_password_hash(self.password_hash, password)
```

## User Management UI

Access the user management interface at `/admin/users` (requires appropriate permissions).

### User List

The user list displays:
- Email address
- Display name
- Role badge
- Account status (active/inactive)
- Creation date

Features:
- Search by email or name
- Sort by any column
- Paginated results
- Quick actions (edit, activate/deactivate)

### Create User

Create new admin users with:
- Email address (unique)
- Display name
- Password (minimum 8 characters)
- Role selection
- Initial activation status

### Edit User

Update existing users:
- Change email or name
- Update role assignment
- Modify activation status
- Reset password (optional)

### Password Management

#### Change Own Password

Users can change their own password through the profile page:

```http
POST /admin/api/auth/me/change-password
Content-Type: application/json

{
    "current_password": "old-password",
    "new_password": "new-secure-password"
}
```

#### Admin Password Reset

Admins can reset any user's password:

```http
POST /admin/api/users/{user_id}/change-password
Content-Type: application/json

{
    "new_password": "temporary-password"
}
```

#### Password Reset via Email

For self-service password reset:

```http
POST /admin/api/auth/forgot-password
Content-Type: application/json

{
    "email": "user@example.com"
}
```

```{note}
Email-based password reset requires configuring an email backend.
```

## API Endpoints

### List Users

```http
GET /admin/api/users?page=1&page_size=25&search=john
```

**Response:**
```json
{
    "items": [
        {
            "id": 1,
            "email": "john@example.com",
            "name": "John Doe",
            "role": "admin",
            "is_active": true,
            "created_at": "2024-01-15T10:30:00Z"
        }
    ],
    "total": 1,
    "page": 1,
    "page_size": 25
}
```

### Create User

```http
POST /admin/api/users
Content-Type: application/json

{
    "email": "newuser@example.com",
    "name": "New User",
    "password": "secure-password-123",
    "role": "editor",
    "is_active": true
}
```

### Get User

```http
GET /admin/api/users/{user_id}
```

### Update User

```http
PATCH /admin/api/users/{user_id}
Content-Type: application/json

{
    "name": "Updated Name",
    "role": "admin"
}
```

### Delete User

```http
DELETE /admin/api/users/{user_id}
```

### Activate User

```http
POST /admin/api/users/{user_id}/activate
```

### Deactivate User

```http
POST /admin/api/users/{user_id}/deactivate
```

## Role-Based Access

User management requires appropriate permissions:

| Action | Required Permission |
|--------|---------------------|
| View users | `users:read` |
| Create users | `users:create` |
| Edit users | `users:update` |
| Delete users | `users:delete` |
| Change passwords | `users:password` |
| Manage roles | `users:roles` |

### Default Role Permissions

| Role | Permissions |
|------|-------------|
| Viewer | Read-only access to allowed models |
| Editor | Create and edit records |
| Admin | Full CRUD + user management |
| Superadmin | Everything + system settings |

## Password Security

### Password Hashing

Passwords are hashed using bcrypt with a secure work factor:

```python
from litestar_admin.auth import hash_password, verify_password

# Hash a password
hashed = hash_password("user-password")

# Verify a password
is_valid = verify_password("user-password", hashed)
```

### Password Requirements

Configure password requirements in `AdminConfig`:

```python
from litestar_admin import AdminConfig

admin_config = AdminConfig(
    title="My Admin",
    password_min_length=12,
    password_require_uppercase=True,
    password_require_lowercase=True,
    password_require_digit=True,
    password_require_special=True,
)
```

### Secure Password Reset

Password reset tokens are:
- Cryptographically secure
- Time-limited (default: 1 hour)
- Single-use (invalidated after use)
- Stored hashed in the database

## Audit Logging

All user management actions are automatically logged:

```python
# Logged events:
# - User created
# - User updated (with changed fields)
# - User deleted
# - User activated/deactivated
# - Password changed
# - Role changed
# - Login attempts (success/failure)
```

View audit logs at `/admin/audit` or query programmatically:

```python
from litestar_admin.audit import get_audit_logs

logs = await get_audit_logs(
    action="user.created",
    actor_id=current_user.id,
    since=datetime.now() - timedelta(days=7),
)
```

## Integration Example

Complete example with user management enabled:

```python
from litestar import Litestar
from litestar_admin import AdminPlugin, AdminConfig
from litestar_admin.auth import JWTAuthBackend, JWTConfig

# Configure authentication
jwt_config = JWTConfig(
    secret_key="your-secret-key",
    token_expiry=3600,
)

async def load_user(identifier: str | int):
    """Load user from database."""
    return await user_repository.get_by_id_or_email(identifier)

auth_backend = JWTAuthBackend(
    config=jwt_config,
    user_loader=load_user,
)

# Create admin plugin
admin_plugin = AdminPlugin(
    config=AdminConfig(
        title="My Admin",
        auth_backend=auth_backend,
        # User management is automatically enabled
        # when auth_backend is configured
    )
)

app = Litestar(
    plugins=[admin_plugin],
)
```

## Customization

### Custom User View

Customize the user management view:

```python
from litestar_admin.views import UserManagementView

class CustomUserAdmin(UserManagementView):
    # Customize columns
    column_list = ["id", "email", "name", "role", "is_active", "last_login"]

    # Add search fields
    column_searchable_list = ["email", "name"]

    # Disable delete
    can_delete = False

    # Custom form fields
    form_excluded_columns = ["password_hash", "created_at", "updated_at"]
```

### Custom Password Validation

Add custom password validation:

```python
from litestar_admin.auth import PasswordValidator

class StrongPasswordValidator(PasswordValidator):
    def validate(self, password: str) -> list[str]:
        errors = super().validate(password)

        # Add custom rules
        if password.lower() in common_passwords:
            errors.append("Password is too common")

        if self.user_email and self.user_email.split("@")[0] in password.lower():
            errors.append("Password cannot contain your email username")

        return errors
```

### Custom User Creation Hook

Execute custom logic when users are created:

```python
class CustomUserAdmin(UserManagementView):
    @classmethod
    async def after_model_change(
        cls,
        record: User,
        *,
        is_create: bool,
    ) -> None:
        if is_create:
            # Send welcome email
            await send_welcome_email(record.email, record.name)

            # Create default settings
            await create_user_settings(record.id)

            # Log to external system
            await audit_service.log_user_created(record)
```

## See Also

- [Authentication](../authentication.md) - Authentication setup
- [Guards & RBAC](../guards.md) - Role-based access control
- [Audit Logging](audit.md) - Audit log configuration
