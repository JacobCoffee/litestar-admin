"""Tests for SQLAdmin bridge functionality."""

from __future__ import annotations

import pytest

from litestar_admin.contrib.sqladmin import (
    SQLADMIN_ATTR_MAPPING,
    SQLADMIN_SPECIFIC_ATTRS,
    SQLAdminBridge,
    convert_sqladmin_view,
)
from litestar_admin.views.base import BaseModelView

# ==============================================================================
# Mock sqladmin ModelView
# ==============================================================================


class MockSQLAdminModelView:
    """Mock sqladmin ModelView base class for testing.

    This mimics the structure of sqladmin.ModelView without requiring
    the actual sqladmin dependency.
    """

    model = None
    name = ""
    name_plural = ""
    icon = ""
    category = None

    column_list = []
    column_exclude_list = []
    column_searchable_list = []
    column_sortable_list = []
    column_default_sort = None

    form_columns = []
    form_excluded_columns = []

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    can_export = True

    page_size = 10
    page_size_options = [10, 25, 50, 100]


# ==============================================================================
# Test convert_sqladmin_view function
# ==============================================================================


class TestConvertSQLAdminView:
    """Tests for the convert_sqladmin_view function."""

    def test_basic_conversion(self, user_model) -> None:
        """Test basic conversion of sqladmin view."""

        class UserAdmin(MockSQLAdminModelView):
            model = user_model
            column_list = ["id", "email", "name"]

        converted = convert_sqladmin_view(UserAdmin)

        assert issubclass(converted, BaseModelView)
        assert converted.model is user_model
        assert converted.column_list == ["id", "email", "name"]

    def test_custom_class_name(self, user_model) -> None:
        """Test conversion with custom class name."""

        class UserAdmin(MockSQLAdminModelView):
            model = user_model

        converted = convert_sqladmin_view(UserAdmin, class_name="CustomUserAdmin")

        assert converted.__name__ == "CustomUserAdmin"

    def test_default_class_name(self, user_model) -> None:
        """Test default generated class name."""

        class UserAdmin(MockSQLAdminModelView):
            model = user_model

        converted = convert_sqladmin_view(UserAdmin)

        assert converted.__name__ == "LitestarUserAdmin"

    def test_permission_conversion(self, user_model) -> None:
        """Test that permissions are converted correctly."""

        class UserAdmin(MockSQLAdminModelView):
            model = user_model
            can_create = False
            can_edit = True
            can_delete = False
            can_view_details = True
            can_export = False

        converted = convert_sqladmin_view(UserAdmin)

        assert converted.can_create is False
        assert converted.can_edit is True
        assert converted.can_delete is False
        assert converted.can_view_details is True
        assert converted.can_export is False

    def test_column_configuration_conversion(self, user_model) -> None:
        """Test that column configuration is converted."""

        class UserAdmin(MockSQLAdminModelView):
            model = user_model
            column_list = ["id", "email", "name"]
            column_exclude_list = ["password"]
            column_searchable_list = ["email", "name"]
            column_sortable_list = ["id", "email"]

        converted = convert_sqladmin_view(UserAdmin)

        assert converted.column_list == ["id", "email", "name"]
        assert converted.column_exclude_list == ["password"]
        assert converted.column_searchable_list == ["email", "name"]
        assert converted.column_sortable_list == ["id", "email"]

    def test_form_configuration_conversion(self, user_model) -> None:
        """Test that form configuration is converted."""

        class UserAdmin(MockSQLAdminModelView):
            model = user_model
            form_columns = ["email", "name"]
            form_excluded_columns = ["id", "created_at"]

        converted = convert_sqladmin_view(UserAdmin)

        assert converted.form_columns == ["email", "name"]
        assert converted.form_excluded_columns == ["id", "created_at"]

    def test_display_configuration_conversion(self, user_model) -> None:
        """Test that display configuration is converted."""

        class UserAdmin(MockSQLAdminModelView):
            model = user_model
            name = "Account"
            name_plural = "Accounts"
            icon = "user"
            category = "Users"

        converted = convert_sqladmin_view(UserAdmin)

        assert converted.name == "Account"
        assert converted.name_plural == "Accounts"
        assert converted.icon == "user"
        assert converted.category == "Users"

    def test_pagination_configuration_conversion(self, user_model) -> None:
        """Test that pagination configuration is converted."""

        class UserAdmin(MockSQLAdminModelView):
            model = user_model
            page_size = 50
            page_size_options = [25, 50, 100, 200]

        converted = convert_sqladmin_view(UserAdmin)

        assert converted.page_size == 50
        assert converted.page_size_options == [25, 50, 100, 200]

    def test_column_default_sort_string(self, user_model) -> None:
        """Test column_default_sort with string value."""

        class UserAdmin(MockSQLAdminModelView):
            model = user_model
            column_default_sort = "email"

        converted = convert_sqladmin_view(UserAdmin)

        assert converted.column_default_sort == ("email", "asc")

    def test_column_default_sort_tuple_bool(self, user_model) -> None:
        """Test column_default_sort with tuple (column, bool) format."""

        class UserAdmin(MockSQLAdminModelView):
            model = user_model
            column_default_sort = ("created_at", True)  # True = descending

        converted = convert_sqladmin_view(UserAdmin)

        assert converted.column_default_sort == ("created_at", "desc")

    def test_column_default_sort_tuple_string(self, user_model) -> None:
        """Test column_default_sort with tuple (column, string) format."""

        class UserAdmin(MockSQLAdminModelView):
            model = user_model
            column_default_sort = ("email", "DESC")

        converted = convert_sqladmin_view(UserAdmin)

        assert converted.column_default_sort == ("email", "desc")

    def test_column_default_sort_list(self, user_model) -> None:
        """Test column_default_sort with list format (uses first item)."""

        class UserAdmin(MockSQLAdminModelView):
            model = user_model
            column_default_sort = [("created_at", True), ("id", False)]

        converted = convert_sqladmin_view(UserAdmin)

        # Should use first item only
        assert converted.column_default_sort == ("created_at", "desc")

    def test_no_model_raises_error(self) -> None:
        """Test that missing model raises ValueError."""

        class UserAdmin(MockSQLAdminModelView):
            pass  # No model attribute

        with pytest.raises(ValueError, match="has no model attribute"):
            convert_sqladmin_view(UserAdmin)

    def test_include_model_false(self, user_model) -> None:
        """Test conversion without model reference."""

        class UserAdmin(MockSQLAdminModelView):
            model = user_model
            column_list = ["id", "email"]

        converted = convert_sqladmin_view(UserAdmin, include_model=False)

        assert not hasattr(converted, "model") or converted.model is None
        assert converted.column_list == ["id", "email"]


