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

### form_fieldsets

Group form fields into collapsible sections for better organization. Each fieldset is a dictionary with the following options:

| Option | Type | Description |
|--------|------|-------------|
| `title` | `str` | The section header displayed to users |
| `description` | `str` | Optional help text shown below the title |
| `fields` | `list[str]` | List of field names to include in this section |
| `collapsible` | `bool` | Whether users can collapse/expand this section (default: `True`) |
| `collapsed` | `bool` | Whether the section starts collapsed (default: `False`) |

```python
from typing import Any, ClassVar

from litestar_admin import ModelView
from myapp.models import User


class UserAdmin(ModelView, model=User):
    form_fieldsets: ClassVar[list[dict[str, Any]]] = [
        {
            "title": "Personal Information",
            "description": "Basic user information and contact details",
            "fields": ["email", "name", "password"],
            "collapsible": False,  # Always visible
        },
        {
            "title": "Access Control",
            "description": "User permissions and account status",
            "fields": ["role", "is_active"],
            "collapsed": False,
            "collapsible": True,  # Users can collapse this section
        },
    ]
```

Fieldsets provide visual separation and help users navigate complex forms. The collapsible behavior uses smooth height animations and maintains accessibility with proper ARIA attributes.

### form_widgets

Specify custom widget types for specific fields. This allows using specialized input components like rich text editors instead of plain text areas.

```python
from typing import ClassVar

from litestar_admin import ModelView
from myapp.models import BlogPost


class BlogPostAdmin(ModelView, model=BlogPost):
    form_widgets: ClassVar[dict[str, str]] = {
        "content": "richtext",  # Use rich text editor for content field
    }
```

Available widget types:

| Widget | Description |
|--------|-------------|
| `richtext` | Tiptap-based WYSIWYG editor with formatting toolbar |

