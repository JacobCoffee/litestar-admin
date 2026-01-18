"""Tests for AdminPlugin."""

from __future__ import annotations

from litestar import Litestar

from litestar_admin import AdminConfig, AdminPlugin, ModelView


class TestAdminPlugin:
    """Tests for AdminPlugin."""

    def test_default_config(self) -> None:
        """Test plugin with default configuration."""
        plugin = AdminPlugin()

        assert plugin.config.title == "Admin"
        assert plugin.config.base_url == "/admin"
        assert len(plugin.registry) == 0

    def test_custom_config(self) -> None:
        """Test plugin with custom configuration."""
        config = AdminConfig(
            title="My Admin",
            base_url="/my-admin",
        )
        plugin = AdminPlugin(config=config)

        assert plugin.config.title == "My Admin"
        assert plugin.config.base_url == "/my-admin"

    def test_views_registration(self, user_model) -> None:
        """Test that views are registered on app init."""

        class UserAdmin(ModelView, model=user_model):
            pass

        plugin = AdminPlugin(
            config=AdminConfig(views=[UserAdmin])
        )

        # Create app to trigger on_app_init
        app = Litestar(plugins=[plugin])

        assert plugin.registry.has_model(user_model)
        assert "admin_config" in app.dependencies
        assert "admin_registry" in app.dependencies

    def test_properties(self) -> None:
        """Test config and registry properties."""
        config = AdminConfig(title="Test")
        plugin = AdminPlugin(config=config)

        assert plugin.config is config
        assert plugin.registry is not None

    def test_app_integration(self) -> None:
        """Test full app integration."""
        plugin = AdminPlugin(
            config=AdminConfig(
                title="Integration Test",
                auto_discover=False,
            )
        )

        app = Litestar(plugins=[plugin])

        # Verify plugin was initialized
        assert app is not None
        assert "admin_config" in app.dependencies
