# Model Views

Model views define how your SQLAlchemy models are displayed and managed in the admin panel. This guide covers all customization options and advanced techniques.

## Basic Usage

There are two ways to create model views:

### Using ModelView (Recommended)

The `ModelView` class allows you to specify the model as a class parameter:

```python
from litestar_admin import ModelView
from myapp.models import User


class UserAdmin(ModelView, model=User):
    column_list = ["id", "email", "name"]
```

### Using BaseModelView

Alternatively, use `BaseModelView` and set the model as a class attribute:

```python
from litestar_admin import BaseModelView
from myapp.models import User


class UserAdmin(BaseModelView):
    model = User
    column_list = ["id", "email", "name"]
```

Both approaches are functionally equivalent.

## Display Configuration

### Model Naming

#### name

Display name for the model in the sidebar and page headers. Defaults to the model class name.

```python
class UserAdmin(ModelView, model=User):
    name = "User Account"
```

#### name_plural

Plural display name. Defaults to `name + "s"`.

```python
class PersonAdmin(ModelView, model=Person):
    name = "Person"
    name_plural = "People"
```

#### icon

Icon name for the sidebar. Uses FontAwesome icon names.

```python
class UserAdmin(ModelView, model=User):
    icon = "user"

class OrderAdmin(ModelView, model=Order):
    icon = "shopping-cart"

class SettingsAdmin(ModelView, model=Settings):
    icon = "cog"
```

#### category

Group models under a category in the sidebar.

```python
class UserAdmin(ModelView, model=User):
    category = "Users & Access"

class RoleAdmin(ModelView, model=Role):
    category = "Users & Access"

class ProductAdmin(ModelView, model=Product):
    category = "Store"

class OrderAdmin(ModelView, model=Order):
    category = "Store"
```

Models with the same category will be grouped together in the sidebar.

## Column Configuration

### List View Columns

#### column_list

Specify which columns to display in the list view.

```python
class UserAdmin(ModelView, model=User):
    # Only these columns will be shown
    column_list = ["id", "email", "name", "created_at"]
```

If not specified, all columns are shown.

#### column_exclude_list

Columns to exclude from the list view.

```python
class UserAdmin(ModelView, model=User):
    # Show all columns except these
    column_exclude_list = ["password_hash", "internal_notes"]
```

### Search and Sort

#### column_searchable_list

Columns that can be searched via the search box.

```python
class UserAdmin(ModelView, model=User):
    column_searchable_list = ["email", "name", "phone"]
```

Search performs case-insensitive partial matching on string columns.

#### column_sortable_list

Columns that can be sorted by clicking the column header.

```python
class UserAdmin(ModelView, model=User):
    column_sortable_list = ["id", "email", "created_at"]
```

If not specified, all columns are sortable by default.

#### column_default_sort

Default sort order when loading the list view.

```python
class UserAdmin(ModelView, model=User):
    # Sort by created_at descending (newest first)
    column_default_sort = ("created_at", "desc")

class OrderAdmin(ModelView, model=Order):
    # Sort by id ascending
    column_default_sort = ("id", "asc")
```

## Form Configuration

### form_columns

Columns to include in create/edit forms.

```python
class UserAdmin(ModelView, model=User):
    form_columns = ["email", "name", "bio", "is_active"]
```

If not specified, all non-primary-key columns are included.

### form_excluded_columns

Columns to exclude from forms.

```python
class UserAdmin(ModelView, model=User):
    # Exclude auto-generated and sensitive fields
    form_excluded_columns = ["id", "created_at", "updated_at", "password_hash"]
```

## Permissions

Control what actions are allowed for each model.

### can_create

Allow creating new records.

```python
class LogAdmin(ModelView, model=AuditLog):
    can_create = False  # Logs are system-generated only
```

### can_edit

Allow editing existing records.

```python
class TransactionAdmin(ModelView, model=Transaction):
    can_edit = False  # Transactions are immutable
```

### can_delete

Allow deleting records.

```python
class UserAdmin(ModelView, model=User):
    can_delete = False  # Prevent accidental user deletion
```

### can_view_details

Allow viewing detailed record information.

```python
class SecretAdmin(ModelView, model=Secret):
    can_view_details = False  # Hide detailed view
```

### can_export

Allow exporting records to CSV/JSON.

```python
class SensitiveDataAdmin(ModelView, model=SensitiveData):
    can_export = False  # Prevent data export
```

## Pagination

### page_size

Default number of records per page.

```python
class UserAdmin(ModelView, model=User):
    page_size = 50  # Default is 25
```

### page_size_options

Available page size options in the dropdown.

```python
class UserAdmin(ModelView, model=User):
    page_size_options = [10, 25, 50, 100, 200]
```

## Access Control Hooks

Override these methods for dynamic access control based on the current request.

### is_accessible

Control whether the view is accessible at all.

```python
class AdminSettingsAdmin(ModelView, model=AdminSettings):
    @classmethod
    async def is_accessible(cls, connection: ASGIConnection) -> bool:
        # Only superadmins can access
        user = getattr(connection, "user", None)
        return user is not None and "superadmin" in user.roles
```

### can_create_record

Control whether records can be created.

```python
class PostAdmin(ModelView, model=Post):
    @classmethod
    async def can_create_record(cls, connection: ASGIConnection) -> bool:
        user = getattr(connection, "user", None)
        if user is None:
            return False
        # Only editors can create posts
        return "editor" in user.roles
```

