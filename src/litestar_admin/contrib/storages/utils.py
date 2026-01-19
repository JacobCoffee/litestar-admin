"""Storage utilities for litestar-admin.

This module provides utility functions for file validation, path generation,
and URL handling in the admin storage system.

Example:
    >>> from litestar_admin.contrib.storages.utils import (
    ...     get_storage_path,
    ...     get_public_url,
    ...     validate_file,
    ... )
    >>>
    >>> path = get_storage_path("user", "avatar", "photo.jpg")
    >>> print(path)
    'uploads/admin/user/avatar/550e8400-e29b-41d4-a716-446655440000_photo.jpg'
"""

from __future__ import annotations

import hashlib
import re
import secrets
import unicodedata
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from litestar_admin.contrib.storages.config import StorageConfig

__all__ = [
    "generate_thumbnail",
    "get_file_extension",
    "get_public_url",
    "get_storage_path",
    "is_image_extension",
    "sanitize_filename",
    "validate_file",
]


# Image extensions that support thumbnail generation
IMAGE_EXTENSIONS: frozenset[str] = frozenset(
    {
        "jpg",
        "jpeg",
        "png",
        "gif",
        "webp",
        "bmp",
        "tiff",
        "tif",
    }
)


def get_file_extension(filename: str) -> str:
    """Extract the file extension from a filename.

    Args:
        filename: The filename to extract the extension from.

    Returns:
        The file extension (lowercase, without leading dot), or empty string
        if no extension is found.

    Example:
        >>> get_file_extension("document.PDF")
        'pdf'
        >>> get_file_extension("file")
        ''
    """
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()


