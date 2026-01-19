"""File field types for model view forms.

This module provides field types for handling file uploads in admin forms,
integrating with the storage backend system.

Example:
    Basic file field usage::

        from litestar_admin import ModelView
        from litestar_admin.fields import FileField, ImageField
        from myapp.models import Document


        class DocumentAdmin(ModelView, model=Document):
            file_fields = [
                FileField(
                    name="attachment",
                    allowed_extensions=["pdf", "doc", "docx"],
                    max_size=10 * 1024 * 1024,  # 10MB
                ),
                ImageField(
                    name="thumbnail",
                    generate_thumbnail=True,
                    thumbnail_size=(200, 200),
                ),
            ]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from litestar.datastructures import UploadFile

__all__ = [
    "FileField",
    "FileFieldValidationError",
    "FileUploadResult",
    "ImageField",
    "validate_file_field",
]

# Default allowed extensions for general files
DEFAULT_FILE_EXTENSIONS: frozenset[str] = frozenset({
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
    "rtf",
    "odt",
    "ods",
    "odp",
    # Archives
    "zip",
    "tar",
    "gz",
    "7z",
    "rar",
    # Text/Code
    "json",
    "xml",
    "yaml",
    "yml",
    "md",
    "html",
    "css",
    "js",
})

# Default allowed extensions for images
DEFAULT_IMAGE_EXTENSIONS: frozenset[str] = frozenset({
    "jpg",
    "jpeg",
    "png",
    "gif",
    "webp",
    "svg",
    "bmp",
    "ico",
    "tiff",
    "tif",
})

# Default maximum file size (10 MB)
DEFAULT_MAX_FILE_SIZE: int = 10 * 1024 * 1024

# Default thumbnail size
DEFAULT_THUMBNAIL_SIZE: tuple[int, int] = (200, 200)


@dataclass
class FileField:
    """File upload field for model views.

    This class defines a file upload field that can be used in admin forms.
    It provides validation rules for file uploads including allowed extensions,
    maximum file size, and optional path prefix.

    Attributes:
        name: The field name, corresponding to the model attribute.
        allowed_extensions: List of allowed file extensions (without dots).
            If None, uses DEFAULT_FILE_EXTENSIONS.
        max_size: Maximum file size in bytes. If None, uses DEFAULT_MAX_FILE_SIZE.
        upload_to: Storage path prefix for uploaded files. If None, uses
            the model name and field name to generate a path.
        required: Whether the field is required for form submission.
        multiple: Whether to allow multiple file uploads for this field.
        description: Optional description displayed in the form.
        label: Optional custom label for the form field.

    Example:
        >>> file_field = FileField(
        ...     name="document",
        ...     allowed_extensions=["pdf", "docx"],
        ...     max_size=5 * 1024 * 1024,  # 5MB
        ...     required=True,
        ... )
    """

    name: str
    allowed_extensions: list[str] | None = None
    max_size: int | None = None
    upload_to: str | None = None
    required: bool = False
    multiple: bool = False
    description: str | None = None
    label: str | None = None

    @property
    def allowed_extensions_set(self) -> frozenset[str]:
        """Get allowed extensions as a frozenset.

        Returns:
            Frozenset of allowed file extensions (lowercase, without dots).
        """
        if self.allowed_extensions is None:
            return DEFAULT_FILE_EXTENSIONS
        return frozenset(ext.lower().lstrip(".") for ext in self.allowed_extensions)

    @property
    def max_file_size(self) -> int:
        """Get the maximum file size in bytes.

        Returns:
            Maximum file size in bytes.
        """
        return self.max_size if self.max_size is not None else DEFAULT_MAX_FILE_SIZE

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

    def to_dict(self) -> dict[str, Any]:
        """Convert the field to a dictionary for API responses.

        Returns:
            Dictionary representation of the field configuration.
        """
        return {
            "name": self.name,
            "type": "file",
            "allowed_extensions": list(self.allowed_extensions_set),
            "max_size": self.max_file_size,
            "upload_to": self.upload_to,
            "required": self.required,
            "multiple": self.multiple,
            "description": self.description,
            "label": self.label or self.name.replace("_", " ").title(),
        }


@dataclass
class ImageField(FileField):
    """Image upload field with thumbnail generation support.

    This class extends FileField with image-specific functionality including
    automatic thumbnail generation and image-specific allowed extensions.

    Attributes:
        generate_thumbnail: Whether to generate a thumbnail for uploaded images.
        thumbnail_size: Tuple of (width, height) for thumbnails.
        allowed_extensions: List of allowed image extensions. Defaults to
            common image formats if not specified.

    Example:
        >>> image_field = ImageField(
        ...     name="avatar",
        ...     generate_thumbnail=True,
        ...     thumbnail_size=(150, 150),
        ...     max_size=5 * 1024 * 1024,  # 5MB
        ... )
    """

    generate_thumbnail: bool = True
    thumbnail_size: tuple[int, int] = field(default_factory=lambda: DEFAULT_THUMBNAIL_SIZE)
    allowed_extensions: list[str] | None = field(
        default_factory=lambda: list(DEFAULT_IMAGE_EXTENSIONS)
    )

    @property
    def allowed_extensions_set(self) -> frozenset[str]:
        """Get allowed extensions as a frozenset.

        Returns:
            Frozenset of allowed image extensions (lowercase, without dots).
        """
        if self.allowed_extensions is None:
            return DEFAULT_IMAGE_EXTENSIONS
        return frozenset(ext.lower().lstrip(".") for ext in self.allowed_extensions)

    def to_dict(self) -> dict[str, Any]:
        """Convert the field to a dictionary for API responses.

        Returns:
            Dictionary representation of the field configuration.
        """
        base = super().to_dict()
        base["type"] = "image"
        base["generate_thumbnail"] = self.generate_thumbnail
        base["thumbnail_size"] = list(self.thumbnail_size)
        return base


@dataclass
class FileFieldValidationError:
    """Validation error for file field uploads.

    Attributes:
        field_name: The name of the field that failed validation.
        error: The error message.
        error_code: A machine-readable error code.
    """

    field_name: str
    error: str
    error_code: str


@dataclass
class FileUploadResult:
    """Result of a file upload operation.

    Attributes:
        field_name: The name of the file field.
        storage_path: The path where the file was stored.
        original_filename: The original filename from the upload.
        file_size: The size of the file in bytes.
        content_type: The MIME type of the file.
        thumbnail_path: Path to the generated thumbnail (for images).
    """

    field_name: str
    storage_path: str
    original_filename: str
    file_size: int
    content_type: str | None = None
    thumbnail_path: str | None = None


def validate_file_field(
    file: UploadFile,
    field_config: FileField,
    *,
    file_content: bytes | None = None,
) -> list[FileFieldValidationError]:
    """Validate an uploaded file against a file field configuration.

    This function checks the file against the field's validation rules including:
    - File extension validation
    - File size validation
    - Required field validation

    Args:
        file: The uploaded file from the request.
        field_config: The FileField or ImageField configuration.
        file_content: Optional pre-read file content for size validation.
            If not provided, size will be checked from the file object.

    Returns:
        List of validation errors. Empty list if validation passes.

    Example:
        >>> from litestar.datastructures import UploadFile
        >>> field = FileField(name="doc", allowed_extensions=["pdf"], max_size=1024)
        >>> errors = validate_file_field(upload_file, field)
        >>> if errors:
        ...     for error in errors:
        ...         print(f"{error.field_name}: {error.error}")
    """
    errors: list[FileFieldValidationError] = []

    # Check if file is provided for required fields
    if field_config.required and (not file or not file.filename):
        errors.append(
            FileFieldValidationError(
                field_name=field_config.name,
                error="This field is required",
                error_code="required",
            )
        )
        return errors

    # If no file provided and not required, validation passes
    if not file or not file.filename:
        return errors

    # Validate extension
    filename = file.filename
    if "." not in filename:
        errors.append(
            FileFieldValidationError(
                field_name=field_config.name,
                error="File must have an extension",
                error_code="no_extension",
            )
        )
    else:
        extension = filename.rsplit(".", 1)[-1].lower()
        if not field_config.is_extension_allowed(extension):
            allowed = ", ".join(sorted(field_config.allowed_extensions_set))
            errors.append(
                FileFieldValidationError(
                    field_name=field_config.name,
                    error=f"File extension '.{extension}' is not allowed. Allowed: {allowed}",
                    error_code="invalid_extension",
                )
            )

    # Validate size
    file_size = len(file_content) if file_content is not None else getattr(file, "size", 0)

    if file_size > 0 and not field_config.is_size_allowed(file_size):
        max_mb = field_config.max_file_size / (1024 * 1024)
        size_mb = file_size / (1024 * 1024)
        errors.append(
            FileFieldValidationError(
                field_name=field_config.name,
                error=f"File size ({size_mb:.1f} MB) exceeds maximum allowed size ({max_mb:.1f} MB)",
                error_code="file_too_large",
            )
        )

    return errors


def validate_multiple_files(
    files: list[UploadFile],
    field_config: FileField,
    *,
    file_contents: list[bytes] | None = None,
) -> list[FileFieldValidationError]:
    """Validate multiple uploaded files against a file field configuration.

    Args:
        files: List of uploaded files from the request.
        field_config: The FileField or ImageField configuration.
        file_contents: Optional pre-read file contents for size validation.

    Returns:
        List of validation errors. Empty list if all files pass validation.
    """
    errors: list[FileFieldValidationError] = []

    if not field_config.multiple and len(files) > 1:
        errors.append(
            FileFieldValidationError(
                field_name=field_config.name,
                error="Multiple files not allowed for this field",
                error_code="multiple_not_allowed",
            )
        )
        return errors

    if field_config.required and not files:
        errors.append(
            FileFieldValidationError(
                field_name=field_config.name,
                error="This field is required",
                error_code="required",
            )
        )
        return errors

    for i, file in enumerate(files):
        content = file_contents[i] if file_contents and i < len(file_contents) else None
        file_errors = validate_file_field(file, field_config, file_content=content)
        errors.extend(file_errors)

    return errors


def get_file_extension(filename: str) -> str:
    """Extract the file extension from a filename.

    Args:
        filename: The filename to extract the extension from.

    Returns:
        The file extension (lowercase, without leading dot), or empty string
        if no extension is found.
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
    """
    ext = extension.lower().lstrip(".")
    return ext in DEFAULT_IMAGE_EXTENSIONS
