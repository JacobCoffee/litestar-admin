"""Tests for ModelRegistry."""

from __future__ import annotations

import pytest

from litestar_admin import ModelRegistry, ModelView


class TestModelRegistry:
    """Tests for ModelRegistry."""

    def test_register_view(self, user_model) -> None:
        """Test registering a model view."""

        class UserAdmin(ModelView, model=user_model):
            column_list = ["id", "email"]

        registry = ModelRegistry()
        registry.register(UserAdmin)

        assert registry.has_model(user_model)
        assert registry.has_model_by_name("User")
        assert len(registry) == 1

    def test_register_duplicate_model_raises(self, user_model) -> None:
        """Test that registering duplicate model raises error."""

        class UserAdmin1(ModelView, model=user_model):
            pass

        class UserAdmin2(ModelView, model=user_model):
            pass

        registry = ModelRegistry()
        registry.register(UserAdmin1)

        with pytest.raises(ValueError, match="Model User is already registered"):
            registry.register(UserAdmin2)

    def test_unregister_by_model(self, user_model) -> None:
        """Test unregistering by model class."""

        class UserAdmin(ModelView, model=user_model):
            pass

        registry = ModelRegistry()
        registry.register(UserAdmin)
        registry.unregister(user_model)

        assert not registry.has_model(user_model)
        assert len(registry) == 0

    def test_unregister_by_name(self, user_model) -> None:
        """Test unregistering by view name."""

        class UserAdmin(ModelView, model=user_model):
            pass

        registry = ModelRegistry()
        registry.register(UserAdmin)
        registry.unregister("User")

        assert not registry.has_model_by_name("User")
        assert len(registry) == 0

    def test_unregister_nonexistent_raises(self, user_model) -> None:
        """Test unregistering nonexistent view raises error."""
        registry = ModelRegistry()

        with pytest.raises(KeyError, match="Model User is not registered"):
            registry.unregister(user_model)

        with pytest.raises(KeyError, match="View 'User' is not registered"):
            registry.unregister("User")

    def test_get_view(self, user_model) -> None:
        """Test getting view by model class."""

        class UserAdmin(ModelView, model=user_model):
            pass

        registry = ModelRegistry()
        registry.register(UserAdmin)

        view = registry.get_view(user_model)
        assert view is UserAdmin

    def test_get_view_by_name(self, user_model) -> None:
        """Test getting view by name."""

        class UserAdmin(ModelView, model=user_model):
            pass

        registry = ModelRegistry()
        registry.register(UserAdmin)

        view = registry.get_view_by_name("User")
        assert view is UserAdmin

    def test_get_nonexistent_view_raises(self, user_model, post_model) -> None:
        """Test getting nonexistent view raises error."""
        registry = ModelRegistry()

        with pytest.raises(KeyError, match="Model User is not registered"):
            registry.get_view(user_model)

        with pytest.raises(KeyError, match="View 'Post' is not registered"):
            registry.get_view_by_name("Post")

    def test_list_models(self, user_model, post_model) -> None:
        """Test listing all registered models."""

        class UserAdmin(ModelView, model=user_model):
            icon = "user"
            category = "Users"

        class PostAdmin(ModelView, model=post_model):
            icon = "file"
            can_delete = False

        registry = ModelRegistry()
        registry.register(UserAdmin)
        registry.register(PostAdmin)

        models = registry.list_models()
        assert len(models) == 2

        user_info = next(m for m in models if m["name"] == "User")
        assert user_info["icon"] == "user"
        assert user_info["category"] == "Users"

        post_info = next(m for m in models if m["name"] == "Post")
        assert post_info["can_delete"] is False

    def test_iteration(self, user_model, post_model) -> None:
        """Test iterating over registry."""

        class UserAdmin(ModelView, model=user_model):
            pass

        class PostAdmin(ModelView, model=post_model):
            pass

        registry = ModelRegistry()
        registry.register(UserAdmin)
        registry.register(PostAdmin)

        views = list(registry)
        assert len(views) == 2
        assert UserAdmin in views
        assert PostAdmin in views
