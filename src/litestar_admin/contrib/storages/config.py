"""Storage configuration for litestar-admin.

This module provides configuration classes for file storage integration
with litestar-storages library.

Example:
    Basic usage with local storage:

    >>> from litestar_admin.contrib.storages import StorageConfig, StorageBackendType
    >>>
    >>> config = StorageConfig(
    ...     backend=StorageBackendType.LOCAL,
    ...     upload_path="/uploads/admin",
    ...     allowed_extensions=["jpg", "png", "pdf"],
    ...     max_file_size=10 * 1024 * 1024,  # 10MB
    ... )

    S3 storage configuration:

    >>> config = StorageConfig(
    ...     backend=StorageBackendType.S3,
    ...     upload_path="admin/uploads",
    ...     s3_bucket="my-bucket",
    ...     s3_region="us-east-1",
    ...     s3_access_key="...",
    ...     s3_secret_key="...",
    ... )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "StorageBackendType",
    "StorageConfig",
    "ThumbnailConfig",
]


class StorageBackendType(str, Enum):
    """Supported storage backend types.

    These correspond to storage backends available in litestar-storages.

    Attributes:
        LOCAL: Local filesystem storage.
        S3: Amazon S3 or S3-compatible storage (MinIO, DigitalOcean Spaces, etc.).
        GCS: Google Cloud Storage.
        MEMORY: In-memory storage (useful for testing).
    """

    LOCAL = "local"
    S3 = "s3"
    GCS = "gcs"
    MEMORY = "memory"


@dataclass
class ThumbnailConfig:
    """Configuration for image thumbnail generation.

    Attributes:
        enabled: Whether to generate thumbnails for images.
        width: Maximum thumbnail width in pixels.
        height: Maximum thumbnail height in pixels.
        quality: JPEG quality for thumbnails (1-100).
        format: Output format for thumbnails (jpeg, png, webp).
        suffix: Suffix to append to thumbnail filenames.

    Example:
        >>> config = ThumbnailConfig(
        ...     enabled=True,
        ...     width=200,
        ...     height=200,
        ...     quality=85,
        ... )
    """

    enabled: bool = False
    width: int = 200
    height: int = 200
    quality: int = 85
    format: str = "jpeg"
    suffix: str = "_thumb"

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.width < 1:
            msg = "thumbnail width must be at least 1"
            raise ValueError(msg)

        if self.height < 1:
            msg = "thumbnail height must be at least 1"
            raise ValueError(msg)

        min_quality = 1
        max_quality = 100
        if not min_quality <= self.quality <= max_quality:
            msg = f"thumbnail quality must be between {min_quality} and {max_quality}"
            raise ValueError(msg)

        allowed_formats = {"jpeg", "jpg", "png", "webp"}
        if self.format.lower() not in allowed_formats:
            msg = f"thumbnail format must be one of: {', '.join(sorted(allowed_formats))}"
            raise ValueError(msg)


# Default allowed file extensions for uploads
DEFAULT_ALLOWED_EXTENSIONS: frozenset[str] = frozenset(
    {
        # Images
        "jpg",
        "jpeg",
        "png",
        "gif",
        "webp",
        "svg",
        "ico",
        # Documents
        "pdf",
        "doc",
        "docx",
        "xls",
        "xlsx",
        "ppt",
        "pptx",
        "txt",
        "csv",
        # Archives
        "zip",
        "tar",
        "gz",
    }
)

# Default maximum file size (10 MB)
DEFAULT_MAX_FILE_SIZE: int = 10 * 1024 * 1024


@dataclass
class StorageConfig:
    """Configuration for file storage in litestar-admin.

    This dataclass holds all configuration options for file storage,
    including backend type, upload settings, and validation rules.

    Attributes:
        backend: Type of storage backend to use.
        upload_path: Base path or prefix for file uploads.
        allowed_extensions: Set of allowed file extensions (without dots).
        max_file_size: Maximum file size in bytes.
        thumbnails: Configuration for thumbnail generation.
        public_url_base: Base URL for public file access (if different from storage).
        s3_bucket: S3 bucket name (required for S3 backend).
        s3_region: AWS region for S3 bucket.
        s3_access_key: AWS access key ID (or use environment/IAM role).
        s3_secret_key: AWS secret access key (or use environment/IAM role).
        s3_endpoint_url: Custom S3 endpoint URL (for MinIO, etc.).
        gcs_bucket: GCS bucket name (required for GCS backend).
        gcs_project: GCS project ID.
        gcs_credentials_path: Path to GCS service account JSON file.
        local_base_path: Base filesystem path for local storage.

    Example:
        Local storage:

        >>> config = StorageConfig(
        ...     backend=StorageBackendType.LOCAL,
        ...     upload_path="uploads/admin",
        ...     local_base_path="/var/www/app/static",
        ...     public_url_base="https://example.com/static",
        ... )

        S3 storage:

        >>> config = StorageConfig(
        ...     backend=StorageBackendType.S3,
        ...     upload_path="admin/uploads",
        ...     s3_bucket="my-bucket",
        ...     s3_region="us-east-1",
        ...     public_url_base="https://my-bucket.s3.amazonaws.com",
        ... )
    """

    # General settings
    backend: StorageBackendType = StorageBackendType.LOCAL
    upload_path: str = "uploads/admin"
    allowed_extensions: Sequence[str] | None = None
    max_file_size: int = DEFAULT_MAX_FILE_SIZE
    thumbnails: ThumbnailConfig = field(default_factory=ThumbnailConfig)
    public_url_base: str | None = None

    # S3 settings
    s3_bucket: str | None = None
    s3_region: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_endpoint_url: str | None = None

    # GCS settings
    gcs_bucket: str | None = None
    gcs_project: str | None = None
    gcs_credentials_path: str | None = None

    # Local storage settings
    local_base_path: str | None = None

    def __post_init__(self) -> None:
        """Validate configuration values."""
        # Normalize upload path (remove leading/trailing slashes)
        self.upload_path = self.upload_path.strip("/")

        # Validate max file size
        if self.max_file_size < 1:
            msg = "max_file_size must be at least 1 byte"
            raise ValueError(msg)

        # Validate backend-specific requirements
        if self.backend == StorageBackendType.S3 and not self.s3_bucket:
            msg = "s3_bucket is required for S3 storage backend"
            raise ValueError(msg)

        if self.backend == StorageBackendType.GCS and not self.gcs_bucket:
            msg = "gcs_bucket is required for GCS storage backend"
            raise ValueError(msg)

        if self.backend == StorageBackendType.LOCAL and not self.local_base_path:
            msg = "local_base_path is required for local storage backend"
            raise ValueError(msg)

    @property
    def allowed_extensions_set(self) -> frozenset[str]:
        """Get allowed extensions as a frozenset.

        Returns:
            Frozenset of allowed file extensions (lowercase, without dots).
        """
        if self.allowed_extensions is None:
            return DEFAULT_ALLOWED_EXTENSIONS
        return frozenset(ext.lower().lstrip(".") for ext in self.allowed_extensions)

    def is_extension_allowed(self, extension: str) -> bool:
        """Check if a file extension is allowed.

        Args:
            extension: The file extension to check (with or without leading dot).

        Returns:
            True if the extension is allowed, False otherwise.
        """
        ext = extension.lower().lstrip(".")
        return ext in self.allowed_extensions_set

    def is_size_allowed(self, size: int) -> bool:
        """Check if a file size is within the allowed limit.

        Args:
            size: The file size in bytes.

        Returns:
            True if the size is allowed, False otherwise.
        """
        return 0 < size <= self.max_file_size

    def get_storage_kwargs(self) -> dict[str, str | None]:
        """Get keyword arguments for litestar-storages backend constructor.

        Returns:
            Dictionary of kwargs for the storage backend constructor.

        Raises:
            ValueError: If required configuration for the backend is missing.
        """
        if self.backend == StorageBackendType.LOCAL:
            return {
                "path": self.local_base_path,
            }

        if self.backend == StorageBackendType.S3:
            kwargs: dict[str, str | None] = {
                "bucket": self.s3_bucket,
            }
            if self.s3_region:
                kwargs["region"] = self.s3_region
            if self.s3_access_key:
                kwargs["access_key"] = self.s3_access_key
            if self.s3_secret_key:
                kwargs["secret_key"] = self.s3_secret_key
            if self.s3_endpoint_url:
                kwargs["endpoint_url"] = self.s3_endpoint_url
            return kwargs

        if self.backend == StorageBackendType.GCS:
            kwargs = {
                "bucket": self.gcs_bucket,
            }
            if self.gcs_project:
                kwargs["project"] = self.gcs_project
            if self.gcs_credentials_path:
                kwargs["credentials_path"] = self.gcs_credentials_path
            return kwargs

        # Memory storage has no special kwargs
        return {}
