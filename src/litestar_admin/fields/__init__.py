"""Field types for litestar-admin model views.

This module provides specialized field types for handling various input types
in admin forms, including file uploads, image fields, and rich text editors.

Example:
    Using file fields in a model view::

        from litestar_admin import ModelView
        from litestar_admin.fields import FileField, ImageField
        from myapp.models import Product


        class ProductAdmin(ModelView, model=Product):
            file_fields = [
                FileField(
                    name="manual",
                    allowed_extensions=["pdf"],
                    max_size=20 * 1024 * 1024,  # 20MB
                    description="Product manual in PDF format",
                ),
                ImageField(
                    name="photo",
                    generate_thumbnail=True,
                    thumbnail_size=(300, 300),
                ),
            ]

    Using rich text fields in a model view::

        from litestar_admin import ModelView
        from litestar_admin.fields import RichTextField
        from myapp.models import BlogPost


        class BlogPostAdmin(ModelView, model=BlogPost):
            rich_text_fields = [
                RichTextField(
                    name="content",
                    description="Main article content",
                    toolbar=["bold", "italic", "link", "heading"],
                    max_length=50000,
                ),
            ]
"""

from __future__ import annotations

from litestar_admin.fields.file import (
    DEFAULT_FILE_EXTENSIONS,
    DEFAULT_IMAGE_EXTENSIONS,
    DEFAULT_MAX_FILE_SIZE,
    DEFAULT_THUMBNAIL_SIZE,
    FileField,
    FileFieldValidationError,
    FileUploadResult,
    ImageField,
    get_file_extension,
    is_image_extension,
    validate_file_field,
    validate_multiple_files,
)
from litestar_admin.fields.rich_text import (
    DEFAULT_RICH_TEXT_TOOLBAR,
    DEFAULT_SAFE_HTML_TAGS,
    RichTextField,
    RichTextFieldValidationError,
    validate_rich_text_field,
)

__all__ = [
    # Field types
    "FileField",
    "ImageField",
    "RichTextField",
    # Results and errors
    "FileFieldValidationError",
    "FileUploadResult",
    "RichTextFieldValidationError",
    # Validation functions
    "get_file_extension",
    "is_image_extension",
    "validate_file_field",
    "validate_multiple_files",
    "validate_rich_text_field",
    # Constants
    "DEFAULT_FILE_EXTENSIONS",
    "DEFAULT_IMAGE_EXTENSIONS",
    "DEFAULT_MAX_FILE_SIZE",
    "DEFAULT_RICH_TEXT_TOOLBAR",
    "DEFAULT_SAFE_HTML_TAGS",
    "DEFAULT_THUMBNAIL_SIZE",
]