### can_edit_record

Control whether a specific record can be edited.

```python
class PostAdmin(ModelView, model=Post):
    @classmethod
    async def can_edit_record(
        cls,
        connection: ASGIConnection,
        record: Post,
    ) -> bool:
        user = getattr(connection, "user", None)
        if user is None:
            return False
        # Users can only edit their own posts
        return record.author_id == user.id or "admin" in user.roles
```

### can_delete_record

Control whether a specific record can be deleted.

```python
class UserAdmin(ModelView, model=User):
    @classmethod
    async def can_delete_record(
        cls,
        connection: ASGIConnection,
        record: User,
    ) -> bool:
        user = getattr(connection, "user", None)
        if user is None:
            return False
        # Cannot delete yourself
        return record.id != user.id
```

## Lifecycle Hooks

Override these methods to add custom logic during CRUD operations.

### on_model_change

Called before creating or updating a record. Use this for validation or data transformation.

```python
class UserAdmin(ModelView, model=User):
    @classmethod
    async def on_model_change(
        cls,
        data: dict[str, Any],
        record: User | None,
        *,
        is_create: bool,
    ) -> dict[str, Any]:
        # Hash password before saving
        if "password" in data:
            data["password_hash"] = hash_password(data.pop("password"))

        # Set created_by on create
        if is_create:
            data["created_by"] = "admin"

        # Set updated_at on update
        if not is_create:
            data["updated_at"] = datetime.utcnow()

        return data
```

### after_model_change

Called after creating or updating a record. Use this for side effects.

```python
class UserAdmin(ModelView, model=User):
    @classmethod
    async def after_model_change(
        cls,
        record: User,
        *,
        is_create: bool,
    ) -> None:
        if is_create:
            # Send welcome email
            await send_welcome_email(record.email)
        else:
            # Log update
            logger.info(f"User {record.id} updated")
```

### after_model_delete

Called after deleting a record. Use this for cleanup.

```python
class UserAdmin(ModelView, model=User):
    @classmethod
    async def after_model_delete(cls, record: User) -> None:
        # Clean up related files
        await delete_user_avatar(record.id)

        # Send notification
        await notify_admins(f"User {record.email} was deleted")
```

## Helper Methods

These methods can be used to access column information programmatically.

### get_list_columns

Get the list of columns for the list view.

```python
columns = UserAdmin.get_list_columns()
# Returns: ["id", "email", "name", "created_at"]
```

### get_form_columns

Get the list of columns for forms.

```python
# For create form
create_columns = UserAdmin.get_form_columns(is_create=True)

# For edit form
edit_columns = UserAdmin.get_form_columns(is_create=False)
```

### get_column_info

Get metadata for a specific column.

```python
info = UserAdmin.get_column_info("email")
# Returns: {
#     "name": "email",
#     "sortable": True,
#     "searchable": True,
#     "type": "VARCHAR(255)",
#     "nullable": False,
#     "primary_key": False,
# }
```

## Complete Example

Here's a comprehensive model view example:

```python
from __future__ import annotations

from datetime import datetime
from typing import Any

from litestar.connection import ASGIConnection

from litestar_admin import ModelView
from myapp.models import Article


class ArticleAdmin(ModelView, model=Article):
    """Admin view for Article model with full customization."""

    # Display settings
    name = "Article"
    name_plural = "Articles"
    icon = "newspaper"
    category = "Content"

    # Column configuration
    column_list = ["id", "title", "author", "status", "published_at", "views"]
    column_exclude_list = ["content"]  # Too long for list view
    column_searchable_list = ["title", "content", "author"]
    column_sortable_list = ["id", "title", "published_at", "views"]
    column_default_sort = ("published_at", "desc")

    # Form configuration
    form_columns = ["title", "content", "author", "status", "published_at"]
    form_excluded_columns = ["id", "created_at", "updated_at", "views"]

    # Permissions
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    can_export = True

    # Pagination
    page_size = 25
    page_size_options = [10, 25, 50, 100]

    @classmethod
    async def is_accessible(cls, connection: ASGIConnection) -> bool:
        """Only authenticated users can access articles."""
        return getattr(connection, "user", None) is not None

    @classmethod
    async def can_delete_record(
        cls,
        connection: ASGIConnection,
        record: Article,
    ) -> bool:
        """Only admins can delete published articles."""
        user = getattr(connection, "user", None)
        if user is None:
            return False
        if record.status == "published":
            return "admin" in user.roles
        return True

    @classmethod
    async def on_model_change(
        cls,
        data: dict[str, Any],
        record: Article | None,
        *,
        is_create: bool,
    ) -> dict[str, Any]:
        """Process data before save."""
        # Auto-generate slug from title
        if "title" in data and ("slug" not in data or not data["slug"]):
            data["slug"] = slugify(data["title"])

        # Set timestamps
        now = datetime.utcnow()
        if is_create:
            data["created_at"] = now
        data["updated_at"] = now

        return data

    @classmethod
    async def after_model_change(
        cls,
        record: Article,
        *,
        is_create: bool,
    ) -> None:
        """Actions after save."""
        if record.status == "published":
            # Invalidate cache
            await cache.delete(f"article:{record.id}")
            # Notify subscribers
            await notify_subscribers(record)

    @classmethod
    async def after_model_delete(cls, record: Article) -> None:
        """Cleanup after delete."""
        # Remove from search index
        await search_index.delete(f"article:{record.id}")
```
