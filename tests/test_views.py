"""Tests for BaseModelView and ModelView."""

from __future__ import annotations

from litestar_admin import BaseModelView, ModelView


class TestBaseModelView:
    """Tests for BaseModelView."""

    def test_subclass_sets_name_from_model(self, user_model) -> None:
        """Test that name is set from model class name."""

        class UserAdmin(BaseModelView):
            model = user_model

        assert UserAdmin.name == "User"
        assert UserAdmin.name_plural == "Users"

    def test_custom_name(self, user_model) -> None:
        """Test custom name and plural."""

        class UserAdmin(BaseModelView):
            model = user_model
            name = "Account"
            name_plural = "Accounts"

        assert UserAdmin.name == "Account"
        assert UserAdmin.name_plural == "Accounts"

    def test_default_permissions(self, user_model) -> None:
        """Test default permission values."""

        class UserAdmin(BaseModelView):
            model = user_model

        assert UserAdmin.can_create is True
        assert UserAdmin.can_edit is True
        assert UserAdmin.can_delete is True
        assert UserAdmin.can_view_details is True
        assert UserAdmin.can_export is True

    def test_get_list_columns_explicit(self, user_model) -> None:
        """Test get_list_columns with explicit column_list."""

        class UserAdmin(BaseModelView):
            model = user_model
            column_list = ["id", "email", "name"]
            column_exclude_list = ["name"]

        columns = UserAdmin.get_list_columns()
        assert columns == ["id", "email"]

    def test_get_list_columns_auto_detect(self, user_model) -> None:
        """Test get_list_columns with auto-detection."""

        class UserAdmin(BaseModelView):
            model = user_model

        columns = UserAdmin.get_list_columns()
        assert "id" in columns
        assert "email" in columns
        assert "name" in columns

    def test_get_form_columns_explicit(self, user_model) -> None:
        """Test get_form_columns with explicit form_columns."""

        class UserAdmin(BaseModelView):
            model = user_model
            form_columns = ["email", "name"]
            form_excluded_columns = ["name"]

        columns = UserAdmin.get_form_columns()
        assert columns == ["email"]

    def test_get_form_columns_auto_detect_create(self, user_model) -> None:
        """Test get_form_columns auto-detection for create."""

        class UserAdmin(BaseModelView):
            model = user_model

        columns = UserAdmin.get_form_columns(is_create=True)
        # Auto-increment primary key should be excluded for create
        assert "id" not in columns
        assert "email" in columns
        assert "name" in columns

    def test_get_column_info(self, user_model) -> None:
        """Test get_column_info method."""

        class UserAdmin(BaseModelView):
            model = user_model
            column_sortable_list = ["email"]
            column_searchable_list = ["email", "name"]

        info = UserAdmin.get_column_info("email")
        assert info["name"] == "email"
        assert info["sortable"] is True
        assert info["searchable"] is True

        info = UserAdmin.get_column_info("id")
        assert info["sortable"] is False
        assert info["searchable"] is False


class TestModelView:
    """Tests for ModelView with model parameter."""

    def test_model_parameter(self, user_model) -> None:
        """Test model specified as class parameter."""

        class UserAdmin(ModelView, model=user_model):
            column_list = ["id", "email"]

        assert UserAdmin.model is user_model
        assert UserAdmin.name == "User"

    def test_model_attribute(self, user_model) -> None:
        """Test model specified as class attribute."""

        class UserAdmin(ModelView):
            model = user_model
            column_list = ["id", "email"]

        assert UserAdmin.model is user_model

    def test_inheritance(self, user_model) -> None:
        """Test inheritance from ModelView."""

        class BaseUserAdmin(ModelView, model=user_model):
            can_delete = False

        class ExtendedUserAdmin(BaseUserAdmin):
            can_create = False

        assert ExtendedUserAdmin.model is user_model
        assert ExtendedUserAdmin.can_delete is False
        assert ExtendedUserAdmin.can_create is False
