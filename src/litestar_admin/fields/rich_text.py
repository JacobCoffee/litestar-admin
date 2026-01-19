"""Rich text field types for model view forms.

This module provides field types for handling rich text content in admin forms,
integrating with the Tiptap-based rich text editor on the frontend.

Example:
    Basic rich text field usage::

        from litestar_admin import ModelView
        from litestar_admin.fields import RichTextField
        from myapp.models import BlogPost


        class BlogPostAdmin(ModelView, model=BlogPost):
            rich_text_fields = [
                RichTextField(
                    name="content",
                    description="Main article content",
                    toolbar=["bold", "italic", "link", "heading", "list"],
                    max_length=50000,
                ),
                RichTextField(
                    name="summary",
                    placeholder="Enter a brief summary...",
                    required=True,
                ),
            ]
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = [
    "DEFAULT_RICH_TEXT_TOOLBAR",
    "DEFAULT_SAFE_HTML_TAGS",
    "RichTextField",
]

# Default toolbar configuration for the rich text editor
# These map to Tiptap extensions available on the frontend
DEFAULT_RICH_TEXT_TOOLBAR: tuple[str, ...] = (
    "bold",
    "italic",
    "underline",
    "strike",
    "code",
    "heading",
    "bulletList",
    "orderedList",
    "blockquote",
    "codeBlock",
    "link",
    "image",
    "horizontalRule",
    "undo",
    "redo",
)

# Default allowed HTML tags for XSS sanitization
# This is a safe subset of HTML tags commonly used in rich text content
DEFAULT_SAFE_HTML_TAGS: tuple[str, ...] = (
    # Block elements
    "p",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "blockquote",
    "pre",
    "code",
    "hr",
    "br",
    "div",
    # Lists
    "ul",
    "ol",
    "li",
    # Inline elements
    "a",
    "strong",
    "b",
    "em",
    "i",
    "u",
    "s",
    "strike",
    "sub",
    "sup",
    "span",
    "mark",
    # Media (with proper attribute filtering)
    "img",
    # Tables
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
)


@dataclass
class RichTextField:
    """Rich text editor field for model views.

    This class defines a rich text field that uses the Tiptap editor
    on the frontend for WYSIWYG content editing. It provides configuration
    options for toolbar customization, content validation, and XSS protection.

    Attributes:
        name: The field name, corresponding to the model attribute.
        description: Help text displayed below the editor.
        required: Whether the field is required for form submission.
        placeholder: Placeholder text shown when the editor is empty.
        toolbar: List of toolbar buttons to display. If None, uses
            DEFAULT_RICH_TEXT_TOOLBAR. Available options include:
            bold, italic, underline, strike, code, heading, bulletList,
            orderedList, blockquote, codeBlock, link, image, horizontalRule,
            undo, redo.
        max_length: Maximum character count for content (excluding HTML tags).
            If None, no limit is enforced.
        allowed_tags: List of allowed HTML tags for XSS sanitization.
            If None, uses DEFAULT_SAFE_HTML_TAGS. Content will be sanitized
            on the server before storage.
        label: Optional custom label for the form field.

    Example:
        >>> rich_field = RichTextField(
        ...     name="content",
        ...     description="Main article content",
        ...     required=True,
        ...     toolbar=["bold", "italic", "link", "heading"],
        ...     max_length=10000,
        ... )
    """

    name: str
    description: str = ""
    required: bool = False
    placeholder: str = ""
    toolbar: list[str] | None = None
    max_length: int | None = None
    allowed_tags: list[str] | None = None
    label: str | None = None

    @property
    def toolbar_items(self) -> list[str]:
        """Get toolbar items as a list.

        Returns:
            List of toolbar button identifiers.
        """
        if self.toolbar is None:
            return list(DEFAULT_RICH_TEXT_TOOLBAR)
        return self.toolbar.copy()

    @property
    def allowed_tags_set(self) -> frozenset[str]:
        """Get allowed HTML tags as a frozenset.

        Returns:
            Frozenset of allowed HTML tag names (lowercase).
        """
        if self.allowed_tags is None:
            return frozenset(DEFAULT_SAFE_HTML_TAGS)
        return frozenset(tag.lower() for tag in self.allowed_tags)

    def is_tag_allowed(self, tag: str) -> bool:
        """Check if an HTML tag is allowed.

        Args:
            tag: The HTML tag name to check (case-insensitive).

        Returns:
            True if the tag is allowed, False otherwise.
        """
        return tag.lower() in self.allowed_tags_set

    def is_length_valid(self, text_content: str) -> bool:
        """Check if text content length is within the allowed limit.

        This checks the plain text length, not the HTML length.

        Args:
            text_content: The plain text content (HTML tags stripped).

        Returns:
            True if the length is valid, False if it exceeds max_length.
        """
        if self.max_length is None:
            return True
        return len(text_content) <= self.max_length

    def to_dict(self) -> dict[str, Any]:
        """Convert the field to a dictionary for API responses.

        Returns:
            Dictionary representation of the field configuration.
        """
        return {
            "name": self.name,
            "type": "richtext",
            "description": self.description,
            "required": self.required,
            "placeholder": self.placeholder,
            "toolbar": self.toolbar_items,
            "max_length": self.max_length,
            "allowed_tags": list(self.allowed_tags_set),
            "label": self.label or self.name.replace("_", " ").title(),
        }


@dataclass
class RichTextFieldValidationError:
    """Validation error for rich text field content.

    Attributes:
        field_name: The name of the field that failed validation.
        error: The error message.
        error_code: A machine-readable error code.
    """

    field_name: str
    error: str
    error_code: str


def validate_rich_text_field(
    content: str | None,
    field_config: RichTextField,
    *,
    plain_text: str | None = None,
) -> list[RichTextFieldValidationError]:
    """Validate rich text content against a field configuration.

    This function checks the content against the field's validation rules:
    - Required field validation
    - Maximum length validation (on plain text, not HTML)

    Note: HTML tag sanitization should be performed separately using a
    dedicated library like bleach or nh3 before storing content.

    Args:
        content: The HTML content from the rich text editor.
        field_config: The RichTextField configuration.
        plain_text: Optional pre-extracted plain text for length validation.
            If not provided, length validation is skipped.

    Returns:
        List of validation errors. Empty list if validation passes.

    Example:
        >>> field = RichTextField(name="content", required=True, max_length=1000)
        >>> errors = validate_rich_text_field(html_content, field, plain_text=extracted_text)
        >>> if errors:
        ...     for error in errors:
        ...         print(f"{error.field_name}: {error.error}")
    """
    errors: list[RichTextFieldValidationError] = []

    # Check required field
    if field_config.required and (content is None or content.strip() == ""):
        errors.append(
            RichTextFieldValidationError(
                field_name=field_config.name,
                error="This field is required",
                error_code="required",
            )
        )
        return errors

    # If content is empty and not required, validation passes
    if content is None or content.strip() == "":
        return errors

    # Check max length on plain text
    if (
        plain_text is not None
        and field_config.max_length is not None
        and not field_config.is_length_valid(plain_text)
    ):
        errors.append(
            RichTextFieldValidationError(
                field_name=field_config.name,
                error=f"Content exceeds maximum length of {field_config.max_length} characters",
                error_code="max_length_exceeded",
            )
        )

    return errors
