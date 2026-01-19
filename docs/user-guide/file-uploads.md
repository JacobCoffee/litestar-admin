# File Uploads

litestar-admin provides comprehensive file upload support for your admin panel, including drag-and-drop uploads, image previews, thumbnail generation, and multiple storage backends.

## Quick Setup

Add file upload capability to your models with a few configuration steps:

```python
from litestar_admin import AdminPlugin, AdminConfig, ModelView
from litestar_admin.contrib.storages import StorageConfig, StorageBackendType, ThumbnailConfig

# Configure file storage
storage_config = StorageConfig(
    backend=StorageBackendType.LOCAL,
    local_base_path="./uploads",
    upload_path="admin/files",
    public_url_base="/uploads",
    allowed_extensions=["jpg", "jpeg", "png", "gif", "pdf", "doc", "docx"],
    max_file_size=10 * 1024 * 1024,  # 10MB
    thumbnails=ThumbnailConfig(
        enabled=True,
        width=200,
        height=200,
        quality=85,
    ),
)

# Create admin plugin with storage
admin_plugin = AdminPlugin(
    config=AdminConfig(
        title="My Admin",
        storage=storage_config,
        model_views=[DocumentAdmin],
    )
)
```

## Model Setup

Define a model with fields for storing file information:

```python
from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

class Document(Base):
    __tablename__ = "document"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # File storage fields
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    thumbnail_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
```

## ModelView Configuration

Configure your ModelView with file field settings:

```python
from typing import Any, ClassVar
from litestar_admin import ModelView

class DocumentAdmin(ModelView, model=Document):
    name = "Document"
    name_plural = "Documents"
    icon = "file"
    category = "Content"

    column_list = ["id", "title", "original_filename", "file_size", "mime_type"]
    column_searchable_list = ["title", "original_filename"]

    # File field configurations
    file_fields: ClassVar[list[dict[str, Any]]] = [
        {
            "name": "file",
            "type": "file",
            "label": "Upload File",
            "allowed_extensions": ["pdf", "doc", "docx", "txt"],
            "max_size": 10 * 1024 * 1024,  # 10MB
            "description": "Upload a document file",
        },
    ]

    # Image field configurations (with thumbnail support)
    image_fields: ClassVar[list[dict[str, Any]]] = [
        {
            "name": "cover_image",
            "type": "image",
            "label": "Cover Image",
            "allowed_extensions": ["jpg", "jpeg", "png", "gif", "webp"],
            "max_size": 5 * 1024 * 1024,  # 5MB
            "thumbnail_size": (200, 200),
            "description": "Upload a cover image",
        },
    ]
```

## File Field Types

### FileField

For general file uploads (documents, archives, etc.):

```python
from litestar_admin.fields import FileField

file_field = FileField(
    label="Document",
    allowed_extensions=["pdf", "doc", "docx", "txt", "rtf"],
    max_size=10 * 1024 * 1024,  # 10MB
    required=False,
    description="Upload a document file",
)
```

### ImageField

For image uploads with automatic thumbnail generation:

```python
from litestar_admin.fields import ImageField

image_field = ImageField(
    label="Profile Photo",
    allowed_extensions=["jpg", "jpeg", "png", "gif", "webp"],
    max_size=5 * 1024 * 1024,  # 5MB
    thumbnail_size=(200, 200),
    thumbnail_quality=85,
    required=False,
)
```

## Handling File Uploads in Hooks

Process uploaded files in the `on_model_change` hook:

```python
import mimetypes

class DocumentAdmin(ModelView, model=Document):
    @classmethod
    async def on_model_change(
        cls,
        data: dict[str, Any],
        record: Document | None,
        *,
        is_create: bool,
    ) -> dict[str, Any]:
        # Handle file upload data
        if "file" in data and data["file"]:
            file_data = data.pop("file")

            # Extract file metadata
            data["file_path"] = file_data.get("path")
            data["original_filename"] = file_data.get("original_name")
            data["file_size"] = file_data.get("size")

            # Infer MIME type
            if data["original_filename"]:
                mime_type, _ = mimetypes.guess_type(data["original_filename"])
                data["mime_type"] = mime_type

            # Handle thumbnail if present
            if "thumbnail_path" in file_data:
                data["thumbnail_path"] = file_data["thumbnail_path"]

        return data
```