# ==============================================================================
# Test SQLAdminBridge class
# ==============================================================================


class TestSQLAdminBridge:
    """Tests for the SQLAdminBridge class."""

    def test_init(self) -> None:
        """Test bridge initialization."""
        bridge = SQLAdminBridge()

        assert len(bridge) == 0
        assert bridge.warnings == []
        assert bridge.strict is False

    def test_init_strict_mode(self) -> None:
        """Test bridge initialization with strict mode."""
        bridge = SQLAdminBridge(strict=True)

        assert bridge.strict is True

    def test_register(self, user_model) -> None:
        """Test registering a view."""

        class UserAdmin(MockSQLAdminModelView):
            model = user_model

        bridge = SQLAdminBridge()
        bridge.register(UserAdmin)

        assert len(bridge) == 1
        assert UserAdmin in bridge

    def test_register_duplicate_raises(self, user_model) -> None:
        """Test that registering duplicate view raises error."""

        class UserAdmin(MockSQLAdminModelView):
            model = user_model

        bridge = SQLAdminBridge()
        bridge.register(UserAdmin)

        with pytest.raises(ValueError, match="already registered"):
            bridge.register(UserAdmin)

    def test_register_many(self, user_model, post_model) -> None:
        """Test registering multiple views."""

        class UserAdmin(MockSQLAdminModelView):
            model = user_model

        class PostAdmin(MockSQLAdminModelView):
            model = post_model

        bridge = SQLAdminBridge()
        bridge.register_many([UserAdmin, PostAdmin])

        assert len(bridge) == 2
        assert UserAdmin in bridge
        assert PostAdmin in bridge

    def test_convert_single(self, user_model) -> None:
        """Test converting a single view."""

        class UserAdmin(MockSQLAdminModelView):
            model = user_model
            column_list = ["id", "email"]

        bridge = SQLAdminBridge()
        bridge.register(UserAdmin)
        converted = bridge.convert(UserAdmin)

        assert issubclass(converted, BaseModelView)
        assert converted.column_list == ["id", "email"]

    def test_convert_unregistered_raises(self, user_model) -> None:
        """Test that converting unregistered view raises error."""

        class UserAdmin(MockSQLAdminModelView):
            model = user_model

        bridge = SQLAdminBridge()

        with pytest.raises(ValueError, match="not registered"):
            bridge.convert(UserAdmin)

    def test_convert_caches_result(self, user_model) -> None:
        """Test that conversion result is cached."""

        class UserAdmin(MockSQLAdminModelView):
            model = user_model

        bridge = SQLAdminBridge()
        bridge.register(UserAdmin)

        converted1 = bridge.convert(UserAdmin)
        converted2 = bridge.convert(UserAdmin)

        assert converted1 is converted2

    def test_convert_all(self, user_model, post_model) -> None:
        """Test converting all registered views."""

        class UserAdmin(MockSQLAdminModelView):
            model = user_model

        class PostAdmin(MockSQLAdminModelView):
            model = post_model

        bridge = SQLAdminBridge()
        bridge.register_many([UserAdmin, PostAdmin])
        converted = bridge.convert_all()

        assert len(converted) == 2
        assert all(issubclass(v, BaseModelView) for v in converted)

    def test_unsupported_features_warning(self, user_model) -> None:
        """Test that unsupported features generate warnings."""

        class UserAdmin(MockSQLAdminModelView):
            model = user_model
            column_labels = {"email": "Email Address"}  # sqladmin-specific

        bridge = SQLAdminBridge()
        bridge.register(UserAdmin)
        bridge.convert(UserAdmin)

        assert len(bridge.warnings) == 1
        assert "column_labels" in bridge.warnings[0]

    def test_unsupported_features_strict_mode(self, user_model) -> None:
        """Test that strict mode raises for unsupported features."""

        class UserAdmin(MockSQLAdminModelView):
            model = user_model
            column_formatters = {"email": lambda v: v.upper()}  # sqladmin-specific

        bridge = SQLAdminBridge(strict=True)
        bridge.register(UserAdmin)

        with pytest.raises(ValueError, match="sqladmin-specific features"):
            bridge.convert(UserAdmin)

    def test_clear_warnings(self, user_model) -> None:
        """Test clearing warnings."""

        class UserAdmin(MockSQLAdminModelView):
            model = user_model
            column_labels = {"email": "Email Address"}

        bridge = SQLAdminBridge()
        bridge.register(UserAdmin)
        bridge.convert(UserAdmin)

        assert len(bridge.warnings) > 0
        bridge.clear_warnings()
        assert len(bridge.warnings) == 0

    def test_get_model_mapping(self, user_model, post_model) -> None:
        """Test getting model to view mapping."""

        class UserAdmin(MockSQLAdminModelView):
            model = user_model

        class PostAdmin(MockSQLAdminModelView):
            model = post_model

        bridge = SQLAdminBridge()
        bridge.register_many([UserAdmin, PostAdmin])
        bridge.convert_all()

        mapping = bridge.get_model_mapping()

        assert user_model in mapping
        assert post_model in mapping
        assert issubclass(mapping[user_model], BaseModelView)
        assert issubclass(mapping[post_model], BaseModelView)

    def test_contains(self, user_model) -> None:
        """Test __contains__ method."""

        class UserAdmin(MockSQLAdminModelView):
            model = user_model

        class OtherAdmin(MockSQLAdminModelView):
            model = user_model

        bridge = SQLAdminBridge()
        bridge.register(UserAdmin)

        assert UserAdmin in bridge
        assert OtherAdmin not in bridge

    def test_len(self, user_model, post_model) -> None:
        """Test __len__ method."""

        class UserAdmin(MockSQLAdminModelView):
            model = user_model

        class PostAdmin(MockSQLAdminModelView):
            model = post_model

        bridge = SQLAdminBridge()
        assert len(bridge) == 0

        bridge.register(UserAdmin)
        assert len(bridge) == 1

        bridge.register(PostAdmin)
        assert len(bridge) == 2


