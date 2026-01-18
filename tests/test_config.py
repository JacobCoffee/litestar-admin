"""Tests for AdminConfig."""

from __future__ import annotations

import pytest

from litestar_admin import AdminConfig


class TestAdminConfig:
    """Tests for AdminConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = AdminConfig()

        assert config.title == "Admin"
        assert config.base_url == "/admin"
        assert config.theme == "dark"
        assert config.auto_discover is True
        assert config.debug is False
        assert config.rate_limit_enabled is True
        assert config.rate_limit_requests == 100
        assert config.rate_limit_window_seconds == 60

    def test_custom_values(self) -> None:
        """Test configuration with custom values."""
        config = AdminConfig(
            title="My Admin",
            base_url="/my-admin",
            theme="light",
            debug=True,
        )

        assert config.title == "My Admin"
        assert config.base_url == "/my-admin"
        assert config.theme == "light"
        assert config.debug is True

    def test_base_url_validation_no_leading_slash(self) -> None:
        """Test that base_url must start with '/'."""
        with pytest.raises(ValueError, match="base_url must start with '/'"):
            AdminConfig(base_url="admin")

    def test_base_url_trailing_slash_removed(self) -> None:
        """Test that trailing slash is removed from base_url."""
        config = AdminConfig(base_url="/admin/")
        assert config.base_url == "/admin"

    def test_base_url_root_preserved(self) -> None:
        """Test that root '/' base_url is preserved."""
        config = AdminConfig(base_url="/")
        assert config.base_url == "/"

    def test_rate_limit_validation(self) -> None:
        """Test rate limit validation."""
        with pytest.raises(ValueError, match="rate_limit_requests must be at least 1"):
            AdminConfig(rate_limit_requests=0)

        with pytest.raises(ValueError, match="rate_limit_window_seconds must be at least 1"):
            AdminConfig(rate_limit_window_seconds=0)

    def test_api_base_url_property(self) -> None:
        """Test api_base_url property."""
        config = AdminConfig(base_url="/admin")
        assert config.api_base_url == "/admin/api"

    def test_static_base_url_property(self) -> None:
        """Test static_base_url property."""
        config = AdminConfig(base_url="/admin")
        assert config.static_base_url == "/admin/static"

    def test_extra_settings(self) -> None:
        """Test extra settings dictionary."""
        config = AdminConfig(extra={"custom_setting": "value"})
        assert config.extra["custom_setting"] == "value"
