# Storage Configuration

litestar-admin supports multiple storage backends for file uploads through the `litestar-storages` integration. This guide covers all available storage options and their configuration.

## Installation

Install the storage extra for your preferred backend:

`````{tab-set}
````{tab-item} Local Filesystem
```bash
# Base installation includes local filesystem support
pip install litestar-admin
```
````

````{tab-item} Amazon S3
```bash
pip install "litestar-admin[storage]"
pip install "litestar-storages[s3]"
```
````

````{tab-item} Google Cloud Storage
```bash
pip install "litestar-admin[storage]"
pip install "litestar-storages[gcs]"
```
````
`````

## Storage Backends

### Local Filesystem

Store files on the local filesystem. Best for development and single-server deployments.

```python
from litestar_admin.contrib.storages import StorageConfig, StorageBackendType

storage_config = StorageConfig(
    backend=StorageBackendType.LOCAL,
    local_base_path="/var/www/app/uploads",  # Required
    upload_path="admin/files",
    public_url_base="https://example.com/uploads",
)
```

#### Configuration Options

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `local_base_path` | `str` | Yes | Absolute path to the storage directory |
| `upload_path` | `str` | No | Subdirectory for admin uploads (default: `uploads/admin`) |
| `public_url_base` | `str` | No | Base URL for serving files |

```{warning}
Ensure the `local_base_path` directory exists and is writable by the application user.
```

### Amazon S3

Store files in Amazon S3 or S3-compatible services (MinIO, DigitalOcean Spaces, etc.).

```python
from litestar_admin.contrib.storages import StorageConfig, StorageBackendType

storage_config = StorageConfig(
    backend=StorageBackendType.S3,
    s3_bucket="my-app-uploads",  # Required
    s3_region="us-east-1",
    s3_access_key="AKIAIOSFODNN7EXAMPLE",  # Or use IAM role
    s3_secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    upload_path="admin/uploads",
    public_url_base="https://my-app-uploads.s3.amazonaws.com",
)
```

#### S3-Compatible Services

For MinIO, DigitalOcean Spaces, or other S3-compatible services:

```python
storage_config = StorageConfig(
    backend=StorageBackendType.S3,
    s3_bucket="my-bucket",
    s3_endpoint_url="https://minio.example.com:9000",  # Custom endpoint
    s3_access_key="minioadmin",
    s3_secret_key="minioadmin",
    public_url_base="https://minio.example.com:9000/my-bucket",
)
```

#### Configuration Options

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `s3_bucket` | `str` | Yes | S3 bucket name |
| `s3_region` | `str` | No | AWS region (e.g., `us-east-1`) |
| `s3_access_key` | `str` | No | AWS access key ID |
| `s3_secret_key` | `str` | No | AWS secret access key |
| `s3_endpoint_url` | `str` | No | Custom S3 endpoint URL |

```{note}
If access keys are not provided, the SDK will use the default credential chain (environment variables, IAM role, etc.).
```

### Google Cloud Storage

Store files in Google Cloud Storage.

```python
from litestar_admin.contrib.storages import StorageConfig, StorageBackendType

storage_config = StorageConfig(
    backend=StorageBackendType.GCS,
    gcs_bucket="my-app-uploads",  # Required
    gcs_project="my-gcp-project",
    gcs_credentials_path="/path/to/service-account.json",  # Or use ADC
    upload_path="admin/uploads",
    public_url_base="https://storage.googleapis.com/my-app-uploads",
)
```

#### Configuration Options

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `gcs_bucket` | `str` | Yes | GCS bucket name |
| `gcs_project` | `str` | No | GCP project ID |
| `gcs_credentials_path` | `str` | No | Path to service account JSON |

### Memory Storage

In-memory storage for testing. Files are lost when the application restarts.

```python
from litestar_admin.contrib.storages import StorageConfig, StorageBackendType

storage_config = StorageConfig(
    backend=StorageBackendType.MEMORY,
    upload_path="admin/uploads",
)
```

```{warning}
Memory storage is for testing only. Do not use in production.
```

## File Validation

### Allowed Extensions

Whitelist file extensions that can be uploaded:

```python
storage_config = StorageConfig(
    backend=StorageBackendType.LOCAL,
    local_base_path="./uploads",
    allowed_extensions=[
        # Images
        "jpg", "jpeg", "png", "gif", "webp", "svg",
        # Documents
        "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
        # Archives
        "zip", "tar", "gz",
    ],
)
```

Default allowed extensions include common image, document, and archive formats.

### Maximum File Size

Set the maximum allowed file size in bytes:

```python
storage_config = StorageConfig(
    backend=StorageBackendType.LOCAL,
    local_base_path="./uploads",
    max_file_size=50 * 1024 * 1024,  # 50MB
)
```

Default is 10MB.

## Thumbnail Configuration

Configure automatic thumbnail generation for image uploads:

