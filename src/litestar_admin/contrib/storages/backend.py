"""Storage backend wrapper for litestar-admin.

This module provides a unified interface for file storage operations,
wrapping litestar-storages backends with admin-specific functionality.

Example:
    Basic usage:

    >>> from litestar_admin.contrib.storages import AdminStorageBackend, StorageConfig
    >>>
    >>> config = StorageConfig(
    ...     backend=StorageBackendType.LOCAL,
    ...     local_base_path="/var/www/uploads",
    ...     upload_path="admin",
    ... )
    >>> storage = AdminStorageBackend(config)
    >>>
    >>> # Upload a file
    >>> path = await storage.upload(
    ...     file_content=b"...",
    ...     filename="document.pdf",
    ...     model_name="user",
    ...     field_name="avatar",
    ... )
    >>>
    >>> # Get public URL
    >>> url = storage.get_public_url(path)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from litestar_admin.contrib.storages.config import StorageBackendType, StorageConfig

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Sequence

    from litestar_admin.contrib.storages.thumbnails import ThumbnailSize

__all__ = [
    "AdminStorageBackend",
    "StorageBackendProtocol",
    "UploadResult",
]


@dataclass
class UploadResult:
    """Result of a file upload operation.

    Attributes:
        storage_path: The path where the main file was stored.
        public_url: The public URL to access the file.
        thumbnail_path: Path to the generated thumbnail (if applicable).
        thumbnail_url: URL to access the thumbnail (if applicable).
        additional_thumbnails: Dictionary of additional thumbnail paths by size suffix.
    """

    storage_path: str
    public_url: str
    thumbnail_path: str | None = None
    thumbnail_url: str | None = None
    additional_thumbnails: dict[str, str] | None = None


@runtime_checkable
class StorageBackendProtocol(Protocol):
    """Protocol for storage backend implementations.

    This protocol defines the interface that storage backends must implement
    to be compatible with the admin storage system.
    """

    async def write(self, path: str, content: bytes) -> None:
        """Write content to a file.

        Args:
            path: The path to write to.
            content: The file content as bytes.
        """
        ...

    async def read(self, path: str) -> bytes:
        """Read content from a file.

        Args:
            path: The path to read from.

        Returns:
            The file content as bytes.
        """
        ...

    async def delete(self, path: str) -> None:
        """Delete a file.

        Args:
            path: The path to delete.
        """
        ...

    async def exists(self, path: str) -> bool:
        """Check if a file exists.

        Args:
            path: The path to check.

        Returns:
            True if the file exists, False otherwise.
        """
        ...


class AdminStorageBackend:
    """Admin-specific storage backend wrapper.

    This class wraps litestar-storages backends with admin-specific
    functionality like path generation, validation, and URL handling.

    Attributes:
        config: Storage configuration.
        _backend: The underlying litestar-storages backend instance.

    Example:
        >>> config = StorageConfig(
        ...     backend=StorageBackendType.LOCAL,
        ...     local_base_path="/uploads",
        ...     upload_path="admin",
        ... )
        >>> storage = AdminStorageBackend(config)
        >>> await storage.upload(content, "file.pdf", "document", "attachment")
    """

    def __init__(self, config: StorageConfig) -> None:
        """Initialize the admin storage backend.

        Args:
            config: Storage configuration options.
        """
        self.config = config
        self._backend: Any = None

    def _get_backend(self) -> Any:
        """Get or create the underlying storage backend.

        Returns:
            The litestar-storages backend instance.

        Raises:
            ImportError: If litestar-storages is not installed.
            ValueError: If the backend type is not supported.
        """
        if self._backend is not None:
            return self._backend

        try:
            from litestar_storages import FileSystemStorage, MemoryStorage
        except ImportError as e:
            msg = (
                "litestar-storages is required for file storage support. "
                "Install it with: pip install 'litestar-admin[storage]'"
            )
            raise ImportError(msg) from e

        backend_type = self.config.backend
        kwargs = self.config.get_storage_kwargs()

        if backend_type == StorageBackendType.LOCAL:
            self._backend = FileSystemStorage(path=kwargs.get("path", "."))

        elif backend_type == StorageBackendType.MEMORY:
            self._backend = MemoryStorage()

        elif backend_type == StorageBackendType.S3:
            try:
                from litestar_storages import S3Storage
            except ImportError as e:
                msg = "S3 storage requires additional dependencies. Install with: pip install 'litestar-storages[s3]'"
                raise ImportError(msg) from e
            self._backend = S3Storage(**kwargs)

        elif backend_type == StorageBackendType.GCS:
            try:
                from litestar_storages import GCSStorage
            except ImportError as e:
                msg = "GCS storage requires additional dependencies. Install with: pip install 'litestar-storages[gcs]'"
                raise ImportError(msg) from e
            self._backend = GCSStorage(**kwargs)

        else:
            msg = f"Unsupported storage backend type: {backend_type}"
            raise ValueError(msg)

        return self._backend

    async def upload(
        self,
        file_content: bytes | AsyncIterator[bytes],
        filename: str,
        model_name: str,
        field_name: str,
        *,
        validate: bool = True,
    ) -> str:
        """Upload a file to storage.

        Args:
            file_content: The file content as bytes or async iterator.
            filename: The original filename.
            model_name: The name of the model this file belongs to.
            field_name: The name of the field this file belongs to.
            validate: Whether to validate the file before uploading.

        Returns:
            The storage path of the uploaded file.

        Raises:
            ValueError: If validation fails (extension or size not allowed).
            ImportError: If litestar-storages is not installed.
        """
        from litestar_admin.contrib.storages.utils import (
            get_file_extension,
            get_storage_path,
            sanitize_filename,
        )

        # Handle async iterator by reading all content
        if not isinstance(file_content, bytes):
            chunks = []
            async for chunk in file_content:
                chunks.append(chunk)
            content = b"".join(chunks)
        else:
            content = file_content

        # Validate file if requested
        if validate:
            extension = get_file_extension(filename)
            if not self.config.is_extension_allowed(extension):
                msg = f"File extension '{extension}' is not allowed"
                raise ValueError(msg)

            if not self.config.is_size_allowed(len(content)):
                msg = f"File size {len(content)} exceeds maximum allowed size {self.config.max_file_size}"
                raise ValueError(msg)

        # Generate storage path
        safe_filename = sanitize_filename(filename)
        storage_path = get_storage_path(
            model_name=model_name,
            field_name=field_name,
            filename=safe_filename,
            base_path=self.config.upload_path,
        )

        # Upload to backend
        backend = self._get_backend()
        await backend.write(storage_path, content)

        return storage_path

    async def read(self, path: str) -> bytes:
        """Read a file from storage.

        Args:
            path: The storage path to read from.

        Returns:
            The file content as bytes.

        Raises:
            FileNotFoundError: If the file does not exist.
            ImportError: If litestar-storages is not installed.
        """
        backend = self._get_backend()
        return await backend.read(path)

    async def delete(self, path: str) -> None:
        """Delete a file from storage.

        Args:
            path: The storage path to delete.

        Raises:
            ImportError: If litestar-storages is not installed.
        """
        backend = self._get_backend()
        await backend.delete(path)

    async def exists(self, path: str) -> bool:
        """Check if a file exists in storage.

        Args:
            path: The storage path to check.

        Returns:
            True if the file exists, False otherwise.

        Raises:
            ImportError: If litestar-storages is not installed.
        """
        backend = self._get_backend()
        return await backend.exists(path)

    def get_public_url(self, path: str) -> str:
        """Get the public URL for a stored file.

        Args:
            path: The storage path of the file.

        Returns:
            The public URL for accessing the file.
        """
        from litestar_admin.contrib.storages.utils import get_public_url

        return get_public_url(path, self.config)

    async def upload_with_thumbnail(
        self,
        file_content: bytes,
        filename: str,
        model_name: str,
        field_name: str,
        *,
        validate: bool = True,
    ) -> tuple[str, str | None]:
        """Upload an image file with an optional thumbnail.

        Args:
            file_content: The file content as bytes.
            filename: The original filename.
            model_name: The name of the model this file belongs to.
            field_name: The name of the field this file belongs to.
            validate: Whether to validate the file before uploading.

        Returns:
            Tuple of (main_path, thumbnail_path). thumbnail_path is None if
            thumbnails are disabled or if the file is not an image.

        Raises:
            ValueError: If validation fails.
            ImportError: If litestar-storages or PIL is not installed.
        """
        from litestar_admin.contrib.storages.thumbnails import ThumbnailGenerator
        from litestar_admin.contrib.storages.utils import (
            get_file_extension,
            is_image_extension,
        )

        # Upload the main file
        main_path = await self.upload(
            file_content=file_content,
            filename=filename,
            model_name=model_name,
            field_name=field_name,
            validate=validate,
        )

        # Check if thumbnail generation is enabled and file is an image
        thumbnail_path: str | None = None
        extension = get_file_extension(filename)

        if self.config.thumbnails.enabled and is_image_extension(extension):
            # Use ThumbnailGenerator for consistent thumbnail generation
            generator = ThumbnailGenerator(
                default_quality=self.config.thumbnails.quality,
                default_format=self.config.thumbnails.format,
            )

            size = (self.config.thumbnails.width, self.config.thumbnails.height)
            result = await generator.generate_async(
                file_content,
                size=size,
                format=self.config.thumbnails.format,
                quality=self.config.thumbnails.quality,
            )

            if result:
                # Generate thumbnail filename
                base_name = filename.rsplit(".", 1)[0]
                thumb_suffix = self.config.thumbnails.suffix
                thumb_format = self.config.thumbnails.format
                thumb_filename = f"{base_name}{thumb_suffix}.{thumb_format}"

                thumbnail_path = await self.upload(
                    file_content=result.data,
                    filename=thumb_filename,
                    model_name=model_name,
                    field_name=f"{field_name}_thumbnail",
                    validate=False,  # Already validated the original
                )

        return main_path, thumbnail_path

    async def upload_with_thumbnails(
        self,
        file_content: bytes,
        filename: str,
        model_name: str,
        field_name: str,
        sizes: Sequence[ThumbnailSize],
        *,
        validate: bool = True,
        format: str | None = None,  # noqa: A002
        quality: int | None = None,
    ) -> UploadResult:
        """Upload an image file with multiple thumbnail sizes.

        Args:
            file_content: The file content as bytes.
            filename: The original filename.
            model_name: The name of the model this file belongs to.
            field_name: The name of the field this file belongs to.
            sizes: Sequence of ThumbnailSize configurations.
            validate: Whether to validate the file before uploading.
            format: Output format for thumbnails (webp, jpeg, png).
            quality: Quality for JPEG/WebP thumbnails (1-100).

        Returns:
            UploadResult with main file path and all thumbnail paths.

        Raises:
            ValueError: If validation fails.
            ImportError: If litestar-storages or PIL is not installed.

        Example:
            >>> from litestar_admin.contrib.storages.thumbnails import ThumbnailSize
            >>> sizes = [
            ...     ThumbnailSize(100, 100, "_small"),
            ...     ThumbnailSize(300, 300, "_medium"),
            ...     ThumbnailSize(600, 600, "_large"),
            ... ]
            >>> result = await storage.upload_with_thumbnails(
            ...     content, "photo.jpg", "product", "image", sizes
            ... )
        """
        from litestar_admin.contrib.storages.thumbnails import ThumbnailGenerator
        from litestar_admin.contrib.storages.utils import (
            get_file_extension,
            is_image_extension,
        )

        # Upload the main file
        main_path = await self.upload(
            file_content=file_content,
            filename=filename,
            model_name=model_name,
            field_name=field_name,
            validate=validate,
        )

        public_url = self.get_public_url(main_path)
        extension = get_file_extension(filename)

        # Initialize result
        result = UploadResult(
            storage_path=main_path,
            public_url=public_url,
        )

        # Generate thumbnails if this is an image
        if not is_image_extension(extension) or not sizes:
            return result

        # Use configured or provided format/quality
        output_format = format or self.config.thumbnails.format
        output_quality = quality if quality is not None else self.config.thumbnails.quality

        generator = ThumbnailGenerator(
            default_quality=output_quality,
            default_format=output_format,
        )

        # Generate all thumbnails
        thumbnails = await generator.generate_multiple_async(
            file_content,
            sizes=sizes,
            format=output_format,
            quality=output_quality,
        )

        # Upload thumbnails and collect paths
        additional_thumbnails: dict[str, str] = {}
        first_thumbnail_path: str | None = None
        first_thumbnail_url: str | None = None

        for suffix, thumb_result in thumbnails.items():
            # Generate thumbnail filename
            base_name = filename.rsplit(".", 1)[0]
            thumb_filename = f"{base_name}{suffix}.{output_format}"

            thumb_path = await self.upload(
                file_content=thumb_result.data,
                filename=thumb_filename,
                model_name=model_name,
                field_name=f"{field_name}_thumb{suffix}",
                validate=False,
            )

            additional_thumbnails[suffix] = thumb_path

            # Track the first thumbnail as the default
            if first_thumbnail_path is None:
                first_thumbnail_path = thumb_path
                first_thumbnail_url = self.get_public_url(thumb_path)

        # Update result with thumbnail info
        result.thumbnail_path = first_thumbnail_path
        result.thumbnail_url = first_thumbnail_url
        result.additional_thumbnails = additional_thumbnails if additional_thumbnails else None

        return result

    async def generate_thumbnail(
        self,
        path: str,
        size: tuple[int, int],
        format: str | None = None,  # noqa: A002
        quality: int | None = None,
        *,
        store: bool = True,
    ) -> tuple[bytes, str | None]:
        """Generate a thumbnail for an existing stored image.

        This method reads an existing image from storage and generates
        a thumbnail at the specified size.

        Args:
            path: The storage path of the source image.
            size: The (width, height) for the thumbnail.
            format: Output format (webp, jpeg, png).
            quality: Quality for JPEG/WebP (1-100).
            store: Whether to store the thumbnail alongside the original.

        Returns:
            Tuple of (thumbnail_bytes, thumbnail_path). thumbnail_path is None
            if store=False or if storage fails.

        Raises:
            FileNotFoundError: If the source file does not exist.
            ValueError: If the file is not a supported image format.
        """
        from litestar_admin.contrib.storages.thumbnails import ThumbnailGenerator

        # Check if file exists
        if not await self.exists(path):
            msg = f"File not found: {path}"
            raise FileNotFoundError(msg)

        # Check if it's an image
        if not ThumbnailGenerator.is_supported_image(path):
            msg = f"Not a supported image format: {path}"
            raise ValueError(msg)

        # Read the image
        image_data = await self.read(path)

        # Use configured or provided format/quality
        output_format = format or self.config.thumbnails.format
        output_quality = quality if quality is not None else self.config.thumbnails.quality

        generator = ThumbnailGenerator(
            default_quality=output_quality,
            default_format=output_format,
        )

        # Generate thumbnail
        result = await generator.generate_async(
            image_data,
            size=size,
            format=output_format,
            quality=output_quality,
        )

        if result is None:
            msg = "Failed to generate thumbnail"
            raise ValueError(msg)

        thumbnail_path: str | None = None

        if store:
            # Generate thumbnail path
            thumb_path = generator.get_thumbnail_path(path, size, output_format)

            # Store the thumbnail
            backend = self._get_backend()
            await backend.write(thumb_path, result.data)
            thumbnail_path = thumb_path

        return result.data, thumbnail_path

    async def get_or_generate_thumbnail(
        self,
        path: str,
        size: tuple[int, int],
        format: str | None = None,  # noqa: A002
        quality: int | None = None,
    ) -> tuple[bytes, str]:
        """Get an existing thumbnail or generate one if it doesn't exist.

        This method first checks if a thumbnail already exists at the expected
        path. If not, it generates and stores one.

        Args:
            path: The storage path of the source image.
            size: The (width, height) for the thumbnail.
            format: Output format (webp, jpeg, png).
            quality: Quality for JPEG/WebP (1-100).

        Returns:
            Tuple of (thumbnail_bytes, thumbnail_path).

        Raises:
            FileNotFoundError: If the source file does not exist.
            ValueError: If the file is not a supported image format.
        """
        from litestar_admin.contrib.storages.thumbnails import ThumbnailGenerator

        output_format = format or self.config.thumbnails.format

        generator = ThumbnailGenerator(
            default_quality=quality or self.config.thumbnails.quality,
            default_format=output_format,
        )

        # Check if thumbnail already exists
        thumb_path = generator.get_thumbnail_path(path, size, output_format)

        if await self.exists(thumb_path):
            # Return existing thumbnail
            content = await self.read(thumb_path)
            return content, thumb_path

        # Generate new thumbnail
        content, stored_path = await self.generate_thumbnail(path, size, format, quality, store=True)

        return content, stored_path or thumb_path