# ==============================================================================
# Test attribute mappings
# ==============================================================================


class TestAttributeMappings:
    """Tests for attribute mapping constants."""

    def test_sqladmin_attr_mapping_completeness(self) -> None:
        """Test that common sqladmin attributes are mapped."""
        expected_attrs = [
            "column_list",
            "column_exclude_list",
            "column_searchable_list",
            "column_sortable_list",
            "column_default_sort",
            "form_columns",
            "form_excluded_columns",
            "can_create",
            "can_edit",
            "can_delete",
            "can_view_details",
            "can_export",
            "name",
            "name_plural",
            "icon",
            "category",
            "page_size",
            "page_size_options",
        ]

        for attr in expected_attrs:
            assert attr in SQLADMIN_ATTR_MAPPING

    def test_sqladmin_specific_attrs_defined(self) -> None:
        """Test that sqladmin-specific attributes are defined."""
        expected_specific = [
            "column_labels",
            "column_formatters",
            "form_args",
            "form_widget_args",
            "form_overrides",
            "form_ajax_refs",
            "edit_modal",
            "create_modal",
            "details_modal",
        ]

        for attr in expected_specific:
            assert attr in SQLADMIN_SPECIFIC_ATTRS


# ==============================================================================
# Test integration with BaseModelView
# ==============================================================================