```python
from litestar_admin.contrib.storages import StorageConfig, ThumbnailConfig

storage_config = StorageConfig(
    backend=StorageBackendType.LOCAL,
    local_base_path="./uploads",
    thumbnails=ThumbnailConfig(
        enabled=True,
        width=200,
        height=200,
        quality=85,
        format="jpeg",  # jpeg, png, or webp
        suffix="_thumb",
    ),
)
```

### ThumbnailConfig Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | `bool` | `False` | Enable thumbnail generation |
| `width` | `int` | `200` | Maximum thumbnail width |
| `height` | `int` | `200` | Maximum thumbnail height |
| `quality` | `int` | `85` | JPEG/WebP quality (1-100) |
| `format` | `str` | `jpeg` | Output format (jpeg, png, webp) |
| `suffix` | `str` | `_thumb` | Suffix for thumbnail filenames |

### Multiple Thumbnail Sizes

Generate multiple thumbnail sizes using the storage backend directly:

```python
from litestar_admin.contrib.storages import AdminStorageBackend
from litestar_admin.contrib.storages.thumbnails import ThumbnailSize

storage = AdminStorageBackend(storage_config)

sizes = [
    ThumbnailSize(100, 100, "_small"),
    ThumbnailSize(300, 300, "_medium"),
    ThumbnailSize(600, 600, "_large"),
]

result = await storage.upload_with_thumbnails(
    file_content=image_bytes,
    filename="photo.jpg",
    model_name="product",
    field_name="image",
    sizes=sizes,
    format="webp",
    quality=90,
)

print(result.storage_path)  # Main image path
print(result.additional_thumbnails)  # {"_small": "...", "_medium": "...", "_large": "..."}
```

## Using the Storage Backend

### Direct Usage

Access the storage backend for custom operations:

```python
from litestar_admin.contrib.storages import AdminStorageBackend

storage = AdminStorageBackend(storage_config)

# Upload a file
path = await storage.upload(
    file_content=file_bytes,
    filename="document.pdf",
    model_name="report",
    field_name="attachment",
)

# Get public URL
url = storage.get_public_url(path)

# Check if file exists
exists = await storage.exists(path)

# Read file content
content = await storage.read(path)

# Delete a file
await storage.delete(path)
```

### Upload with Thumbnail

Upload an image with automatic thumbnail generation:

```python
main_path, thumb_path = await storage.upload_with_thumbnail(
    file_content=image_bytes,
    filename="photo.jpg",
    model_name="user",
    field_name="avatar",
)
```

### Generate Thumbnail for Existing File

Create a thumbnail for an already-uploaded image:

```python
thumb_bytes, thumb_path = await storage.generate_thumbnail(
    path="admin/files/user/avatar/photo.jpg",
    size=(150, 150),
    format="webp",
    quality=85,
)
```

### Get or Generate Thumbnail

Get an existing thumbnail or generate one on-demand:

```python
thumb_bytes, thumb_path = await storage.get_or_generate_thumbnail(
    path="admin/files/user/avatar/photo.jpg",
    size=(150, 150),
)
```

## Path Structure

Files are stored with a structured path:

```
{upload_path}/{model_name}/{field_name}/{year}/{month}/{filename}
```

Example:
```
admin/files/document/attachment/2024/01/report-abc123.pdf
```

This structure:
- Organizes files by model and field
- Prevents filename collisions with unique suffixes
- Enables easy cleanup and management
- Allows efficient directory-based queries

## Environment-Based Configuration

Configure storage based on environment:

```python
import os
from litestar_admin.contrib.storages import StorageConfig, StorageBackendType

def get_storage_config() -> StorageConfig:
    """Get storage configuration based on environment."""
    env = os.environ.get("ENV", "development")

    if env == "production":
        return StorageConfig(
            backend=StorageBackendType.S3,
            s3_bucket=os.environ["S3_BUCKET"],
            s3_region=os.environ.get("S3_REGION", "us-east-1"),
            public_url_base=os.environ["CDN_URL"],
            max_file_size=50 * 1024 * 1024,
        )

    elif env == "testing":
        return StorageConfig(
            backend=StorageBackendType.MEMORY,
        )

    else:  # development
        return StorageConfig(
            backend=StorageBackendType.LOCAL,
            local_base_path="./uploads",
            public_url_base="http://localhost:8000/uploads",
        )
```

## Security Considerations

1. **Validate File Types**: Always validate file extensions and MIME types server-side.

2. **Set Size Limits**: Configure reasonable file size limits to prevent denial-of-service.

3. **Sanitize Filenames**: The storage backend automatically sanitizes filenames to prevent path traversal.

4. **Use Signed URLs**: For S3/GCS, consider using signed URLs for private files.

5. **Scan Uploads**: Consider integrating virus scanning for uploaded files.

6. **Restrict Access**: Use bucket policies or filesystem permissions to restrict access.

## See Also

- [File Uploads](file-uploads.md) - Using file uploads in models
- [Configuration](../configuration.md) - General admin configuration
- [Model Views](../model-views.md) - ModelView setup