## Frontend Components

The admin panel includes a modern file upload component with:

- **Drag and Drop**: Drag files directly onto the upload area
- **Progress Indicator**: Visual feedback during upload
- **File Preview**: Preview images before upload
- **Multiple Files**: Upload multiple files at once (when configured)
- **Validation**: Client-side extension and size validation

The component automatically renders for fields with `type: "file"` or `format: "file"` in the schema.

## Validation

### Extension Validation

Configure allowed file extensions at multiple levels:

```python
# Global storage config
storage_config = StorageConfig(
    allowed_extensions=["jpg", "png", "pdf"],
    ...
)

# Per-field override
file_fields = [
    {
        "name": "resume",
        "allowed_extensions": ["pdf", "doc", "docx"],  # Override for this field
    },
]
```

### Size Validation

Set maximum file sizes:

```python
# Global limit
storage_config = StorageConfig(
    max_file_size=10 * 1024 * 1024,  # 10MB
    ...
)

# Per-field limit
file_fields = [
    {
        "name": "avatar",
        "max_size": 2 * 1024 * 1024,  # 2MB for avatars
    },
]
```

### Custom Validation

Add custom validation in hooks:

```python
@classmethod
async def on_model_change(
    cls,
    data: dict[str, Any],
    record: Any | None,
    *,
    is_create: bool,
) -> dict[str, Any]:
    if "file" in data:
        file_data = data["file"]

        # Custom validation: check for virus scan, content validation, etc.
        if not await is_file_safe(file_data["content"]):
            raise ValueError("File failed security scan")

    return data
```

## API Endpoints

When file storage is configured, these endpoints are available:

### Upload File

```http
POST /admin/api/files/upload
Content-Type: multipart/form-data

file: <binary>
model_name: document
field_name: attachment
```

**Response:**
```json
{
    "path": "admin/files/document/attachment/2024/01/file-abc123.pdf",
    "url": "/uploads/admin/files/document/attachment/2024/01/file-abc123.pdf",
    "thumbnail_path": null,
    "thumbnail_url": null,
    "original_name": "report.pdf",
    "size": 1048576,
    "mime_type": "application/pdf"
}
```

### Get File Info

```http
GET /admin/api/files/info/{file_path}
```

**Response:**
```json
{
    "exists": true,
    "path": "admin/files/document/attachment/file.pdf",
    "url": "/uploads/admin/files/document/attachment/file.pdf",
    "size": 1048576,
    "mime_type": "application/pdf"
}
```

### Delete File

```http
DELETE /admin/api/files/{file_path}
```

### Get Thumbnail

```http
GET /admin/api/files/thumbnail/{file_path}?size=200x200&format=webp&quality=85
```

## Best Practices

1. **Store Metadata Separately**: Keep file paths, sizes, and MIME types in separate database columns for efficient querying.

2. **Use Thumbnails**: Enable thumbnail generation for images to improve admin panel performance.

3. **Set Reasonable Limits**: Configure appropriate file size limits to prevent abuse.

4. **Validate Extensions**: Whitelist allowed extensions rather than blacklisting dangerous ones.

5. **Secure Storage**: Use proper filesystem permissions or cloud storage IAM policies.

6. **Clean Up Orphans**: Implement cleanup logic for files that are no longer referenced.

```python
@classmethod
async def after_model_delete(cls, record: Document) -> None:
    # Clean up associated files
    if record.file_path:
        storage = get_admin_storage()
        await storage.delete(record.file_path)

    if record.thumbnail_path:
        await storage.delete(record.thumbnail_path)
```

## See Also

- [Storage Configuration](storage.md) - Detailed storage backend setup
- [Model Views](../model-views.md) - ModelView configuration options
- [Custom Views](custom-views.md) - Building custom admin views
