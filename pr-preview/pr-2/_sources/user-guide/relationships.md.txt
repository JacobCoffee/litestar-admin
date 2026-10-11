# Relationships

litestar-admin provides automatic detection and handling of SQLAlchemy relationships, offering intuitive UI components for managing foreign key and many-to-many associations in your admin forms.

## Overview

The relationship system includes:

- **Automatic Detection**: SQLAlchemy foreign keys and relationships are detected automatically
- **FK Autocomplete Picker**: Select2-style search and select for foreign key fields
- **M2M Multi-Select Widget**: Tag-style interface for many-to-many relationships
- **Flexible API**: REST endpoints for searching and resolving related records
- **Smart Display Labels**: Intelligent column detection for human-readable labels

## Relationship Types

litestar-admin supports all standard SQLAlchemy relationship patterns:

| Type | Description | Example |
|------|-------------|---------|
| Many-to-One | FK on this model pointing to another | `Post.author_id -> User` |
| One-to-Many | FK on related model pointing to this one | `User.posts` |
| Many-to-Many | Association table linking two models | `User.roles` via `user_roles` |
| One-to-One | Single reference with `uselist=False` | `User.profile` |

## Quick Setup

Relationships are detected automatically from your SQLAlchemy models. No additional configuration is required for basic functionality.

```python
from sqlalchemy import ForeignKey, Integer, String, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from your_app.db import Base

# Association table for M2M
post_tags = Table(
    "post_tags",
    Base.metadata,
    Column("post_id", Integer, ForeignKey("post.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tag.id"), primary_key=True),
)

class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(200), unique=True)

    # One-to-many relationship
    posts: Mapped[list["Post"]] = relationship(back_populates="author")


class Tag(Base):
    __tablename__ = "tag"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)


class Post(Base):
    __tablename__ = "post"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)

    # Many-to-one relationship (FK)
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    author: Mapped[User] = relationship(back_populates="posts")

    # Many-to-many relationship
    tags: Mapped[list[Tag]] = relationship(secondary=post_tags)
```

## Relationship Detection

### How Detection Works

The `RelationshipDetector` class inspects SQLAlchemy models to extract relationship metadata. Detection happens automatically when models are registered with the admin.

```python
from litestar_admin.relationships import RelationshipDetector, RelationshipType

detector = RelationshipDetector()

# Detect all relationships on a model
relationships = detector.detect_relationships(Post)

for rel in relationships:
    print(f"{rel.name}: {rel.relationship_type.value} -> {rel.related_model_name}")
    # Output:
    # author: many_to_one -> User
    # tags: many_to_many -> Tag
```

### RelationshipInfo

Each detected relationship is represented as a `RelationshipInfo` dataclass:

```python
from litestar_admin.relationships import RelationshipInfo

# RelationshipInfo attributes:
info = RelationshipInfo(
    name="author",                          # Relationship attribute name
    related_model=User,                      # Target model class
    relationship_type=RelationshipType.MANY_TO_ONE,
    foreign_key_column="author_id",          # FK column name (if applicable)
    back_populates="posts",                  # Back-reference name
    nullable=False,                          # Whether the FK is nullable
    uselist=False,                           # True for to-many relationships
    secondary_table=None,                    # Association table for M2M
)

# Useful properties
info.is_to_many  # True if relationship returns multiple objects
info.is_to_one   # True if relationship returns a single object
```

### Flexible Field Lookup

The detector supports flexible lookups by either relationship name or FK column name:

```python
# By relationship name
rel_info = detector.get_relationship_info(Post, "author")

# By FK column name
rel_info = detector.get_relationship_info_by_fk(Post, "author_id")

# Flexible lookup (tries both)
rel_info = detector.get_relationship_info_flexible(Post, "author_id")
```

## Using RelationshipPicker in Forms

### Single-Select (FK) Picker

For many-to-one and one-to-one relationships, the `RelationshipPicker` component provides a Select2-style autocomplete interface.