See the [Rich Text Fields](#rich-text-fields) section for more details.

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

## Column Visibility

The admin panel allows users to show or hide columns in data tables. This feature helps users focus on the data most relevant to their tasks.

### How It Works

Users can toggle column visibility through a dropdown menu in the table toolbar. The visibility preferences are persisted in the browser's localStorage, so each user's settings are remembered across sessions.

Key features:

- **Per-table persistence**: Each model view stores its own column visibility state
- **Bulk actions**: "Show All" and "Hide All" buttons for quick configuration
- **Minimum columns**: At least one column must remain visible
- **Required columns**: Some columns (like primary keys) may be marked as non-hideable

### Default Visible Columns

By default, all columns in `column_list` are visible. The frontend uses a storage key based on the model identity to persist user preferences:

```
litestar-admin:columns:{model_identity}
```

For example, a User model might use `litestar-admin:columns:user`.

### Column Configuration

Columns can be configured with visibility options through the column metadata:

```python
class UserAdmin(ModelView, model=User):
    column_list = ["id", "email", "name", "role", "is_active", "created_at"]

    # The frontend will show all columns by default
    # Users can hide any column except those marked as required
```

The visibility state includes:

- Which columns are currently visible
- The count of visible vs. total columns (shown in the dropdown button)
- Visual indicators for hidden columns

## Rich Text Fields

For content fields that require formatting (like blog posts or descriptions), you can use the rich text editor widget. This provides a WYSIWYG editing experience with a formatting toolbar.

### Configuring Rich Text Fields

There are two ways to configure rich text fields:

#### Using form_widgets (Simple)

Use the `form_widgets` attribute to specify which fields should use the rich text editor:

```python
from typing import ClassVar

from litestar_admin import ModelView
from myapp.models import BlogPost


class BlogPostAdmin(ModelView, model=BlogPost):
    form_widgets: ClassVar[dict[str, str]] = {
        "content": "richtext",
    }
```

#### Using RichTextField (Advanced)

For more control over toolbar, validation, and XSS sanitization, use `RichTextField`:

```python
from typing import ClassVar

from litestar_admin import ModelView
from litestar_admin.fields import RichTextField
from myapp.models import BlogPost


class BlogPostAdmin(ModelView, model=BlogPost):
    rich_text_fields: ClassVar[list[RichTextField]] = [
        RichTextField(
            name="content",
            description="Main article content",
            required=True,
            toolbar=["bold", "italic", "link", "heading", "bulletList", "orderedList"],
            max_length=50000,
            allowed_tags=["p", "h1", "h2", "h3", "strong", "em", "a", "ul", "ol", "li"],
        ),
        RichTextField(
            name="summary",
            placeholder="Enter a brief summary...",
            max_length=500,
        ),
    ]
```

**RichTextField Options**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `name` | `str` | Required | Field name matching the model attribute |
| `description` | `str` | `""` | Help text shown below the editor |
| `required` | `bool` | `False` | Whether the field is required |
| `placeholder` | `str` | `""` | Placeholder text when empty |
| `toolbar` | `list[str]` | All buttons | Toolbar buttons to display |
| `max_length` | `int \| None` | `None` | Max character count (plain text) |
| `allowed_tags` | `list[str]` | Safe defaults | Allowed HTML tags for sanitization |
| `label` | `str \| None` | Auto-generated | Custom label for the field |

**Available Toolbar Buttons**

- `bold`, `italic`, `underline`, `strike` - Text formatting
- `code`, `codeBlock` - Code formatting
- `heading` - H1-H6 headings
- `bulletList`, `orderedList` - Lists
- `blockquote` - Block quotes
- `link`, `image` - Media
- `horizontalRule` - Horizontal line
- `undo`, `redo` - History

### Editor Features

The rich text editor is built on [Tiptap](https://tiptap.dev/) and includes:

**Text Formatting**
- Bold (Ctrl+B)
- Italic (Ctrl+I)
- Strikethrough
- Inline code

**Structure**
- Headings (H1, H2, H3)
- Bullet lists
- Numbered lists
- Blockquotes
- Horizontal rules

**Links**
- Add links with URL editing
- Remove links
- Links open in new tabs by default

**Code**
- Code blocks with syntax highlighting
- Supports common programming languages via lowlight

**History**
- Undo (Ctrl+Z)
- Redo (Ctrl+Shift+Z)

### Example: Blog Post Admin

Here's a complete example using both form fieldsets and rich text editing:

```python
from typing import Any, ClassVar

from litestar_admin import ModelView
from myapp.models import BlogPost


class BlogPostAdmin(ModelView, model=BlogPost):
    """Admin view for BlogPost with rich text content editing."""

    name = "Blog Post"
    name_plural = "Blog Posts"
    icon = "edit-3"
    category = "Content"

    column_list = ["id", "title", "status", "author_id", "featured", "created_at"]
    column_searchable_list = ["title", "content", "excerpt"]

    # Exclude auto-generated fields from forms
    form_excluded_columns = ["created_at", "updated_at"]

    # Use rich text editor for the content field
    form_widgets: ClassVar[dict[str, str]] = {
        "content": "richtext",
    }

    # Organize form fields into logical sections
    form_fieldsets: ClassVar[list[dict[str, Any]]] = [
        {
            "title": "Content",
            "description": "Main blog post content with rich text editing",
            "fields": ["title", "slug", "excerpt", "content"],
            "collapsible": False,
        },
        {
            "title": "Publishing",
            "description": "Publication status and visibility settings",
            "fields": ["status", "author_id", "featured", "published_at"],
            "collapsed": False,
            "collapsible": True,
        },
    ]
```

### HTML Output

The rich text editor outputs standard HTML that can be:

- Stored in `TEXT` or `VARCHAR` database columns
- Rendered directly in templates with proper sanitization
- Processed by content pipelines

Example HTML output:

```html
<h2>Welcome to Our Blog</h2>
<p>This is a <strong>formatted</strong> paragraph with <em>emphasis</em>.</p>
<ul>
  <li>First item</li>
  <li>Second item</li>
</ul>
<pre><code class="language-python">print("Hello, World!")</code></pre>
```

### XSS Sanitization

Rich text content is automatically sanitized before saving to protect against XSS attacks. The sanitization:

- Removes dangerous tags like `<script>`, `<iframe>`, `<object>`
- Removes event handlers like `onclick`, `onerror`
- Blocks dangerous URL schemes like `javascript:`
- Adds `rel="noopener noreferrer"` to external links

**Requirements:**

XSS sanitization requires the `nh3` library (Rust ammonia bindings). Install it with:

```bash
pip install litestar-admin[sanitize]
```

If `nh3` is not installed, content is saved as-is with a warning logged.

**Customizing Allowed Tags:**

Use the `allowed_tags` parameter on `RichTextField` to control which HTML tags are allowed:

```python
RichTextField(
    name="content",
    allowed_tags=["p", "strong", "em", "a"],  # Very restrictive
)
```

Default allowed tags include common formatting elements:
- Block: `p`, `h1`-`h6`, `blockquote`, `pre`, `code`, `hr`, `br`, `div`
- Lists: `ul`, `ol`, `li`
- Inline: `a`, `strong`, `b`, `em`, `i`, `u`, `s`, `span`, `mark`
- Media: `img` (with `src`, `alt` attributes filtered)
- Tables: `table`, `thead`, `tbody`, `tr`, `th`, `td`

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