class TestIntegrationWithBaseModelView:
    """Integration tests with litestar-admin BaseModelView."""

    def test_converted_view_has_base_methods(self, user_model) -> None:
        """Test that converted view has BaseModelView methods."""

        class UserAdmin(MockSQLAdminModelView):
            model = user_model
            column_list = ["id", "email", "name"]
            column_sortable_list = ["id", "email"]
            column_searchable_list = ["email", "name"]

        converted = convert_sqladmin_view(UserAdmin)

        # Test inherited methods work
        columns = converted.get_list_columns()
        assert columns == ["id", "email", "name"]

        info = converted.get_column_info("email")
        assert info["name"] == "email"
        assert info["sortable"] is True
        assert info["searchable"] is True

    def test_converted_view_form_columns(self, user_model) -> None:
        """Test that form columns work on converted view."""

        class UserAdmin(MockSQLAdminModelView):
            model = user_model
            form_columns = ["email", "name"]

        converted = convert_sqladmin_view(UserAdmin)

        form_cols = converted.get_form_columns()
        assert form_cols == ["email", "name"]

    def test_converted_view_permissions_async(self, user_model) -> None:
        """Test that async permission methods are inherited."""

        class UserAdmin(MockSQLAdminModelView):
            model = user_model
            can_create = False
            can_delete = True

        converted = convert_sqladmin_view(UserAdmin)

        # These should be async methods from BaseModelView
        assert hasattr(converted, "is_accessible")
        assert hasattr(converted, "can_create_record")
        assert hasattr(converted, "can_delete_record")