def is_image_extension(extension: str) -> bool:
    """Check if an extension is a supported image format.

    Args:
        extension: The file extension to check (with or without leading dot).

    Returns:
        True if the extension is a supported image format, False otherwise.

    Example:
        >>> is_image_extension("jpg")
        True
        >>> is_image_extension("pdf")
        False
    """
    ext = extension.lower().lstrip(".")
    return ext in IMAGE_EXTENSIONS


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename for safe storage.

    This function removes or replaces potentially dangerous characters,
    normalizes unicode, and ensures the filename is safe for use in file paths.

    Args:
        filename: The original filename to sanitize.

    Returns:
        A sanitized filename safe for storage.

    Example:
        >>> sanitize_filename("My Document (1).pdf")
        'my_document_1.pdf'
        >>> sanitize_filename("../../etc/passwd")
        'etc_passwd'
    """
    # Normalize unicode characters
    filename = unicodedata.normalize("NFKD", filename)
    filename = filename.encode("ascii", "ignore").decode("ascii")

    # Get the extension before processing
    if "." in filename:
        name, ext = filename.rsplit(".", 1)
        ext = ext.lower()
    else:
        name = filename
        ext = ""

    # Remove path separators and directory traversal
    name = name.replace("/", "_").replace("\\", "_").replace("..", "_")

    # Replace spaces and special characters with underscores
    name = re.sub(r"[^\w\-]", "_", name.lower())

    # Remove consecutive underscores
    name = re.sub(r"_+", "_", name)

    # Remove leading/trailing underscores
    name = name.strip("_")

    # Ensure we have a valid name
    if not name:
        name = "unnamed"

    # Limit filename length (leaving room for extension and unique prefix)
    max_name_length = 100
    if len(name) > max_name_length:
        name = name[:max_name_length]

    # Reconstruct filename with extension
    if ext:
        return f"{name}.{ext}"
    return name


def get_storage_path(
    model_name: str,
    field_name: str,
    filename: str,
    base_path: str = "uploads/admin",
    *,
    include_date: bool = True,
    include_unique_prefix: bool = True,
) -> str:
    """Generate a storage path for a file.

    Creates a hierarchical path structure:
    ``{base_path}/{model_name}/{field_name}/{date?}/{unique_prefix?}_{filename}``

    Args:
        model_name: The name of the model this file belongs to.
        field_name: The name of the field this file belongs to.
        filename: The sanitized filename.
        base_path: The base path prefix for uploads.
        include_date: Whether to include date-based directory structure.
        include_unique_prefix: Whether to add a unique prefix to prevent overwrites.

    Returns:
        The full storage path for the file.

    Example:
        >>> get_storage_path("user", "avatar", "photo.jpg")
        'uploads/admin/user/avatar/2024/01/a1b2c3d4_photo.jpg'
        >>> get_storage_path("user", "avatar", "photo.jpg", include_date=False)
        'uploads/admin/user/avatar/a1b2c3d4_photo.jpg'
    """
    # Sanitize model and field names
    safe_model = re.sub(r"[^\w\-]", "_", model_name.lower())
    safe_field = re.sub(r"[^\w\-]", "_", field_name.lower())

    # Build path components
    path_parts = [base_path.strip("/"), safe_model, safe_field]

    # Add date-based structure
    if include_date:
        now = datetime.now(tz=timezone.utc)
        path_parts.extend([str(now.year), f"{now.month:02d}"])

    # Add unique prefix to filename
    if include_unique_prefix:
        unique_prefix = secrets.token_hex(4)
        filename = f"{unique_prefix}_{filename}"

    path_parts.append(filename)

    return "/".join(path_parts)


def get_public_url(storage_path: str, config: StorageConfig) -> str:
    """Get the public URL for a stored file.

    Args:
        storage_path: The storage path of the file.
        config: The storage configuration.

    Returns:
        The public URL for accessing the file.

    Example:
        >>> config = StorageConfig(public_url_base="https://cdn.example.com")
        >>> get_public_url("uploads/user/avatar/photo.jpg", config)
        'https://cdn.example.com/uploads/user/avatar/photo.jpg'
    """
    # Normalize the path
    path = storage_path.lstrip("/")

    if config.public_url_base:
        base = config.public_url_base.rstrip("/")
        return f"{base}/{path}"

    # Fall back to a relative path
    return f"/{path}"


def validate_file(
    filename: str,
    size: int,
    config: StorageConfig,
) -> tuple[bool, str | None]:
    """Validate a file against the storage configuration.

    Args:
        filename: The filename to validate.
        size: The file size in bytes.
        config: The storage configuration.

    Returns:
        Tuple of (is_valid, error_message). error_message is None if valid.

    Example:
        >>> config = StorageConfig(max_file_size=1024, allowed_extensions=["pdf"])
        >>> validate_file("doc.pdf", 512, config)
        (True, None)
        >>> validate_file("doc.exe", 512, config)
        (False, "File extension 'exe' is not allowed")
    """
    # Check extension
    extension = get_file_extension(filename)
    if not config.is_extension_allowed(extension):
        allowed = ", ".join(sorted(config.allowed_extensions_set))
        return False, f"File extension '{extension}' is not allowed. Allowed: {allowed}"

    # Check size
    if size <= 0:
        return False, "File size must be greater than 0"

    if not config.is_size_allowed(size):
        max_mb = config.max_file_size / (1024 * 1024)
        return False, f"File size exceeds maximum allowed size of {max_mb:.1f} MB"

    return True, None


def generate_thumbnail(
    image_content: bytes,
    width: int = 200,
    height: int = 200,
    quality: int = 85,
    format_: str = "jpeg",
) -> bytes | None:
    """Generate a thumbnail from image content.

    Uses PIL/Pillow to resize the image while maintaining aspect ratio.

    Args:
        image_content: The original image content as bytes.
        width: Maximum thumbnail width in pixels.
        height: Maximum thumbnail height in pixels.
        quality: JPEG quality (1-100).
        format_: Output format (jpeg, png, webp).

    Returns:
        The thumbnail image content as bytes, or None if generation fails.

    Example:
        >>> with open("photo.jpg", "rb") as f:
        ...     content = f.read()
        >>> thumb = generate_thumbnail(content, width=100, height=100)
    """
    try:
        from io import BytesIO

        from PIL import Image
    except ImportError:
        # PIL not installed, thumbnails not available
        return None

    try:
        # Open the image
        img = Image.open(BytesIO(image_content))

        # Convert to RGB if necessary (for JPEG output)
        if format_.lower() in ("jpeg", "jpg") and img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
            img = background

        # Create thumbnail (maintains aspect ratio)
        img.thumbnail((width, height), Image.Resampling.LANCZOS)

        # Save to bytes
        output = BytesIO()
        save_format = format_.upper()
        if save_format == "JPG":
            save_format = "JPEG"

        save_kwargs: dict[str, int | bool] = {}
        if save_format == "JPEG":
            save_kwargs["quality"] = quality
            save_kwargs["optimize"] = True
        elif save_format == "PNG":
            save_kwargs["optimize"] = True
        elif save_format == "WEBP":
            save_kwargs["quality"] = quality

        img.save(output, format=save_format, **save_kwargs)
        return output.getvalue()

    except Exception:
        # Any error in processing returns None
        return None


def get_content_hash(content: bytes) -> str:
    """Calculate SHA-256 hash of file content.

    Useful for deduplication or content-addressed storage.

    Args:
        content: The file content as bytes.

    Returns:
        The hexadecimal SHA-256 hash of the content.

    Example:
        >>> get_content_hash(b"Hello, World!")
        'dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f'
    """
    return hashlib.sha256(content).hexdigest()