```tsx
import { RelationshipPicker } from "@/components/forms/RelationshipPicker";

function PostForm({ post, onSave }) {
  const [authorId, setAuthorId] = useState(post?.author_id ?? null);

  return (
    <form>
      <label>Author</label>
      <RelationshipPicker
        modelName="Post"
        fieldName="author_id"
        value={authorId}
        onChange={(id) => setAuthorId(id)}
        placeholder="Select an author..."
      />
    </form>
  );
}
```

#### RelationshipPicker Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `modelName` | `string` | required | Source model name |
| `fieldName` | `string` | required | Relationship or FK field name |
| `value` | `string \| number \| null` | required | Currently selected value |
| `onChange` | `(value) => void` | required | Change handler |
| `placeholder` | `string` | `"Search..."` | Input placeholder text |
| `disabled` | `boolean` | `false` | Disable the picker |
| `minChars` | `number` | `1` | Minimum characters before search |
| `debounceMs` | `number` | `300` | Search debounce delay |
| `maxResults` | `number` | `20` | Maximum search results |
| `error` | `boolean` | `false` | Show error styling |

#### Features

- **Debounced Search**: Configurable delay prevents excessive API calls
- **Keyboard Navigation**: Arrow keys, Enter, and Escape support
- **Loading State**: Visual feedback during search
- **Clear Button**: Easy value clearing
- **Dark Theme**: Matches the admin panel aesthetic

## M2M Multi-Select Configuration

### Multi-Select Picker

For many-to-many relationships, the `MultiRelationshipPicker` component provides a tag/chip-style multi-select interface.

```tsx
import { MultiRelationshipPicker } from "@/components/forms/MultiRelationshipPicker";

function PostForm({ post, onSave }) {
  const [tagIds, setTagIds] = useState<(string | number)[]>(
    post?.tags?.map(t => t.id) ?? []
  );

  return (
    <form>
      <label>Tags</label>
      <MultiRelationshipPicker
        modelName="Post"
        fieldName="tags"
        value={tagIds}
        onChange={(ids) => setTagIds(ids)}
        placeholder="Add tags..."
        maxItems={10}
      />
    </form>
  );
}
```

#### MultiRelationshipPicker Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `modelName` | `string` | required | Source model name |
| `fieldName` | `string` | required | Relationship field name |
| `value` | `(string \| number)[]` | required | Array of selected values |
| `onChange` | `(value) => void` | required | Change handler |
| `placeholder` | `string` | `"Search to add..."` | Input placeholder |
| `disabled` | `boolean` | `false` | Disable the picker |
| `minChars` | `number` | `1` | Minimum characters before search |
| `debounceMs` | `number` | `300` | Search debounce delay |
| `maxResults` | `number` | `20` | Maximum search results |
| `maxItems` | `number` | `0` | Max selections (0 = unlimited) |
| `error` | `boolean` | `false` | Show error styling |

#### Features

- **Chip Display**: Selected items shown as removable chips
- **Individual Removal**: Click X to remove single items
- **Backspace Removal**: Press backspace to remove last item
- **Clear All**: Button to remove all selections at once
- **Max Limit**: Optional cap on number of selections

## Customizing Display Labels

### Automatic Label Detection

The relationship system automatically detects the best column to use for display labels. It checks these column names in order of preference:

1. `name`
2. `title`
3. `label`
4. `display_name`
5. `full_name`
6. `username`
7. `email`
8. `slug`
9. `code`
10. Falls back to primary key

### Custom Search Fields

Configure which fields are searched for a relationship:

```python
from litestar_admin import ModelView

class PostAdmin(ModelView, model=Post):
    name = "Post"

    # Configure search fields for specific relationships
    relationship_search_fields = {
        "author": ["name", "email", "username"],  # Search these User fields
        "tags": ["name", "slug"],                  # Search these Tag fields
    }
```

### Additional Display Data

Include extra fields in the autocomplete response:

```python
class PostAdmin(ModelView, model=Post):
    name = "Post"

    # Include additional fields in autocomplete options
    relationship_display_fields = {
        "author": ["email", "created_at"],  # Include email and created_at
        "tags": ["description"],             # Include tag description
    }
```

The additional data is available in the `data` property of each option:

```typescript
interface RelationshipOption {
  id: string | number;
  label: string;
  data?: {
    email?: string;
    created_at?: string;
    // ... other configured fields
  };
}
```

