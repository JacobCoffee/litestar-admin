"""File storage integration for litestar-admin using litestar-storages.

This module provides file upload and storage capabilities for the admin panel,
supporting multiple storage backends (local filesystem, S3, GCS).

Example:
    Basic setup with local storage:

    >>> from litestar_admin import AdminConfig, AdminPlugin
    >>> from litestar_admin.contrib.storages import (
    ...     AdminStorageBackend,
    ...     StorageBackendType,
    ...     StorageConfig,
    ... )
    >>>
    >>> storage_config = StorageConfig(
    ...     backend=StorageBackendType.LOCAL,
    ...     local_base_path="/var/www/uploads",
    ...     upload_path="admin/files",
    ...     allowed_extensions=["jpg", "png", "pdf"],
    ...     max_file_size=10 * 1024 * 1024,  # 10MB
    ... )
    >>>
    >>> admin_config = AdminConfig(
    ...     title="My Admin",
    ...     storage=storage_config,
    ... )

    S3 storage configuration:

    >>> from litestar_admin.contrib.storages import StorageConfig, StorageBackendType
    >>>
    >>> storage_config = StorageConfig(
    ...     backend=StorageBackendType.S3,
    ...     upload_path="admin/uploads",
    ...     s3_bucket="my-bucket",
    ...     s3_region="us-east-1",
    ...     s3_access_key="AKIAIOSFODNN7EXAMPLE",
    ...     s3_secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    ...     public_url_base="https://my-bucket.s3.amazonaws.com",
    ... )

    Using the storage backend directly:

    >>> storage = AdminStorageBackend(storage_config)
    >>> path = await storage.upload(
    ...     file_content=file_bytes,
    ...     filename="document.pdf",
    ...     model_name="user",
    ...     field_name="resume",
    ... )
    >>> url = storage.get_public_url(path)

Note:
    This module requires the ``litestar-storages`` package to be installed.
    Install it with: ``pip install 'litestar-admin[storage]'``

    For S3 storage, you also need boto3:
    ``pip install 'litestar-storages[s3]'``

    For GCS storage, you need google-cloud-storage:
    ``pip install 'litestar-storages[gcs]'``

    For thumbnail generation, you need Pillow:
    ``pip install pillow``
"""

from __future__ import annotations

from litestar_admin.contrib.storages.backend import (
    AdminStorageBackend,
    StorageBackendProtocol,
    UploadResult,
)
from litestar_admin.contrib.storages.config import (
    DEFAULT_ALLOWED_EXTENSIONS,
    DEFAULT_MAX_FILE_SIZE,
    StorageBackendType,
    StorageConfig,
    ThumbnailConfig,
)
from litestar_admin.contrib.storages.thumbnails import (
    ThumbnailGenerator,
    ThumbnailResult,
    ThumbnailSize,
)
from litestar_admin.contrib.storages.utils import (
    generate_thumbnail,
    get_content_hash,
    get_file_extension,
    get_public_url,
    get_storage_path,
    is_image_extension,
    sanitize_filename,
    validate_file,
)

__all__ = [
    # Backend
    "AdminStorageBackend",
    "StorageBackendProtocol",
    "UploadResult",
    # Config
    "DEFAULT_ALLOWED_EXTENSIONS",
    "DEFAULT_MAX_FILE_SIZE",
    "StorageBackendType",
    "StorageConfig",
    "ThumbnailConfig",
    # Thumbnails
    "ThumbnailGenerator",
    "ThumbnailResult",
    "ThumbnailSize",
    # Utils
    "generate_thumbnail",
    "get_content_hash",
    "get_file_extension",
    "get_public_url",
    "get_storage_path",
    "is_image_extension",
    "sanitize_filename",
    "validate_file",
]
