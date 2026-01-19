"""HTML sanitization utilities for rich text content.

This module provides XSS protection for rich text fields by sanitizing HTML content
before storage. It uses the nh3 library (Python bindings to Rust ammonia) for fast
and secure HTML sanitization.

Example:
    Basic sanitization::

        from litestar_admin.fields.sanitize import sanitize_html
        from litestar_admin.fields.rich_text import DEFAULT_SAFE_HTML_TAGS

        # Sanitize user-provided HTML content
        clean_html = sanitize_html(
            '<script>alert("XSS")</script><p>Hello <b>World</b></p>',
            allowed_tags=DEFAULT_SAFE_HTML_TAGS,
        )
        # Result: '<p>Hello <b>World</b></p>'

    Using with RichTextField configuration::

        from litestar_admin.fields import RichTextField
        from litestar_admin.fields.sanitize import sanitize_html

        field = RichTextField(name="content", allowed_tags=["p", "b", "i", "a"])
        clean_html = sanitize_html(user_content, allowed_tags=field.allowed_tags_set)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

__all__ = [
    "DEFAULT_TAG_ATTRIBUTES",
    "NH3_AVAILABLE",
    "sanitize_html",
]

logger = logging.getLogger(__name__)

# Check if nh3 is available
try:
    import nh3

    NH3_AVAILABLE = True
except ImportError:
    NH3_AVAILABLE = False

# Default safe attributes per tag
# These attributes are generally safe and commonly used in rich text content
# Note: Do NOT include "rel" for "a" tags - nh3 handles rel via link_rel parameter
DEFAULT_TAG_ATTRIBUTES: dict[str, frozenset[str]] = {
    # Links - href is essential, target for UX (rel is handled by nh3's link_rel)
    "a": frozenset({"href", "title", "target"}),
    # Images - src and alt are essential, dimensions for layout
    "img": frozenset({"src", "alt", "title", "width", "height", "loading"}),
    # Tables - alignment and dimensions
    "table": frozenset({"border", "cellpadding", "cellspacing", "width"}),
    "td": frozenset({"colspan", "rowspan", "width", "height", "align", "valign"}),
    "th": frozenset({"colspan", "rowspan", "width", "height", "align", "valign", "scope"}),
    "tr": frozenset({"align", "valign"}),
    # Block elements - common styling attributes
    "div": frozenset({"class", "id"}),
    "span": frozenset({"class", "id"}),
    "p": frozenset({"class", "id"}),
    # Headings
    "h1": frozenset({"class", "id"}),
    "h2": frozenset({"class", "id"}),
    "h3": frozenset({"class", "id"}),
    "h4": frozenset({"class", "id"}),
    "h5": frozenset({"class", "id"}),
    "h6": frozenset({"class", "id"}),
    # Lists
    "ul": frozenset({"class", "id"}),
    "ol": frozenset({"class", "id", "start", "type"}),
    "li": frozenset({"class", "id", "value"}),
    # Code blocks
    "pre": frozenset({"class", "id"}),
    "code": frozenset({"class", "id"}),
    # Blockquote
    "blockquote": frozenset({"class", "id", "cite"}),
}

# URL schemes that are safe for href and src attributes
SAFE_URL_SCHEMES: frozenset[str] = frozenset({
    "http",
    "https",
    "mailto",
    "tel",
    "data",  # For base64 embedded images
})


def sanitize_html(
    content: str,
    allowed_tags: Iterable[str],
    *,
    tag_attributes: dict[str, Iterable[str]] | None = None,
    strip_comments: bool = True,
) -> str:
    """Sanitize HTML content by removing disallowed tags and attributes.

    This function uses nh3 (Python bindings to Rust ammonia) for fast and secure
    HTML sanitization. If nh3 is not installed, it logs a warning and returns
    the content unchanged.

    Args:
        content: The HTML content to sanitize.
        allowed_tags: Iterable of allowed HTML tag names (case-insensitive).
        tag_attributes: Optional mapping of tag names to allowed attributes.
            If not provided, uses DEFAULT_TAG_ATTRIBUTES. Pass an empty dict
            to disallow all attributes.
        strip_comments: Whether to remove HTML comments (default: True).

    Returns:
        Sanitized HTML string with disallowed tags and attributes removed.
        If nh3 is not installed, returns the original content with a warning logged.

    Example:
        >>> from litestar_admin.fields.sanitize import sanitize_html
        >>> sanitize_html(
        ...     '<script>alert("XSS")</script><p onclick="hack()">Hello</p>',
        ...     allowed_tags=["p", "b", "i"],
        ... )
        '<p>Hello</p>'

        >>> # Preserve links with safe href
        >>> sanitize_html(
        ...     '<a href="https://example.com" onclick="hack()">Link</a>',
        ...     allowed_tags=["a"],
        ... )
        '<a href="https://example.com">Link</a>'

    Note:
        If nh3 is not installed, this function will:
        1. Log a warning on the first call
        2. Return the content unchanged

        To install nh3, add the 'sanitize' extra:
        ``pip install litestar-admin[sanitize]``
    """
    if not content:
        return content

    if not NH3_AVAILABLE:
        logger.warning(
            "nh3 library is not installed. HTML content will NOT be sanitized. "
            "Install with: pip install litestar-admin[sanitize]"
        )
        return content

    # Normalize allowed tags to a set of lowercase strings
    tags_set = {tag.lower() for tag in allowed_tags}

    # Build attribute map for nh3
    # nh3 expects a dict of tag -> set of attribute names
    if tag_attributes is None:
        # Use defaults, but only for tags that are actually allowed
        attr_map: dict[str, set[str]] = {}
        for tag in tags_set:
            if tag in DEFAULT_TAG_ATTRIBUTES:
                attr_map[tag] = set(DEFAULT_TAG_ATTRIBUTES[tag])
    else:
        # Use provided attributes
        attr_map = {tag.lower(): set(attrs) for tag, attrs in tag_attributes.items() if tag.lower() in tags_set}

    # Call nh3.clean with our configuration
    # nh3.clean is the main sanitization function
    return nh3.clean(
        content,
        tags=tags_set,
        attributes=attr_map,
        strip_comments=strip_comments,
        url_schemes=SAFE_URL_SCHEMES,
        link_rel="noopener noreferrer",  # Security: prevent reverse tabnabbing
    )


def get_sanitizer_status() -> dict[str, bool | str]:
    """Get the current status of the HTML sanitizer.

    Returns:
        Dictionary with sanitizer status information:
        - available: Whether nh3 is installed
        - version: The nh3 version if available, None otherwise
        - message: Human-readable status message
    """
    if NH3_AVAILABLE:
        import nh3

        version = getattr(nh3, "__version__", "unknown")
        return {
            "available": True,
            "version": version,
            "message": f"nh3 {version} is available for HTML sanitization",
        }
    return {
        "available": False,
        "version": None,
        "message": "nh3 is not installed. Install with: pip install litestar-admin[sanitize]",
    }