## API Endpoint Reference

### Search Relationships

Search related records for autocomplete functionality.

```http
GET /admin/api/models/{model_name}/relationships/{field_name}/search
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `q` | string | `""` | Search query string |
| `limit` | integer | `20` | Maximum results (max 100) |
| `page` | integer | `1` | Page number (1-indexed) |

**Example:**

```http
GET /admin/api/models/Post/relationships/author_id/search?q=john&limit=10
```

**Response:**

```json
{
  "items": [
    {
      "id": 1,
      "label": "John Doe",
      "data": {
        "email": "john@example.com"
      }
    },
    {
      "id": 5,
      "label": "Johnny Smith",
      "data": {
        "email": "johnny@example.com"
      }
    }
  ],
  "total": 2,
  "has_more": false
}
```

### Get Options by IDs

Resolve specific related records by their IDs.

```http
GET /admin/api/models/{model_name}/relationships/{field_name}/options
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `ids` | string | Comma-separated list of IDs |

**Example:**

```http
GET /admin/api/models/Post/relationships/tags/options?ids=1,3,5
```

**Response:**

```json
{
  "items": [
    { "id": 1, "label": "Technology", "data": null },
    { "id": 3, "label": "Python", "data": null },
    { "id": 5, "label": "Web Development", "data": null }
  ],
  "total": 3,
  "has_more": false
}
```

## ModelView Configuration

### Complete Example

```python
from typing import ClassVar
from litestar_admin import ModelView

class PostAdmin(ModelView, model=Post):
    name = "Post"
    name_plural = "Posts"
    icon = "file-text"
    category = "Content"

    # List display
    column_list = ["id", "title", "author", "tags", "created_at"]
    column_searchable_list = ["title"]

    # Relationship configuration
    relationship_search_fields: ClassVar[dict[str, list[str]]] = {
        "author": ["name", "email"],
        "tags": ["name"],
    }

    relationship_display_fields: ClassVar[dict[str, list[str]]] = {
        "author": ["email"],
    }

    # Form fields (relationships auto-detected)
    form_include = ["title", "content", "author_id", "tags"]
```

### Handling Relationship Data in Hooks

Process relationship changes in the `on_model_change` hook:

```python
class PostAdmin(ModelView, model=Post):
    @classmethod
    async def on_model_change(
        cls,
        data: dict[str, Any],
        record: Post | None,
        *,
        is_create: bool,
    ) -> dict[str, Any]:
        # Handle M2M relationship
        if "tags" in data:
            tag_ids = data.pop("tags")
            # M2M relationships are handled separately
            record._pending_tags = tag_ids

        return data

    @classmethod
    async def after_model_change(
        cls,
        data: dict[str, Any],
        record: Post,
        *,
        is_create: bool,
        session: AsyncSession,
    ) -> None:
        # Apply pending M2M changes
        if hasattr(record, "_pending_tags"):
            tag_ids = record._pending_tags
            # Query and assign tags
            tags = await session.scalars(
                select(Tag).where(Tag.id.in_(tag_ids))
            )
            record.tags = list(tags.all())
            delattr(record, "_pending_tags")
```

## Best Practices

1. **Use Meaningful Column Names**: Name your columns `name`, `title`, or `label` for automatic display detection.

2. **Define Back-References**: Always define `back_populates` for bidirectional relationship navigation.

3. **Configure Search Fields**: For large datasets, specify `relationship_search_fields` to search only indexed columns.

4. **Set Reasonable Limits**: Use `maxItems` for M2M relationships to prevent users from adding too many associations.

5. **Handle Nullable FKs**: Ensure your ModelView allows clearing nullable FK fields.

6. **Test with Large Datasets**: The autocomplete search is optimized for performance, but test with realistic data volumes.

```python
# Good: Indexed column for searching
class User(Base):
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)

# Configure to search the indexed column
class PostAdmin(ModelView, model=Post):
    relationship_search_fields = {
        "author": ["email"],  # Search the indexed column
    }
```

## See Also

- [Model Views](../model-views.md) - ModelView configuration options
- [Custom Views](custom-views.md) - Building custom admin views
- [File Uploads](file-uploads.md) - Handling file uploads in forms
