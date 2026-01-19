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

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from litestar_admin.contrib.storages.config import StorageBackendType, StorageConfig

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

__all__ = [
    "AdminStorageBackend",
    "StorageBackendProtocol",
]


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
                msg = (
                    "S3 storage requires additional dependencies. "
                    "Install with: pip install 'litestar-storages[s3]'"
                )
                raise ImportError(msg) from e
            self._backend = S3Storage(**kwargs)

        elif backend_type == StorageBackendType.GCS:
            try:
                from litestar_storages import GCSStorage
            except ImportError as e:
                msg = (
                    "GCS storage requires additional dependencies. "
                    "Install with: pip install 'litestar-storages[gcs]'"
                )
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
        from litestar_admin.contrib.storages.utils import (
            generate_thumbnail,
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
            # Generate thumbnail
            thumbnail_content = generate_thumbnail(
                file_content,
                width=self.config.thumbnails.width,
                height=self.config.thumbnails.height,
                quality=self.config.thumbnails.quality,
                format_=self.config.thumbnails.format,
            )

            if thumbnail_content:
                # Generate thumbnail filename
                base_name = filename.rsplit(".", 1)[0]
                thumb_suffix = self.config.thumbnails.suffix
                thumb_format = self.config.thumbnails.format
                thumb_filename = f"{base_name}{thumb_suffix}.{thumb_format}"

                thumbnail_path = await self.upload(
                    file_content=thumbnail_content,
                    filename=thumb_filename,
                    model_name=model_name,
                    field_name=f"{field_name}_thumbnail",
                    validate=False,  # Already validated the original
                )

        return main_path, thumbnail_path
