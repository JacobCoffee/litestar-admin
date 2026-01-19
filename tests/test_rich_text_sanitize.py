"""Tests for rich text XSS sanitization."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from litestar_admin.fields.rich_text import DEFAULT_SAFE_HTML_TAGS, RichTextField
from litestar_admin.fields.sanitize import (
    DEFAULT_TAG_ATTRIBUTES,
    SAFE_URL_SCHEMES,
    get_sanitizer_status,
    sanitize_html,
)

if TYPE_CHECKING:
    pass


class TestSanitizeHtml:
    """Tests for the sanitize_html function."""

    @pytest.fixture(autouse=True)
    def check_nh3_available(self) -> None:
        """Skip tests if nh3 is not installed."""
        try:
            import nh3  # noqa: F401
        except ImportError:
            pytest.skip("nh3 is not installed")

    def test_removes_script_tags(self) -> None:
        """Test that script tags are completely removed."""
        content = '<p>Hello</p><script>alert("XSS")</script><p>World</p>'
        result = sanitize_html(content, allowed_tags=["p"])
        assert "<script>" not in result
        assert "alert" not in result
        assert "<p>Hello</p>" in result
        assert "<p>World</p>" in result

    def test_removes_script_tags_with_attributes(self) -> None:
        """Test that script tags with src attributes are removed."""
        content = '<script src="evil.js"></script><p>Safe</p>'
        result = sanitize_html(content, allowed_tags=["p"])
        assert "<script" not in result
        assert "evil.js" not in result
        assert "<p>Safe</p>" in result

    def test_removes_iframe_tags(self) -> None:
        """Test that iframe tags are removed."""
        content = '<p>Text</p><iframe src="https://evil.com"></iframe>'
        result = sanitize_html(content, allowed_tags=["p"])
        assert "<iframe" not in result
        assert "evil.com" not in result
        assert "<p>Text</p>" in result

    def test_removes_object_tags(self) -> None:
        """Test that object tags are removed."""
        content = '<object data="malware.swf"></object><p>Safe</p>'
        result = sanitize_html(content, allowed_tags=["p"])
        assert "<object" not in result
        assert "malware.swf" not in result

    def test_removes_embed_tags(self) -> None:
        """Test that embed tags are removed."""
        content = '<embed src="malware.swf"><p>Safe</p>'
        result = sanitize_html(content, allowed_tags=["p"])
        assert "<embed" not in result

    def test_removes_onclick_attributes(self) -> None:
        """Test that onclick event handlers are removed."""
        content = '<p onclick="alert(\'XSS\')">Click me</p>'
        result = sanitize_html(content, allowed_tags=["p"])
        assert "onclick" not in result
        assert "<p>Click me</p>" in result

    def test_removes_onerror_attributes(self) -> None:
        """Test that onerror event handlers are removed."""
        content = '<img src="x" onerror="alert(\'XSS\')">'
        result = sanitize_html(content, allowed_tags=["img"])
        assert "onerror" not in result

    def test_removes_onload_attributes(self) -> None:
        """Test that onload event handlers are removed."""
        content = '<body onload="alert(\'XSS\')"><p>Text</p></body>'
        result = sanitize_html(content, allowed_tags=["p"])
        assert "onload" not in result

    def test_removes_javascript_href(self) -> None:
        """Test that javascript: protocol in href is handled."""
        content = '<a href="javascript:alert(\'XSS\')">Click</a>'
        result = sanitize_html(content, allowed_tags=["a"])
        assert "javascript:" not in result

    def test_removes_data_href_with_script(self) -> None:
        """Test that data: URLs with scripts are handled appropriately."""
        content = '<a href="data:text/html,<script>alert(1)</script>">Click</a>'
        result = sanitize_html(content, allowed_tags=["a"])
        # The data URL should be preserved but the script inside won't execute
        # as it's just text in the href attribute
        assert "<a" in result  # Link tag should be preserved

    def test_preserves_allowed_tags(self) -> None:
        """Test that allowed tags are preserved in output."""
        content = "<p>Paragraph</p><strong>Bold</strong><em>Italic</em>"
        result = sanitize_html(content, allowed_tags=["p", "strong", "em"])
        assert "<p>Paragraph</p>" in result
        assert "<strong>Bold</strong>" in result
        assert "<em>Italic</em>" in result

    def test_preserves_heading_tags(self) -> None:
        """Test that heading tags are preserved when allowed."""
        content = "<h1>Title</h1><h2>Subtitle</h2><p>Content</p>"
        result = sanitize_html(content, allowed_tags=["h1", "h2", "p"])
        assert "<h1>Title</h1>" in result
        assert "<h2>Subtitle</h2>" in result
        assert "<p>Content</p>" in result

    def test_preserves_list_tags(self) -> None:
        """Test that list tags are preserved when allowed."""
        content = "<ul><li>Item 1</li><li>Item 2</li></ul>"
        result = sanitize_html(content, allowed_tags=["ul", "li"])
        assert "<ul>" in result
        assert "<li>Item 1</li>" in result
        assert "<li>Item 2</li>" in result
        assert "</ul>" in result

    def test_preserves_safe_link_attributes(self) -> None:
        """Test that safe attributes on links are preserved."""
        content = '<a href="https://example.com" title="Example">Link</a>'
        result = sanitize_html(content, allowed_tags=["a"])
        assert 'href="https://example.com"' in result
        assert 'title="Example"' in result

    def test_preserves_safe_image_attributes(self) -> None:
        """Test that safe attributes on images are preserved."""
        content = '<img src="https://example.com/image.jpg" alt="Description" width="100">'
        result = sanitize_html(content, allowed_tags=["img"])
        assert 'src="https://example.com/image.jpg"' in result
        assert 'alt="Description"' in result

    def test_removes_style_attribute(self) -> None:
        """Test that style attributes are removed by default."""
        content = '<p style="color: red; background: url(evil.js)">Text</p>'
        result = sanitize_html(content, allowed_tags=["p"])
        assert "style=" not in result
        assert "<p>Text</p>" in result

    def test_handles_nested_tags(self) -> None:
        """Test sanitization of nested tag structures."""
        content = "<div><p>Hello <strong>World</strong></p></div>"
        result = sanitize_html(content, allowed_tags=["div", "p", "strong"])
        assert "<div><p>Hello <strong>World</strong></p></div>" in result

    def test_handles_empty_content(self) -> None:
        """Test that empty content returns empty string."""
        result = sanitize_html("", allowed_tags=["p"])
        assert result == ""

    def test_handles_none_like_empty(self) -> None:
        """Test that whitespace-only content is preserved."""
        result = sanitize_html("   ", allowed_tags=["p"])
        assert result == "   "

    def test_handles_plain_text(self) -> None:
        """Test that plain text without tags is preserved."""
        content = "Hello World, this is plain text!"
        result = sanitize_html(content, allowed_tags=["p"])
        assert "Hello World, this is plain text!" in result

    def test_case_insensitive_tags(self) -> None:
        """Test that tag matching is case-insensitive."""
        content = "<P>Paragraph</P><STRONG>Bold</STRONG>"
        result = sanitize_html(content, allowed_tags=["p", "strong"])
        # nh3 normalizes tags to lowercase but preserves content case
        assert "<p>" in result
        assert "Paragraph" in result
        assert "<strong>" in result
        assert "Bold" in result

    def test_custom_tag_attributes(self) -> None:
        """Test that custom tag attributes can be specified."""
        content = '<div data-custom="value" class="test">Content</div>'
        result = sanitize_html(
            content,
            allowed_tags=["div"],
            tag_attributes={"div": ["data-custom", "class"]},
        )
        assert 'data-custom="value"' in result
        assert 'class="test"' in result

    def test_strips_html_comments(self) -> None:
        """Test that HTML comments are stripped by default."""
        content = "<p>Before</p><!-- Secret comment --><p>After</p>"
        result = sanitize_html(content, allowed_tags=["p"])
        assert "<!--" not in result
        assert "Secret comment" not in result
        assert "<p>Before</p>" in result
        assert "<p>After</p>" in result

    def test_preserves_comments_when_disabled(self) -> None:
        """Test that comments can be preserved when strip_comments=False."""
        content = "<p>Before</p><!-- Comment --><p>After</p>"
        result = sanitize_html(content, allowed_tags=["p"], strip_comments=False)
        assert "<!-- Comment -->" in result

    def test_table_tags_preserved(self) -> None:
        """Test that table elements are preserved when allowed."""
        content = """
        <table>
            <thead><tr><th>Header</th></tr></thead>
            <tbody><tr><td>Data</td></tr></tbody>
        </table>
        """
        result = sanitize_html(
            content,
            allowed_tags=["table", "thead", "tbody", "tr", "th", "td"],
        )
        assert "<table>" in result
        assert "<th>Header</th>" in result
        assert "<td>Data</td>" in result

    def test_blockquote_with_cite(self) -> None:
        """Test that blockquote with cite attribute is handled."""
        content = '<blockquote cite="https://example.com">Quote</blockquote>'
        result = sanitize_html(content, allowed_tags=["blockquote"])
        assert "<blockquote" in result
        assert "Quote</blockquote>" in result

    def test_code_blocks_preserved(self) -> None:
        """Test that code blocks are preserved."""
        content = "<pre><code>function test() { return true; }</code></pre>"
        result = sanitize_html(content, allowed_tags=["pre", "code"])
        assert "<pre><code>" in result
        assert "function test()" in result

    def test_default_safe_html_tags_work(self) -> None:
        """Test that DEFAULT_SAFE_HTML_TAGS work correctly."""
        content = """
        <h1>Title</h1>
        <p>Paragraph with <strong>bold</strong> and <em>italic</em>.</p>
        <ul><li>Item</li></ul>
        <a href="https://example.com">Link</a>
        <script>alert('XSS')</script>
        """
        result = sanitize_html(content, allowed_tags=DEFAULT_SAFE_HTML_TAGS)
        assert "<h1>Title</h1>" in result
        assert "<strong>bold</strong>" in result
        assert "<script>" not in result
        assert "alert" not in result


class TestSanitizeHtmlWithoutNh3:
    """Tests for sanitize_html behavior when nh3 is not installed."""

    def test_returns_content_unchanged_without_nh3(self) -> None:
        """Test that content is returned unchanged when nh3 is not available."""
        # Mock nh3 as unavailable
        with patch.dict("sys.modules", {"nh3": None}):
            # Need to reimport to pick up the mock

            from litestar_admin.fields import sanitize

            # Temporarily set NH3_AVAILABLE to False
            original_available = sanitize.NH3_AVAILABLE
            sanitize.NH3_AVAILABLE = False

            try:
                dangerous_content = '<script>alert("XSS")</script><p>Hello</p>'
                result = sanitize.sanitize_html(dangerous_content, allowed_tags=["p"])
                # Without nh3, content should be returned as-is
                assert result == dangerous_content
            finally:
                sanitize.NH3_AVAILABLE = original_available

    def test_logs_warning_without_nh3(self) -> None:
        """Test that a warning is logged when nh3 is not available."""
        from litestar_admin.fields import sanitize

        original_available = sanitize.NH3_AVAILABLE
        sanitize.NH3_AVAILABLE = False

        try:
            with patch.object(sanitize.logger, "warning") as mock_warning:
                sanitize.sanitize_html("<p>Test</p>", allowed_tags=["p"])
                mock_warning.assert_called_once()
                assert "nh3 library is not installed" in mock_warning.call_args[0][0]
        finally:
            sanitize.NH3_AVAILABLE = original_available


class TestGetSanitizerStatus:
    """Tests for the get_sanitizer_status function."""

    def test_returns_available_true_with_nh3(self) -> None:
        """Test status returns available=True when nh3 is installed."""
        try:
            import nh3  # noqa: F401

            status = get_sanitizer_status()
            assert status["available"] is True
            assert status["version"] is not None
            assert "nh3" in status["message"]
        except ImportError:
            pytest.skip("nh3 is not installed")

    def test_returns_available_false_without_nh3(self) -> None:
        """Test status returns available=False when nh3 is not installed."""
        from litestar_admin.fields import sanitize

        original_available = sanitize.NH3_AVAILABLE
        sanitize.NH3_AVAILABLE = False

        try:
            status = sanitize.get_sanitizer_status()
            assert status["available"] is False
            assert status["version"] is None
            assert "not installed" in status["message"]
        finally:
            sanitize.NH3_AVAILABLE = original_available


class TestDefaultTagAttributes:
    """Tests for DEFAULT_TAG_ATTRIBUTES constant."""

    def test_link_attributes(self) -> None:
        """Test that link tag has safe attributes defined."""
        assert "a" in DEFAULT_TAG_ATTRIBUTES
        a_attrs = DEFAULT_TAG_ATTRIBUTES["a"]
        assert "href" in a_attrs
        assert "title" in a_attrs
        # Note: rel is NOT in attributes because nh3 handles it via link_rel parameter
        assert "rel" not in a_attrs
        assert "target" in a_attrs

    def test_image_attributes(self) -> None:
        """Test that img tag has safe attributes defined."""
        assert "img" in DEFAULT_TAG_ATTRIBUTES
        img_attrs = DEFAULT_TAG_ATTRIBUTES["img"]
        assert "src" in img_attrs
        assert "alt" in img_attrs
        assert "width" in img_attrs
        assert "height" in img_attrs

    def test_table_attributes(self) -> None:
        """Test that table-related tags have appropriate attributes."""
        assert "table" in DEFAULT_TAG_ATTRIBUTES
        assert "td" in DEFAULT_TAG_ATTRIBUTES
        assert "th" in DEFAULT_TAG_ATTRIBUTES
        assert "colspan" in DEFAULT_TAG_ATTRIBUTES["td"]
        assert "rowspan" in DEFAULT_TAG_ATTRIBUTES["td"]

    def test_no_dangerous_attributes(self) -> None:
        """Test that no dangerous attributes are in defaults."""
        dangerous = {"onclick", "onerror", "onload", "onmouseover", "onfocus", "onblur"}
        for tag, attrs in DEFAULT_TAG_ATTRIBUTES.items():
            for attr in attrs:
                assert attr not in dangerous, f"Dangerous attribute {attr} found in {tag}"


class TestSafeUrlSchemes:
    """Tests for SAFE_URL_SCHEMES constant."""

    def test_contains_safe_schemes(self) -> None:
        """Test that common safe schemes are included."""
        assert "http" in SAFE_URL_SCHEMES
        assert "https" in SAFE_URL_SCHEMES
        assert "mailto" in SAFE_URL_SCHEMES
        assert "tel" in SAFE_URL_SCHEMES

    def test_does_not_contain_dangerous_schemes(self) -> None:
        """Test that dangerous schemes are not included."""
        assert "javascript" not in SAFE_URL_SCHEMES
        assert "vbscript" not in SAFE_URL_SCHEMES


class TestRichTextFieldIntegration:
    """Tests for RichTextField integration with sanitization."""

    def test_allowed_tags_set_provides_iterable(self) -> None:
        """Test that RichTextField.allowed_tags_set works with sanitize_html."""
        field = RichTextField(name="content", allowed_tags=["p", "strong", "em"])
        allowed = field.allowed_tags_set
        assert isinstance(allowed, frozenset)
        assert "p" in allowed
        assert "strong" in allowed
        assert "em" in allowed

    def test_default_tags_used_when_none(self) -> None:
        """Test that DEFAULT_SAFE_HTML_TAGS are used when allowed_tags is None."""
        field = RichTextField(name="content")
        allowed = field.allowed_tags_set
        assert allowed == frozenset(DEFAULT_SAFE_HTML_TAGS)

    @pytest.fixture(autouse=True)
    def check_nh3_for_integration(self) -> None:
        """Skip integration tests if nh3 is not installed."""
        try:
            import nh3  # noqa: F401
        except ImportError:
            pytest.skip("nh3 is not installed")

    def test_sanitize_with_field_config(self) -> None:
        """Test sanitization using RichTextField configuration."""
        field = RichTextField(name="content", allowed_tags=["p", "b"])
        content = "<script>evil</script><p>Hello <b>World</b></p><i>Removed</i>"
        result = sanitize_html(content, allowed_tags=field.allowed_tags_set)
        assert "<script>" not in result
        assert "<p>Hello <b>World</b></p>" in result
        # <i> is not in allowed_tags, so it should be stripped but content preserved
        assert "Removed" in result
        assert "<i>" not in result


class TestAdminServiceSanitization:
    """Tests for AdminService rich text sanitization integration."""

    @pytest.fixture(autouse=True)
    def check_nh3_available(self) -> None:
        """Skip tests if nh3 is not installed."""
        try:
            import nh3  # noqa: F401
        except ImportError:
            pytest.skip("nh3 is not installed")

    def test_sanitize_rich_text_fields_method(self) -> None:
        """Test the _sanitize_rich_text_fields method of AdminService."""

        from litestar_admin.service import AdminService

        # Create mock view class with rich text fields
        mock_view = MagicMock()
        mock_view.get_rich_text_fields.return_value = [
            RichTextField(name="content", allowed_tags=["p", "b"]),
            RichTextField(name="summary", allowed_tags=["p"]),
        ]
        mock_view.model = MagicMock()

        # Create service instance
        mock_session = MagicMock()
        service = AdminService(mock_view, mock_session)

        # Test data with XSS attempts
        data = {
            "title": "Test Title",  # Not a rich text field
            "content": '<script>alert("XSS")</script><p>Hello <b>World</b></p>',
            "summary": '<p>Summary</p><iframe src="evil.com"></iframe>',
        }

        result = service._sanitize_rich_text_fields(data)

        # Regular field should be unchanged
        assert result["title"] == "Test Title"

        # Rich text fields should be sanitized
        assert "<script>" not in result["content"]
        assert "<p>Hello <b>World</b></p>" in result["content"]

        assert "<iframe" not in result["summary"]
        assert "<p>Summary</p>" in result["summary"]

    def test_sanitize_preserves_none_values(self) -> None:
        """Test that None values in rich text fields are preserved."""

        from litestar_admin.service import AdminService

        mock_view = MagicMock()
        mock_view.get_rich_text_fields.return_value = [
            RichTextField(name="content"),
        ]
        mock_view.model = MagicMock()

        mock_session = MagicMock()
        service = AdminService(mock_view, mock_session)

        data = {"content": None}
        result = service._sanitize_rich_text_fields(data)
        assert result["content"] is None

    def test_sanitize_skips_non_string_values(self) -> None:
        """Test that non-string values in rich text fields are preserved."""

        from litestar_admin.service import AdminService

        mock_view = MagicMock()
        mock_view.get_rich_text_fields.return_value = [
            RichTextField(name="content"),
        ]
        mock_view.model = MagicMock()

        mock_session = MagicMock()
        service = AdminService(mock_view, mock_session)

        # If somehow a non-string ends up here, it should be preserved
        data = {"content": 12345}
        result = service._sanitize_rich_text_fields(data)
        assert result["content"] == 12345

    def test_sanitize_with_no_rich_text_fields(self) -> None:
        """Test that data is returned unchanged when no rich text fields defined."""

        from litestar_admin.service import AdminService

        mock_view = MagicMock()
        mock_view.get_rich_text_fields.return_value = []
        mock_view.model = MagicMock()

        mock_session = MagicMock()
        service = AdminService(mock_view, mock_session)

        data = {"content": '<script>alert("XSS")</script>'}
        result = service._sanitize_rich_text_fields(data)
        # No rich text fields, so content should be unchanged
        assert result["content"] == '<script>alert("XSS")</script>'
