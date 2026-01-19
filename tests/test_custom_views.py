"""Tests for custom (non-model) view types.

This module contains unit and integration tests for:
- CustomView - Base class for non-model data sources
- ActionView - One-off admin operations
- PageView - Static and dynamic content pages
- LinkView - External navigation links
- EmbedView - Embedded external content and components
- InMemoryView - In-memory data provider
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest

from litestar_admin.contrib.providers.in_memory import InMemoryView
from litestar_admin.registry import ViewRegistry
from litestar_admin.views import (
    ActionResult,
    ActionView,
    ColumnDefinition,
    CustomView,
    EmbedView,
    FormField,
    LinkView,
    ListResult,
    PageView,
)

if TYPE_CHECKING:
    pass


# ==============================================================================
# Test Fixtures
# ==============================================================================


@pytest.fixture
def mock_connection() -> MagicMock:
    """Create a mock ASGI connection for testing access control."""
    connection = MagicMock(spec=["user", "headers", "scope"])
    connection.user = MagicMock()
    connection.user.id = 1
    connection.user.is_authenticated = True
    connection.headers = {}
    return connection


@pytest.fixture
def view_registry() -> ViewRegistry:
    """Create a fresh view registry for testing."""
    return ViewRegistry()


# ==============================================================================
# ColumnDefinition Tests
# ==============================================================================


class TestColumnDefinition:
    """Tests for ColumnDefinition dataclass."""

    def test_basic_column_definition(self) -> None:
        """Test basic column definition with defaults."""
        col = ColumnDefinition(name="email")

        assert col.name == "email"
        assert col.label == "Email"  # Auto-generated from name
        assert col.type == "string"
        assert col.sortable is False
        assert col.searchable is False
        assert col.filterable is False
        assert col.visible is True
        assert col.format is None
        assert col.render_template is None

    def test_column_with_custom_label(self) -> None:
        """Test column with custom label."""
        col = ColumnDefinition(name="user_email", label="Email Address")

        assert col.name == "user_email"
        assert col.label == "Email Address"

    def test_column_label_auto_generation(self) -> None:
        """Test label auto-generation from name with underscores."""
        col = ColumnDefinition(name="first_name")
        assert col.label == "First Name"

        col2 = ColumnDefinition(name="created_at_timestamp")
        assert col2.label == "Created At Timestamp"

    def test_column_types(self) -> None:
        """Test various column types."""
        types: list[str] = [
            "string",
            "integer",
            "float",
            "boolean",
            "datetime",
            "date",
            "time",
            "json",
            "text",
            "email",
            "url",
            "uuid",
        ]

        for col_type in types:
            col = ColumnDefinition(name="test", type=col_type)  # type: ignore[arg-type]
            assert col.type == col_type

    def test_column_with_all_options(self) -> None:
        """Test column with all options specified."""
        col = ColumnDefinition(
            name="price",
            label="Product Price",
            type="float",
            sortable=True,
            searchable=True,
            filterable=True,
            visible=True,
            format="currency",
            render_template="{{value | currency}}",
        )

        assert col.name == "price"
        assert col.label == "Product Price"
        assert col.type == "float"
        assert col.sortable is True
        assert col.searchable is True
        assert col.filterable is True
        assert col.visible is True
        assert col.format == "currency"
        assert col.render_template == "{{value | currency}}"


# ==============================================================================
# ListResult Tests
# ==============================================================================


class TestListResult:
    """Tests for ListResult dataclass."""

    def test_empty_list_result(self) -> None:
        """Test empty ListResult with defaults."""
        result = ListResult()

        assert result.items == []
        assert result.total == 0
        assert result.page == 1
        assert result.page_size == 25
        assert result.has_next is False
        assert result.has_prev is False

    def test_list_result_with_items(self) -> None:
        """Test ListResult with items and pagination info."""
        items = [{"id": 1, "name": "Item 1"}, {"id": 2, "name": "Item 2"}]
        result = ListResult(
            items=items,
            total=10,
            page=1,
            page_size=2,
        )

        assert result.items == items
        assert result.total == 10
        assert result.page == 1
        assert result.page_size == 2
        assert result.has_next is True  # 10 items, page 1 of 5
        assert result.has_prev is False  # First page

    def test_list_result_pagination_flags_middle_page(self) -> None:
        """Test pagination flags on middle page."""
        result = ListResult(
            items=[{"id": 1}],
            total=100,
            page=5,
            page_size=10,
        )

        assert result.has_next is True  # More pages after 5
        assert result.has_prev is True  # Pages before 5

    def test_list_result_pagination_flags_last_page(self) -> None:
        """Test pagination flags on last page."""
        result = ListResult(
            items=[{"id": 1}],
            total=50,
            page=5,
            page_size=10,
        )

        assert result.has_next is False  # Page 5 is last
        assert result.has_prev is True

    def test_list_result_single_page(self) -> None:
        """Test single page result."""
        result = ListResult(
            items=[{"id": 1}, {"id": 2}],
            total=2,
            page=1,
            page_size=10,
        )

        assert result.has_next is False
        assert result.has_prev is False


# ==============================================================================
# CustomView Tests
# ==============================================================================


class TestCustomView:
    """Tests for CustomView base class."""

    def test_custom_view_subclass_inherits_parent_name(self) -> None:
        """Test that CustomView subclasses inherit parent name without explicit override."""
        # Base CustomView has name="Custom" from its own __init_subclass__
        # Subclasses without explicit name inherit from parent

        class ProductsView(CustomView):
            columns = [ColumnDefinition(name="id")]

            async def get_list(self, **kwargs: Any) -> ListResult:
                return ListResult()

            async def get_one(self, item_id: str) -> dict[str, Any] | None:
                return None

        # Inherits from parent since no explicit name
        assert ProductsView.name == "Custom"
        assert ProductsView.view_type == "custom"

    def test_custom_view_subclass_with_name_and_identity(self) -> None:
        """Test that CustomView subclasses need explicit identity for unique routing."""
        # When subclassing CustomView, you must set identity explicitly
        # because the parent class already has identity="custom" set
        # The name_plural is also inherited from parent unless explicitly set

        class ProductsView(CustomView):
            name = "Products"
            identity = "products"  # Must be explicit
            name_plural = "Products"  # Must be explicit since parent has name_plural="Customs"
            columns = [ColumnDefinition(name="id")]

            async def get_list(self, **kwargs: Any) -> ListResult:
                return ListResult()

            async def get_one(self, item_id: str) -> dict[str, Any] | None:
                return None

        assert ProductsView.name == "Products"
        assert ProductsView.identity == "products"
        assert ProductsView.name_plural == "Products"
        assert ProductsView.view_type == "custom"

    def test_custom_view_explicit_name(self) -> None:
        """Test CustomView with explicit name."""

        class MyDataView(CustomView):
            name = "External Data"
            identity = "ext-data"
            name_plural = "External Data Items"
            columns = [ColumnDefinition(name="id")]

            async def get_list(self, **kwargs: Any) -> ListResult:
                return ListResult()

            async def get_one(self, item_id: str) -> dict[str, Any] | None:
                return None

        assert MyDataView.name == "External Data"
        assert MyDataView.identity == "ext-data"
        assert MyDataView.name_plural == "External Data Items"

    def test_custom_view_column_normalization_from_dict(self) -> None:
        """Test that dict columns are normalized to ColumnDefinition."""

        class DictColumnsView(CustomView):
            columns = [
                {"name": "id", "type": "integer"},
                {"name": "email", "type": "email", "searchable": True},
            ]

            async def get_list(self, **kwargs: Any) -> ListResult:
                return ListResult()

            async def get_one(self, item_id: str) -> dict[str, Any] | None:
                return None

        # Columns should be normalized to ColumnDefinition
        assert len(DictColumnsView.columns) == 2
        assert isinstance(DictColumnsView.columns[0], ColumnDefinition)
        assert isinstance(DictColumnsView.columns[1], ColumnDefinition)
        assert DictColumnsView.columns[0].type == "integer"
        assert DictColumnsView.columns[1].searchable is True

    def test_custom_view_default_permissions(self) -> None:
        """Test default permission values (read-only)."""

        class ReadOnlyView(CustomView):
            columns = [ColumnDefinition(name="id")]

            async def get_list(self, **kwargs: Any) -> ListResult:
                return ListResult()

            async def get_one(self, item_id: str) -> dict[str, Any] | None:
                return None

        # CustomView defaults to read-only
        assert ReadOnlyView.can_create is False
        assert ReadOnlyView.can_edit is False
        assert ReadOnlyView.can_delete is False
        assert ReadOnlyView.can_view_details is True
        assert ReadOnlyView.can_export is True

    def test_custom_view_with_crud_enabled(self) -> None:
        """Test CustomView with CRUD enabled."""

        class CrudView(CustomView):
            columns = [ColumnDefinition(name="id")]
            can_create = True
            can_edit = True
            can_delete = True

            async def get_list(self, **kwargs: Any) -> ListResult:
                return ListResult()

            async def get_one(self, item_id: str) -> dict[str, Any] | None:
                return None

        assert CrudView.can_create is True
        assert CrudView.can_edit is True
        assert CrudView.can_delete is True

    def test_get_list_columns(self) -> None:
        """Test get_list_columns returns only visible columns."""

        class VisibilityView(CustomView):
            columns = [
                ColumnDefinition(name="id", visible=True),
                ColumnDefinition(name="name", visible=True),
                ColumnDefinition(name="internal_id", visible=False),
            ]

            async def get_list(self, **kwargs: Any) -> ListResult:
                return ListResult()

            async def get_one(self, item_id: str) -> dict[str, Any] | None:
                return None

        visible = VisibilityView.get_list_columns()
        assert len(visible) == 2
        assert visible[0].name == "id"
        assert visible[1].name == "name"

    def test_get_searchable_columns(self) -> None:
        """Test get_searchable_columns returns only searchable columns."""

        class SearchView(CustomView):
            columns = [
                ColumnDefinition(name="id", searchable=False),
                ColumnDefinition(name="email", searchable=True),
                ColumnDefinition(name="name", searchable=True),
            ]

            async def get_list(self, **kwargs: Any) -> ListResult:
                return ListResult()

            async def get_one(self, item_id: str) -> dict[str, Any] | None:
                return None

        searchable = SearchView.get_searchable_columns()
        assert len(searchable) == 2
        names = [c.name for c in searchable]
        assert "email" in names
        assert "name" in names

    def test_get_sortable_columns(self) -> None:
        """Test get_sortable_columns returns only sortable columns."""

        class SortView(CustomView):
            columns = [
                ColumnDefinition(name="id", sortable=True),
                ColumnDefinition(name="name", sortable=True),
                ColumnDefinition(name="description", sortable=False),
            ]

            async def get_list(self, **kwargs: Any) -> ListResult:
                return ListResult()

            async def get_one(self, item_id: str) -> dict[str, Any] | None:
                return None

        sortable = SortView.get_sortable_columns()
        assert len(sortable) == 2

    def test_get_filterable_columns(self) -> None:
        """Test get_filterable_columns returns only filterable columns."""

        class FilterView(CustomView):
            columns = [
                ColumnDefinition(name="id", filterable=False),
                ColumnDefinition(name="status", filterable=True),
                ColumnDefinition(name="type", filterable=True),
            ]

            async def get_list(self, **kwargs: Any) -> ListResult:
                return ListResult()

            async def get_one(self, item_id: str) -> dict[str, Any] | None:
                return None

        filterable = FilterView.get_filterable_columns()
        assert len(filterable) == 2

    def test_get_column_by_name(self) -> None:
        """Test get_column_by_name returns correct column."""

        class FindView(CustomView):
            columns = [
                ColumnDefinition(name="id"),
                ColumnDefinition(name="email"),
                ColumnDefinition(name="name"),
            ]

            async def get_list(self, **kwargs: Any) -> ListResult:
                return ListResult()

            async def get_one(self, item_id: str) -> dict[str, Any] | None:
                return None

        col = FindView.get_column_by_name("email")
        assert col is not None
        assert col.name == "email"

        not_found = FindView.get_column_by_name("nonexistent")
        assert not_found is None

    def test_get_schema(self) -> None:
        """Test JSON schema generation."""

        class SchemaView(CustomView):
            columns = [
                ColumnDefinition(name="id", type="integer"),
                ColumnDefinition(name="email", type="email"),
                ColumnDefinition(name="active", type="boolean"),
                ColumnDefinition(name="created_at", type="datetime"),
            ]

            async def get_list(self, **kwargs: Any) -> ListResult:
                return ListResult()

            async def get_one(self, item_id: str) -> dict[str, Any] | None:
                return None

        schema = SchemaView.get_schema()

        assert schema["type"] == "object"
        assert "properties" in schema
        assert schema["properties"]["id"]["type"] == "integer"
        assert schema["properties"]["email"]["type"] == "string"
        assert schema["properties"]["email"]["format"] == "email"
        assert schema["properties"]["active"]["type"] == "boolean"
        assert schema["properties"]["created_at"]["type"] == "string"
        assert schema["properties"]["created_at"]["format"] == "date-time"

    def test_get_api_routes_read_only(self) -> None:
        """Test API routes for read-only custom view."""

        class ReadOnlyApiView(CustomView):
            name = "ReadOnly"
            columns = [ColumnDefinition(name="id")]
            can_create = False
            can_edit = False
            can_delete = False

            async def get_list(self, **kwargs: Any) -> ListResult:
                return ListResult()

            async def get_one(self, item_id: str) -> dict[str, Any] | None:
                return None

        routes = ReadOnlyApiView.get_api_routes()

        # Should have list and get routes only
        assert len(routes) == 2
        operations = [r["operation"] for r in routes]
        assert "list" in operations
        assert "get" in operations
        assert "create" not in operations
        assert "update" not in operations
        assert "delete" not in operations

    def test_get_api_routes_full_crud(self) -> None:
        """Test API routes with full CRUD enabled."""

        class CrudApiView(CustomView):
            name = "Crud"
            columns = [ColumnDefinition(name="id")]
            can_create = True
            can_edit = True
            can_delete = True

            async def get_list(self, **kwargs: Any) -> ListResult:
                return ListResult()

            async def get_one(self, item_id: str) -> dict[str, Any] | None:
                return None

        routes = CrudApiView.get_api_routes()

        # Should have all CRUD routes
        operations = [r["operation"] for r in routes]
        assert "list" in operations
        assert "get" in operations
        assert "create" in operations
        assert "update" in operations
        assert "delete" in operations

    def test_get_navigation_info(self) -> None:
        """Test navigation info includes custom view specific data."""

        class NavView(CustomView):
            name = "Navigation Test"
            icon = "database"
            category = "Data"
            pk_field = "uuid"
            can_create = True
            can_edit = False
            can_delete = True
            columns = [ColumnDefinition(name="uuid")]

            async def get_list(self, **kwargs: Any) -> ListResult:
                return ListResult()

            async def get_one(self, item_id: str) -> dict[str, Any] | None:
                return None

        info = NavView.get_navigation_info()

        assert info["name"] == "Navigation Test"
        assert info["icon"] == "database"
        assert info["category"] == "Data"
        assert info["view_type"] == "custom"
        assert info["pk_field"] == "uuid"
        assert info["can_create"] is True
        assert info["can_edit"] is False
        assert info["can_delete"] is True

    @pytest.mark.asyncio
    async def test_default_is_accessible(self, mock_connection: MagicMock) -> None:
        """Test default is_accessible returns can_access value."""

        class AccessView(CustomView):
            can_access = True
            columns = [ColumnDefinition(name="id")]

            async def get_list(self, **kwargs: Any) -> ListResult:
                return ListResult()

            async def get_one(self, item_id: str) -> dict[str, Any] | None:
                return None

        assert await AccessView.is_accessible(mock_connection) is True

        class NoAccessView(CustomView):
            can_access = False
            columns = [ColumnDefinition(name="id")]

            async def get_list(self, **kwargs: Any) -> ListResult:
                return ListResult()

            async def get_one(self, item_id: str) -> dict[str, Any] | None:
                return None

        assert await NoAccessView.is_accessible(mock_connection) is False

    @pytest.mark.asyncio
    async def test_crud_raises_not_implemented(self) -> None:
        """Test that default create/update/delete raise NotImplementedError."""

        class BasicView(CustomView):
            columns = [ColumnDefinition(name="id")]

            async def get_list(self, **kwargs: Any) -> ListResult:
                return ListResult()

            async def get_one(self, item_id: str) -> dict[str, Any] | None:
                return None

        view = BasicView()

        with pytest.raises(NotImplementedError, match="does not support create"):
            await view.create({"id": 1})

        with pytest.raises(NotImplementedError, match="does not support update"):
            await view.update("1", {"name": "test"})

        with pytest.raises(NotImplementedError, match="does not support delete"):
            await view.delete("1")

    @pytest.mark.asyncio
    async def test_hooks_are_called(self) -> None:
        """Test that lifecycle hooks are called."""
        hook_calls: list[str] = []

        class HookedView(CustomView):
            columns = [ColumnDefinition(name="id")]
            can_create = True
            can_edit = True
            can_delete = True
            _data: dict[str, dict[str, Any]] = {}

            async def get_list(self, **kwargs: Any) -> ListResult:
                return ListResult(items=list(self._data.values()), total=len(self._data))

            async def get_one(self, item_id: str) -> dict[str, Any] | None:
                return self._data.get(item_id)

            async def create(self, data: dict[str, Any]) -> dict[str, Any]:
                self._data[str(data["id"])] = data
                return data

            async def update(self, item_id: str, data: dict[str, Any]) -> dict[str, Any]:
                self._data[item_id].update(data)
                return self._data[item_id]

            async def delete(self, item_id: str) -> bool:
                del self._data[item_id]
                return True

            async def on_before_create(self, data: dict[str, Any]) -> dict[str, Any]:
                hook_calls.append("on_before_create")
                return data

            async def on_after_create(self, item: dict[str, Any]) -> None:
                hook_calls.append("on_after_create")

            async def on_before_update(self, item_id: str, data: dict[str, Any]) -> dict[str, Any]:
                hook_calls.append("on_before_update")
                return data

            async def on_after_update(self, item: dict[str, Any]) -> None:
                hook_calls.append("on_after_update")

            async def on_before_delete(self, item_id: str) -> None:
                hook_calls.append("on_before_delete")

            async def on_after_delete(self, item_id: str) -> None:
                hook_calls.append("on_after_delete")

        view = HookedView()

        # Test create hooks
        data = await view.on_before_create({"id": 1, "name": "test"})
        await view.create(data)
        await view.on_after_create(data)
        assert "on_before_create" in hook_calls
        assert "on_after_create" in hook_calls

        # Test update hooks
        data = await view.on_before_update("1", {"name": "updated"})
        await view.update("1", data)
        await view.on_after_update({"id": 1, "name": "updated"})
        assert "on_before_update" in hook_calls
        assert "on_after_update" in hook_calls

        # Test delete hooks
        await view.on_before_delete("1")
        await view.delete("1")
        await view.on_after_delete("1")
        assert "on_before_delete" in hook_calls
        assert "on_after_delete" in hook_calls


# ==============================================================================
# ActionView Tests
# ==============================================================================


class TestFormField:
    """Tests for FormField dataclass."""

    def test_basic_form_field(self) -> None:
        """Test basic form field with defaults."""
        field = FormField(name="username", label="Username")

        assert field.name == "username"
        assert field.label == "Username"
        assert field.field_type == "text"
        assert field.required is False
        assert field.default is None
        assert field.placeholder == ""
        assert field.help_text == ""
        assert field.options == []
        assert field.validation == {}

    def test_form_field_types(self) -> None:
        """Test various form field types."""
        types = [
            "text",
            "textarea",
            "number",
            "email",
            "password",
            "select",
            "multiselect",
            "checkbox",
            "radio",
            "date",
            "datetime",
            "file",
            "hidden",
        ]

        for field_type in types:
            field = FormField(name="test", label="Test", field_type=field_type)  # type: ignore[arg-type]
            assert field.field_type == field_type

    def test_form_field_with_options(self) -> None:
        """Test form field with options for select/radio."""
        field = FormField(
            name="status",
            label="Status",
            field_type="select",
            required=True,
            options=[
                {"value": "active", "label": "Active"},
                {"value": "inactive", "label": "Inactive"},
            ],
        )

        assert field.field_type == "select"
        assert len(field.options) == 2
        assert field.options[0]["value"] == "active"

    def test_form_field_to_dict(self) -> None:
        """Test to_dict serialization."""
        field = FormField(
            name="email",
            label="Email Address",
            field_type="email",
            required=True,
            placeholder="user@example.com",
            help_text="Enter your email",
            validation={"pattern": r"^\S+@\S+\.\S+$"},
        )

        result = field.to_dict()

        assert result["name"] == "email"
        assert result["label"] == "Email Address"
        assert result["type"] == "email"
        assert result["required"] is True
        assert result["placeholder"] == "user@example.com"
        assert result["helpText"] == "Enter your email"
        assert "pattern" in result["validation"]


class TestActionResult:
    """Tests for ActionResult dataclass."""

    def test_success_result(self) -> None:
        """Test successful action result."""
        result = ActionResult(success=True, message="Operation completed")

        assert result.success is True
        assert result.message == "Operation completed"
        assert result.redirect is None
        assert result.data == {}
        assert result.refresh is False

    def test_failure_result(self) -> None:
        """Test failed action result."""
        result = ActionResult(success=False, message="Operation failed: Invalid input")

        assert result.success is False
        assert result.message == "Operation failed: Invalid input"

    def test_result_with_redirect(self) -> None:
        """Test action result with redirect."""
        result = ActionResult(
            success=True,
            message="Export complete",
            redirect="/admin/exports/download/123",
        )

        assert result.redirect == "/admin/exports/download/123"

    def test_result_with_data(self) -> None:
        """Test action result with additional data."""
        result = ActionResult(
            success=True,
            message="Cache cleared",
            data={"cleared_entries": 1523, "cache_type": "all"},
        )

        assert result.data["cleared_entries"] == 1523
        assert result.data["cache_type"] == "all"

    def test_result_with_refresh(self) -> None:
        """Test action result with refresh flag."""
        result = ActionResult(success=True, message="Updated", refresh=True)

        assert result.refresh is True

    def test_result_to_dict(self) -> None:
        """Test to_dict serialization."""
        result = ActionResult(
            success=True,
            message="Done",
            redirect="/admin/home",
            data={"count": 5},
            refresh=True,
        )

        result_dict = result.to_dict()

        assert result_dict["success"] is True
        assert result_dict["message"] == "Done"
        assert result_dict["redirect"] == "/admin/home"
        assert result_dict["data"]["count"] == 5
        assert result_dict["refresh"] is True


class TestActionView:
    """Tests for ActionView class."""

    def test_action_view_subclass_auto_names(self) -> None:
        """Test ActionView subclass auto-generates name and identity."""

        class ClearCacheAction(ActionView):
            async def execute(self, data: dict[str, Any]) -> ActionResult:
                return ActionResult(success=True, message="Cleared")

        assert ClearCacheAction.name == "ClearCache"
        assert ClearCacheAction.identity == "clearcache"
        assert ClearCacheAction.view_type == "action"

    def test_action_view_explicit_name(self) -> None:
        """Test ActionView with explicit name."""

        class MyAction(ActionView):
            name = "Clear Application Cache"

            async def execute(self, data: dict[str, Any]) -> ActionResult:
                return ActionResult(success=True, message="Done")

        assert MyAction.name == "Clear Application Cache"
        assert MyAction.identity == "clear-application-cache"

    def test_action_view_form_fields(self) -> None:
        """Test ActionView with form fields."""

        class ConfiguredAction(ActionView):
            name = "Send Notification"
            form_fields = [
                FormField(name="message", label="Message", field_type="textarea", required=True),
                FormField(
                    name="priority",
                    label="Priority",
                    field_type="select",
                    options=[
                        {"value": "low", "label": "Low"},
                        {"value": "high", "label": "High"},
                    ],
                ),
            ]

            async def execute(self, data: dict[str, Any]) -> ActionResult:
                return ActionResult(success=True, message="Sent")

        assert len(ConfiguredAction.form_fields) == 2
        assert ConfiguredAction.form_fields[0].name == "message"
        assert ConfiguredAction.form_fields[0].required is True

    def test_action_view_confirmation_settings(self) -> None:
        """Test ActionView confirmation settings."""

        class DangerousAction(ActionView):
            name = "Delete All Data"
            confirmation_message = "Are you sure? This cannot be undone!"
            requires_confirmation = True
            dangerous = True

            async def execute(self, data: dict[str, Any]) -> ActionResult:
                return ActionResult(success=True, message="Deleted")

        assert DangerousAction.confirmation_message == "Are you sure? This cannot be undone!"
        assert DangerousAction.requires_confirmation is True
        assert DangerousAction.dangerous is True

    def test_action_view_auto_confirmation(self) -> None:
        """Test that confirmation_message auto-enables requires_confirmation."""

        class AutoConfirmAction(ActionView):
            name = "Auto Confirm"
            confirmation_message = "Please confirm"
            requires_confirmation = False  # Explicitly set to False

            async def execute(self, data: dict[str, Any]) -> ActionResult:
                return ActionResult(success=True, message="Done")

        # Should be set to True because confirmation_message is set
        assert AutoConfirmAction.requires_confirmation is True

    def test_action_view_default_settings(self) -> None:
        """Test ActionView default settings."""

        class DefaultAction(ActionView):
            async def execute(self, data: dict[str, Any]) -> ActionResult:
                return ActionResult(success=True, message="Done")

        assert DefaultAction.submit_label == "Execute"
        assert DefaultAction.success_redirect is None
        assert DefaultAction.dangerous is False
        assert DefaultAction.run_in_background is False
        assert DefaultAction.timeout_seconds == 60

    def test_get_form_schema(self) -> None:
        """Test get_form_schema returns form field definitions."""

        class FormAction(ActionView):
            name = "Form Action"
            form_fields = [
                FormField(name="name", label="Name", required=True),
                FormField(name="email", label="Email", field_type="email"),
            ]

            async def execute(self, data: dict[str, Any]) -> ActionResult:
                return ActionResult(success=True, message="Done")

        schema = FormAction.get_form_schema()

        assert len(schema) == 2
        assert schema[0]["name"] == "name"
        assert schema[0]["required"] is True
        assert schema[1]["type"] == "email"

    def test_get_action_info(self) -> None:
        """Test get_action_info returns complete action metadata."""

        class InfoAction(ActionView):
            name = "Test Action"
            icon = "play"
            confirmation_message = "Confirm?"
            submit_label = "Run"
            dangerous = True
            form_fields = [FormField(name="param", label="Parameter")]

            async def execute(self, data: dict[str, Any]) -> ActionResult:
                return ActionResult(success=True, message="Done")

        info = InfoAction.get_action_info()

        assert info["name"] == "Test Action"
        assert info["identity"] == "test-action"
        assert info["icon"] == "play"
        assert info["confirmationMessage"] == "Confirm?"
        assert info["submitLabel"] == "Run"
        assert info["dangerous"] is True
        assert len(info["formFields"]) == 1

    def test_get_api_routes(self) -> None:
        """Test API routes for action view."""

        class RoutesAction(ActionView):
            name = "Routes"

            async def execute(self, data: dict[str, Any]) -> ActionResult:
                return ActionResult(success=True, message="Done")

        routes = RoutesAction.get_api_routes()

        assert len(routes) == 2
        operations = [r["operation"] for r in routes]
        assert "info" in operations
        assert "execute" in operations

        # Check paths
        paths = [r["path"] for r in routes]
        assert any("/api/actions/routes" in p for p in paths)

    @pytest.mark.asyncio
    async def test_validate_data_required_fields(self) -> None:
        """Test validate_data checks required fields."""

        class RequiredAction(ActionView):
            name = "Required"
            form_fields = [
                FormField(name="required_field", label="Required", required=True),
                FormField(name="optional_field", label="Optional", required=False),
            ]

            async def execute(self, data: dict[str, Any]) -> ActionResult:
                return ActionResult(success=True, message="Done")

        # Missing required field
        is_valid, error = await RequiredAction.validate_data({"optional_field": "value"})
        assert is_valid is False
        assert "Required" in error

        # Empty required field
        is_valid, error = await RequiredAction.validate_data({"required_field": ""})
        assert is_valid is False

        # Valid data
        is_valid, error = await RequiredAction.validate_data({"required_field": "value"})
        assert is_valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_can_execute(self, mock_connection: MagicMock) -> None:
        """Test can_execute checks access."""

        class AccessibleAction(ActionView):
            name = "Accessible"
            can_access = True

            async def execute(self, data: dict[str, Any]) -> ActionResult:
                return ActionResult(success=True, message="Done")

        assert await AccessibleAction.can_execute(mock_connection) is True

        class InaccessibleAction(ActionView):
            name = "Inaccessible"
            can_access = False

            async def execute(self, data: dict[str, Any]) -> ActionResult:
                return ActionResult(success=True, message="Done")

        assert await InaccessibleAction.can_execute(mock_connection) is False

    @pytest.mark.asyncio
    async def test_execute(self) -> None:
        """Test action execution."""

        class ExecuteAction(ActionView):
            name = "Execute"

            async def execute(self, data: dict[str, Any]) -> ActionResult:
                count = data.get("count", 0)
                return ActionResult(
                    success=True,
                    message=f"Processed {count} items",
                    data={"count": count},
                )

        action = ExecuteAction()
        result = await action.execute({"count": 10})

        assert result.success is True
        assert "10" in result.message
        assert result.data["count"] == 10


# ==============================================================================
# PageView Tests
# ==============================================================================


class TestPageView:
    """Tests for PageView class."""

    def test_page_view_subclass_inherits_parent_name(self) -> None:
        """Test PageView subclass inherits parent name without explicit override."""
        # Base PageView has name="Page" from its own __init_subclass__

        class AboutPage(PageView):
            pass

        # Inherits from parent since no explicit name
        assert AboutPage.name == "Page"
        assert AboutPage.view_type == "page"

    def test_page_view_subclass_explicit_name(self) -> None:
        """Test PageView subclass with explicit name gets proper identity."""

        class AboutPage(PageView):
            name = "About"

        assert AboutPage.name == "About"
        assert AboutPage.identity == "about"
        assert AboutPage.name_plural == "About"  # Pages don't pluralize
        assert AboutPage.view_type == "page"

    def test_page_view_explicit_name(self) -> None:
        """Test PageView with explicit name."""

        class MyPage(PageView):
            name = "Help Center"
            identity = "help"

        assert MyPage.name == "Help Center"
        assert MyPage.identity == "help"

    def test_page_view_static_markdown_content(self) -> None:
        """Test PageView with static markdown content."""

        class MarkdownPage(PageView):
            name = "Documentation"
            content_type = "markdown"
            content = """
            # Welcome

            This is **bold** text.
            """

        assert MarkdownPage.content_type == "markdown"
        assert "# Welcome" in MarkdownPage.content
        assert "**bold**" in MarkdownPage.content

    def test_page_view_static_html_content(self) -> None:
        """Test PageView with static HTML content."""

        class HtmlPage(PageView):
            name = "HTML Page"
            content_type = "html"
            content = "<h1>Welcome</h1><p>This is HTML content.</p>"

        assert HtmlPage.content_type == "html"
        assert "<h1>" in HtmlPage.content

    def test_page_view_static_text_content(self) -> None:
        """Test PageView with static text content."""

        class TextPage(PageView):
            name = "Plain Text"
            content_type = "text"
            content = "This is plain text content."

        assert TextPage.content_type == "text"
        assert TextPage.content == "This is plain text content."

    def test_page_view_dynamic_content_type(self) -> None:
        """Test PageView with dynamic content type."""

        class DynamicPage(PageView):
            name = "Dashboard"
            content_type = "dynamic"
            refresh_interval = 60

            async def get_content(self) -> dict[str, Any]:
                return {
                    "type": "dashboard",
                    "widgets": [
                        {"type": "stat", "title": "Users", "value": 100},
                    ],
                }

        assert DynamicPage.content_type == "dynamic"
        assert DynamicPage.refresh_interval == 60

    def test_page_view_layout_options(self) -> None:
        """Test PageView layout options."""

        class DefaultLayoutPage(PageView):
            name = "Default Layout"
            layout = "default"

        assert DefaultLayoutPage.layout == "default"

        class FullWidthLayoutPage(PageView):
            name = "Full Width Layout"
            layout = "full-width"

        assert FullWidthLayoutPage.layout == "full-width"

        class SidebarLayoutPage(PageView):
            name = "Sidebar Layout"
            layout = "sidebar"

        assert SidebarLayoutPage.layout == "sidebar"

    def test_get_page_metadata(self) -> None:
        """Test get_page_metadata returns complete metadata."""

        class MetaPage(PageView):
            name = "Meta Page"
            icon = "info-circle"
            content_type = "markdown"
            content = "# Hello"
            layout = "full-width"
            refresh_interval = 0

        metadata = MetaPage.get_page_metadata()

        assert metadata["name"] == "Meta Page"
        assert metadata["identity"] == "meta-page"
        assert metadata["icon"] == "info-circle"
        assert metadata["content_type"] == "markdown"
        assert metadata["content"] == "# Hello"
        assert metadata["layout"] == "full-width"
        assert metadata["refresh_interval"] == 0

    def test_get_page_metadata_dynamic_no_content(self) -> None:
        """Test get_page_metadata for dynamic pages excludes content."""

        class DynamicMetaPage(PageView):
            name = "Dynamic"
            content_type = "dynamic"

        metadata = DynamicMetaPage.get_page_metadata()

        assert "content" not in metadata or metadata.get("content") is None

    def test_get_navigation_info(self) -> None:
        """Test navigation info includes page-specific data."""

        class NavPage(PageView):
            name = "Nav Page"
            content_type = "html"
            layout = "sidebar"

        info = NavPage.get_navigation_info()

        assert info["view_type"] == "page"
        assert info["content_type"] == "html"
        assert info["layout"] == "sidebar"

    def test_get_api_routes_static_content(self) -> None:
        """Test API routes for static content page."""

        class StaticPage(PageView):
            name = "Static"
            content_type = "markdown"

        routes = StaticPage.get_api_routes()

        # Static pages only have metadata route
        assert len(routes) == 1
        assert routes[0]["operation"] == "metadata"

    def test_get_api_routes_dynamic_content(self) -> None:
        """Test API routes for dynamic content page."""

        class DynamicRoutePage(PageView):
            name = "Dynamic Routes"
            content_type = "dynamic"

        routes = DynamicRoutePage.get_api_routes()

        # Dynamic pages have metadata and content routes
        assert len(routes) == 2
        operations = [r["operation"] for r in routes]
        assert "metadata" in operations
        assert "content" in operations

    def test_get_api_routes_template_content(self) -> None:
        """Test API routes for template content page."""

        class TemplatePage(PageView):
            name = "Template"
            content_type = "template"
            template = "admin/custom_page.html"

        routes = TemplatePage.get_api_routes()

        # Template pages have metadata and render routes
        assert len(routes) == 2
        operations = [r["operation"] for r in routes]
        assert "metadata" in operations
        assert "render" in operations

    @pytest.mark.asyncio
    async def test_get_content_default(self) -> None:
        """Test default get_content returns empty dict."""

        class DefaultContentPage(PageView):
            name = "Default"

        page = DefaultContentPage()
        content = await page.get_content()

        assert content == {}

    @pytest.mark.asyncio
    async def test_get_content_override(self) -> None:
        """Test get_content can be overridden."""

        class CustomContentPage(PageView):
            name = "Custom"
            content_type = "dynamic"

            async def get_content(self) -> dict[str, Any]:
                return {
                    "users_count": 100,
                    "active_sessions": 25,
                }

        page = CustomContentPage()
        content = await page.get_content()

        assert content["users_count"] == 100
        assert content["active_sessions"] == 25

    @pytest.mark.asyncio
    async def test_get_template_context(self, mock_connection: MagicMock) -> None:
        """Test get_template_context returns static context by default."""

        class TemplateContextPage(PageView):
            name = "Context"
            template_context = {"title": "My Page", "version": "1.0"}

        page = TemplateContextPage()
        context = await page.get_template_context(mock_connection)

        assert context["title"] == "My Page"
        assert context["version"] == "1.0"


# ==============================================================================
# LinkView Tests
# ==============================================================================


class TestLinkView:
    """Tests for LinkView class."""

    def test_link_view_subclass_inherits_parent_name(self) -> None:
        """Test LinkView subclass inherits parent name without explicit override."""
        # Base LinkView has name="Link" from its own __init_subclass__

        class DocsLink(LinkView):
            url = "https://docs.example.com"

        # Inherits from parent since no explicit name
        assert DocsLink.name == "Link"
        assert DocsLink.view_type == "link"

    def test_link_view_subclass_explicit_name(self) -> None:
        """Test LinkView subclass with explicit name gets proper identity."""

        class DocsLink(LinkView):
            name = "Documentation"
            url = "https://docs.example.com"

        assert DocsLink.name == "Documentation"
        assert DocsLink.identity == "documentation"
        assert DocsLink.name_plural == "Documentation"  # Links don't pluralize
        assert DocsLink.view_type == "link"

    def test_link_view_url_and_target(self) -> None:
        """Test LinkView URL and target attributes."""

        class ExternalLink(LinkView):
            name = "External Docs"
            url = "https://external.example.com/docs"
            target = "_blank"

        assert ExternalLink.url == "https://external.example.com/docs"
        assert ExternalLink.target == "_blank"

    def test_link_view_same_window_target(self) -> None:
        """Test LinkView with same window target."""

        class InternalLink(LinkView):
            name = "API Docs"
            url = "/api/docs"
            target = "_self"

        assert InternalLink.url == "/api/docs"
        assert InternalLink.target == "_self"

    def test_get_api_routes_empty(self) -> None:
        """Test LinkView returns no API routes."""

        class NoRoutesLink(LinkView):
            name = "No Routes"
            url = "https://example.com"

        routes = NoRoutesLink.get_api_routes()

        assert routes == []

    def test_get_navigation_info(self) -> None:
        """Test navigation info includes link-specific data."""

        class NavLink(LinkView):
            name = "Documentation"
            icon = "book"
            url = "https://docs.example.com"
            target = "_blank"
            category = "External"

        info = NavLink.get_navigation_info()

        assert info["name"] == "Documentation"
        assert info["icon"] == "book"
        assert info["view_type"] == "link"
        assert info["url"] == "https://docs.example.com"
        assert info["target"] == "_blank"
        assert info["category"] == "External"

    def test_get_url_default(self) -> None:
        """Test default get_url returns static URL."""

        class StaticUrlLink(LinkView):
            name = "Static"
            url = "https://static.example.com"

        link = StaticUrlLink()
        assert link.get_url() == "https://static.example.com"

    def test_get_url_override(self) -> None:
        """Test get_url can be overridden for dynamic URLs."""

        class DynamicUrlLink(LinkView):
            name = "Dynamic"
            url = "https://default.example.com"

            def get_url(self) -> str:
                # Could check environment, configuration, etc.
                return "https://dynamic.example.com"

        link = DynamicUrlLink()
        assert link.get_url() == "https://dynamic.example.com"

    @pytest.mark.asyncio
    async def test_is_accessible(self, mock_connection: MagicMock) -> None:
        """Test is_accessible respects can_access."""

        class AccessibleLink(LinkView):
            name = "Accessible"
            url = "https://example.com"
            can_access = True

        assert await AccessibleLink.is_accessible(mock_connection) is True

        class HiddenLink(LinkView):
            name = "Hidden"
            url = "https://example.com"
            can_access = False

        assert await HiddenLink.is_accessible(mock_connection) is False


# ==============================================================================
# EmbedView Tests
# ==============================================================================


class TestEmbedView:
    """Tests for EmbedView class."""

    def test_embed_view_subclass_inherits_parent_name(self) -> None:
        """Test EmbedView subclass inherits parent name without explicit override."""
        # Base EmbedView has name="Embed" from its own __init_subclass__

        class MetricsEmbed(EmbedView):
            embed_type = "iframe"
            embed_url = "https://grafana.example.com"

        # Inherits from parent since no explicit name
        assert MetricsEmbed.name == "Embed"
        assert MetricsEmbed.view_type == "embed"

    def test_embed_view_subclass_explicit_name(self) -> None:
        """Test EmbedView subclass with explicit name gets proper identity."""

        class MetricsEmbed(EmbedView):
            name = "Metrics"
            embed_type = "iframe"
            embed_url = "https://grafana.example.com"

        assert MetricsEmbed.name == "Metrics"
        assert MetricsEmbed.identity == "metrics"
        assert MetricsEmbed.view_type == "embed"

    def test_embed_view_iframe_configuration(self) -> None:
        """Test EmbedView iframe configuration."""

        class IframeEmbed(EmbedView):
            name = "Dashboard"
            embed_type = "iframe"
            embed_url = "https://dashboard.example.com"
            width = "100%"
            height = "800px"
            min_height = "600px"
            sandbox = "allow-scripts allow-same-origin"
            allow = "fullscreen"
            loading = "lazy"
            referrer_policy = "no-referrer"

        assert IframeEmbed.embed_type == "iframe"
        assert IframeEmbed.embed_url == "https://dashboard.example.com"
        assert IframeEmbed.width == "100%"
        assert IframeEmbed.height == "800px"
        assert IframeEmbed.min_height == "600px"
        assert IframeEmbed.sandbox == "allow-scripts allow-same-origin"
        assert IframeEmbed.allow == "fullscreen"
        assert IframeEmbed.loading == "lazy"
        assert IframeEmbed.referrer_policy == "no-referrer"

    def test_embed_view_component_configuration(self) -> None:
        """Test EmbedView component configuration."""

        class ComponentEmbed(EmbedView):
            name = "Activity Feed"
            embed_type = "component"
            component_name = "ActivityFeed"
            props = {"limit": 20, "showTimestamps": True}

        assert ComponentEmbed.embed_type == "component"
        assert ComponentEmbed.component_name == "ActivityFeed"
        assert ComponentEmbed.props["limit"] == 20
        assert ComponentEmbed.props["showTimestamps"] is True

    def test_embed_view_layout_options(self) -> None:
        """Test EmbedView layout options."""

        class FullEmbed(EmbedView):
            name = "Full"
            embed_type = "iframe"
            embed_url = "https://example.com"
            layout = "full"

        assert FullEmbed.layout == "full"

        class SidebarEmbed(EmbedView):
            name = "Sidebar"
            embed_type = "iframe"
            embed_url = "https://example.com"
            layout = "sidebar"

        assert SidebarEmbed.layout == "sidebar"

        class CardEmbed(EmbedView):
            name = "Card"
            embed_type = "iframe"
            embed_url = "https://example.com"
            layout = "card"

        assert CardEmbed.layout == "card"

    def test_embed_view_validation_iframe_no_url(self) -> None:
        """Test EmbedView validation requires embed_url for iframe type."""
        with pytest.raises(ValueError, match="requires embed_url"):

            class InvalidIframeEmbed(EmbedView):
                name = "Invalid"
                embed_type = "iframe"
                # Missing embed_url

    def test_embed_view_validation_component_no_name(self) -> None:
        """Test EmbedView validation requires component_name for component type."""
        with pytest.raises(ValueError, match="requires component_name"):

            class InvalidComponentEmbed(EmbedView):
                name = "Invalid"
                embed_type = "component"
                # Missing component_name

    def test_get_embed_config_iframe(self) -> None:
        """Test get_embed_config for iframe type."""

        class IframeConfigEmbed(EmbedView):
            name = "Iframe Config"
            embed_type = "iframe"
            embed_url = "https://example.com/embed"
            width = "100%"
            height = "600px"
            sandbox = "allow-scripts"
            show_toolbar = True

        embed = IframeConfigEmbed()
        config = embed.get_embed_config()

        assert config["type"] == "iframe"
        assert config["url"] == "https://example.com/embed"
        assert config["width"] == "100%"
        assert config["height"] == "600px"
        assert config["sandbox"] == "allow-scripts"
        assert config["show_toolbar"] is True

    def test_get_embed_config_component(self) -> None:
        """Test get_embed_config for component type."""

        class ComponentConfigEmbed(EmbedView):
            name = "Component Config"
            embed_type = "component"
            component_name = "CustomWidget"
            props = {"theme": "dark"}

        embed = ComponentConfigEmbed()
        config = embed.get_embed_config()

        assert config["type"] == "component"
        assert config["component_name"] == "CustomWidget"
        assert config["props"]["theme"] == "dark"

    def test_get_navigation_info(self) -> None:
        """Test navigation info includes embed-specific data."""

        class NavEmbed(EmbedView):
            name = "Navigation Embed"
            embed_type = "iframe"
            embed_url = "https://example.com"
            layout = "sidebar"

        info = NavEmbed.get_navigation_info()

        assert info["view_type"] == "embed"
        assert info["embed_type"] == "iframe"
        assert info["layout"] == "sidebar"

    def test_get_api_routes(self) -> None:
        """Test API routes for embed view."""

        class RoutesEmbed(EmbedView):
            name = "Routes"
            embed_type = "iframe"
            embed_url = "https://example.com"

        routes = RoutesEmbed.get_api_routes()

        assert len(routes) == 2
        operations = [r["operation"] for r in routes]
        assert "config" in operations
        assert "props" in operations

    @pytest.mark.asyncio
    async def test_get_props_default(self, mock_connection: MagicMock) -> None:
        """Test default get_props returns static props."""

        class StaticPropsEmbed(EmbedView):
            name = "Static Props"
            embed_type = "component"
            component_name = "Widget"
            props = {"key": "value"}

        embed = StaticPropsEmbed()
        props = await embed.get_props(mock_connection)

        assert props["key"] == "value"

    @pytest.mark.asyncio
    async def test_get_props_override(self, mock_connection: MagicMock) -> None:
        """Test get_props can be overridden for dynamic props."""

        class DynamicPropsEmbed(EmbedView):
            name = "Dynamic Props"
            embed_type = "component"
            component_name = "Widget"

            async def get_props(self, connection: Any) -> dict[str, Any]:
                return {
                    "userId": connection.user.id,
                    "timestamp": "2024-01-01",
                }

        embed = DynamicPropsEmbed()
        props = await embed.get_props(mock_connection)

        assert props["userId"] == 1
        assert props["timestamp"] == "2024-01-01"

    @pytest.mark.asyncio
    async def test_get_embed_url_default(self, mock_connection: MagicMock) -> None:
        """Test default get_embed_url returns static URL."""

        class StaticUrlEmbed(EmbedView):
            name = "Static URL"
            embed_type = "iframe"
            embed_url = "https://static.example.com"

        embed = StaticUrlEmbed()
        url = await embed.get_embed_url(mock_connection)

        assert url == "https://static.example.com"

    @pytest.mark.asyncio
    async def test_get_embed_url_override(self, mock_connection: MagicMock) -> None:
        """Test get_embed_url can be overridden for dynamic URLs."""

        class DynamicUrlEmbed(EmbedView):
            name = "Dynamic URL"
            embed_type = "iframe"
            embed_url = "https://base.example.com"

            async def get_embed_url(self, connection: Any) -> str:
                user_id = connection.user.id
                return f"{self.embed_url}?user={user_id}"

        embed = DynamicUrlEmbed()
        url = await embed.get_embed_url(mock_connection)

        assert url == "https://base.example.com?user=1"

    @pytest.mark.asyncio
    async def test_get_full_config_iframe(self, mock_connection: MagicMock) -> None:
        """Test get_full_config resolves dynamic URL for iframe."""

        class FullConfigIframeEmbed(EmbedView):
            name = "Full Config Iframe"
            embed_type = "iframe"
            embed_url = "https://base.example.com"

            async def get_embed_url(self, connection: Any) -> str:
                return "https://resolved.example.com"

        embed = FullConfigIframeEmbed()
        config = await embed.get_full_config(mock_connection)

        assert config["url"] == "https://resolved.example.com"

    @pytest.mark.asyncio
    async def test_get_full_config_component(self, mock_connection: MagicMock) -> None:
        """Test get_full_config resolves dynamic props for component."""

        class FullConfigComponentEmbed(EmbedView):
            name = "Full Config Component"
            embed_type = "component"
            component_name = "Widget"

            async def get_props(self, connection: Any) -> dict[str, Any]:
                return {"dynamic": True, "userId": connection.user.id}

        embed = FullConfigComponentEmbed()
        config = await embed.get_full_config(mock_connection)

        assert config["props"]["dynamic"] is True
        assert config["props"]["userId"] == 1


# ==============================================================================
# InMemoryView Tests
# ==============================================================================


class TestInMemoryView:
    """Tests for InMemoryView provider."""

    @pytest.fixture(autouse=True)
    def cleanup_data(self) -> None:
        """Clean up test data before and after each test."""
        # Create a fresh class for each test to avoid data leakage
        pass

    def _create_test_view(self) -> type[InMemoryView]:
        """Create a fresh InMemoryView subclass for testing."""

        class TestSettingsView(InMemoryView):
            name = "Test Settings"
            pk_field = "key"
            columns = [
                ColumnDefinition(name="key", type="string", sortable=True, searchable=True),
                ColumnDefinition(name="value", type="string", searchable=True),
                ColumnDefinition(name="description", type="text"),
            ]
            # Fresh data store for each test class
            _data: dict[str, dict[str, Any]] = {}

        return TestSettingsView

    def test_in_memory_view_defaults(self) -> None:
        """Test InMemoryView default settings."""
        view_class = self._create_test_view()

        # InMemoryView defaults to CRUD enabled
        assert view_class.can_create is True
        assert view_class.can_edit is True
        assert view_class.can_delete is True
        assert view_class.auto_generate_pk is True

    def test_seed_data(self) -> None:
        """Test seeding data into InMemoryView."""
        view_class = self._create_test_view()

        view_class.seed_data(
            [
                {"key": "theme", "value": "dark", "description": "UI theme"},
                {"key": "language", "value": "en", "description": "Language"},
            ]
        )

        assert len(view_class._data) == 2
        assert view_class._data["theme"]["value"] == "dark"
        assert view_class._data["language"]["value"] == "en"

    def test_clear_data(self) -> None:
        """Test clearing data from InMemoryView."""
        view_class = self._create_test_view()

        view_class.seed_data([{"key": "test", "value": "value"}])
        assert len(view_class._data) == 1

        view_class.clear_data()
        assert len(view_class._data) == 0

    @pytest.mark.asyncio
    async def test_get_list(self) -> None:
        """Test get_list returns paginated items."""
        view_class = self._create_test_view()

        view_class.seed_data(
            [
                {"key": "a", "value": "1"},
                {"key": "b", "value": "2"},
                {"key": "c", "value": "3"},
            ]
        )

        view = view_class()
        result = await view.get_list(page=1, page_size=2)

        assert result.total == 3
        assert len(result.items) == 2
        assert result.page == 1
        assert result.page_size == 2
        assert result.has_next is True
        assert result.has_prev is False

    @pytest.mark.asyncio
    async def test_get_list_pagination(self) -> None:
        """Test get_list pagination."""
        view_class = self._create_test_view()

        view_class.seed_data([{"key": str(i), "value": f"value{i}"} for i in range(10)])

        view = view_class()

        # Page 1
        result = await view.get_list(page=1, page_size=3)
        assert len(result.items) == 3
        assert result.has_next is True
        assert result.has_prev is False

        # Page 2
        result = await view.get_list(page=2, page_size=3)
        assert len(result.items) == 3
        assert result.has_next is True
        assert result.has_prev is True

        # Last page
        result = await view.get_list(page=4, page_size=3)
        assert len(result.items) == 1
        assert result.has_next is False
        assert result.has_prev is True

    @pytest.mark.asyncio
    async def test_get_list_search(self) -> None:
        """Test get_list with search filter."""
        view_class = self._create_test_view()

        view_class.seed_data(
            [
                {"key": "theme", "value": "dark"},
                {"key": "language", "value": "english"},
                {"key": "timezone", "value": "UTC"},
            ]
        )

        view = view_class()
        result = await view.get_list(search="time")

        assert result.total == 1
        assert result.items[0]["key"] == "timezone"

    @pytest.mark.asyncio
    async def test_get_list_sorting(self) -> None:
        """Test get_list with sorting."""
        view_class = self._create_test_view()

        view_class.seed_data(
            [
                {"key": "c", "value": "3"},
                {"key": "a", "value": "1"},
                {"key": "b", "value": "2"},
            ]
        )

        view = view_class()

        # Sort ascending
        result = await view.get_list(sort_by="key", sort_order="asc")
        keys = [item["key"] for item in result.items]
        assert keys == ["a", "b", "c"]

        # Sort descending
        result = await view.get_list(sort_by="key", sort_order="desc")
        keys = [item["key"] for item in result.items]
        assert keys == ["c", "b", "a"]

    @pytest.mark.asyncio
    async def test_get_list_filters(self) -> None:
        """Test get_list with filters."""
        view_class = self._create_test_view()

        view_class.seed_data(
            [
                {"key": "a", "value": "active"},
                {"key": "b", "value": "inactive"},
                {"key": "c", "value": "active"},
            ]
        )

        view = view_class()
        result = await view.get_list(filters={"value": "active"})

        assert result.total == 2
        assert all(item["value"] == "active" for item in result.items)

    @pytest.mark.asyncio
    async def test_get_one(self) -> None:
        """Test get_one retrieves single item."""
        view_class = self._create_test_view()

        view_class.seed_data([{"key": "test_key", "value": "test_value"}])

        view = view_class()
        item = await view.get_one("test_key")

        assert item is not None
        assert item["key"] == "test_key"
        assert item["value"] == "test_value"

    @pytest.mark.asyncio
    async def test_get_one_not_found(self) -> None:
        """Test get_one returns None for non-existent item."""
        view_class = self._create_test_view()
        view_class.clear_data()

        view = view_class()
        item = await view.get_one("nonexistent")

        assert item is None

    @pytest.mark.asyncio
    async def test_create(self) -> None:
        """Test create adds new item."""
        view_class = self._create_test_view()
        view_class.clear_data()

        view = view_class()
        created = await view.create({"key": "new_key", "value": "new_value"})

        assert created["key"] == "new_key"
        assert created["value"] == "new_value"
        assert "new_key" in view_class._data

    @pytest.mark.asyncio
    async def test_create_auto_generate_pk(self) -> None:
        """Test create auto-generates primary key when not provided."""

        class AutoPkView(InMemoryView):
            name = "Auto PK"
            pk_field = "id"
            auto_generate_pk = True
            columns = [ColumnDefinition(name="id"), ColumnDefinition(name="name")]
            _data: dict[str, dict[str, Any]] = {}

        view = AutoPkView()
        created = await view.create({"name": "Test"})

        assert "id" in created
        assert created["id"] is not None
        assert len(created["id"]) == 36  # UUID length

    @pytest.mark.asyncio
    async def test_create_duplicate_pk_raises(self) -> None:
        """Test create raises error for duplicate primary key."""
        view_class = self._create_test_view()

        view_class.seed_data([{"key": "existing", "value": "value"}])

        view = view_class()
        with pytest.raises(ValueError, match="already exists"):
            await view.create({"key": "existing", "value": "new_value"})

    @pytest.mark.asyncio
    async def test_update(self) -> None:
        """Test update modifies existing item."""
        view_class = self._create_test_view()

        view_class.seed_data([{"key": "update_key", "value": "old_value"}])

        view = view_class()
        updated = await view.update("update_key", {"value": "new_value"})

        assert updated["key"] == "update_key"
        assert updated["value"] == "new_value"

    @pytest.mark.asyncio
    async def test_update_not_found_raises(self) -> None:
        """Test update raises error for non-existent item."""
        view_class = self._create_test_view()
        view_class.clear_data()

        view = view_class()
        with pytest.raises(KeyError, match="not found"):
            await view.update("nonexistent", {"value": "test"})

    @pytest.mark.asyncio
    async def test_delete(self) -> None:
        """Test delete removes item."""
        view_class = self._create_test_view()

        view_class.seed_data([{"key": "delete_key", "value": "value"}])

        view = view_class()
        result = await view.delete("delete_key")

        assert result is True
        assert "delete_key" not in view_class._data

    @pytest.mark.asyncio
    async def test_delete_not_found_raises(self) -> None:
        """Test delete raises error for non-existent item."""
        view_class = self._create_test_view()
        view_class.clear_data()

        view = view_class()
        with pytest.raises(KeyError, match="not found"):
            await view.delete("nonexistent")

    @pytest.mark.asyncio
    async def test_crud_lifecycle(self) -> None:
        """Test complete CRUD lifecycle."""
        view_class = self._create_test_view()
        view_class.clear_data()

        view = view_class()

        # Create
        created = await view.create({"key": "lifecycle", "value": "created"})
        assert created["value"] == "created"

        # Read
        item = await view.get_one("lifecycle")
        assert item is not None
        assert item["value"] == "created"

        # Update
        updated = await view.update("lifecycle", {"value": "updated"})
        assert updated["value"] == "updated"

        # Verify update
        item = await view.get_one("lifecycle")
        assert item["value"] == "updated"

        # Delete
        result = await view.delete("lifecycle")
        assert result is True

        # Verify delete
        item = await view.get_one("lifecycle")
        assert item is None


# ==============================================================================
# ViewRegistry Tests with Custom Views
# ==============================================================================


class TestViewRegistryWithCustomViews:
    """Tests for ViewRegistry with custom view types."""

    def test_register_custom_view(self, view_registry: ViewRegistry) -> None:
        """Test registering a CustomView."""

        class TestCustomDataView(CustomView):
            name = "Test Custom Data"
            identity = "test-custom-data"
            columns = [ColumnDefinition(name="id")]

            async def get_list(self, **kwargs: Any) -> ListResult:
                return ListResult()

            async def get_one(self, item_id: str) -> dict[str, Any] | None:
                return None

        view_registry.register(TestCustomDataView)

        assert view_registry.has_view("test-custom-data")
        assert len(view_registry.list_custom_views()) == 1

    def test_register_action_view(self, view_registry: ViewRegistry) -> None:
        """Test registering an ActionView."""

        class TestAction(ActionView):
            name = "Test Action"

            async def execute(self, data: dict[str, Any]) -> ActionResult:
                return ActionResult(success=True, message="Done")

        view_registry.register(TestAction)

        assert view_registry.has_view("test-action")
        assert len(view_registry.list_action_views()) == 1

    def test_register_page_view(self, view_registry: ViewRegistry) -> None:
        """Test registering a PageView."""

        class TestPage(PageView):
            name = "Test Page"
            content = "Hello World"

        view_registry.register(TestPage)

        assert view_registry.has_view("test-page")
        assert len(view_registry.list_page_views()) == 1

    def test_register_link_view(self, view_registry: ViewRegistry) -> None:
        """Test registering a LinkView."""

        class TestLink(LinkView):
            name = "Test Link"
            url = "https://example.com"

        view_registry.register(TestLink)

        assert view_registry.has_view("test-link")
        assert len(view_registry.list_link_views()) == 1

    def test_register_embed_view(self, view_registry: ViewRegistry) -> None:
        """Test registering an EmbedView."""

        class TestEmbed(EmbedView):
            name = "Test Embed"
            embed_type = "iframe"
            embed_url = "https://example.com"

        view_registry.register(TestEmbed)

        assert view_registry.has_view("test-embed")
        assert len(view_registry.list_embed_views()) == 1

    def test_get_navigation_with_mixed_views(self, view_registry: ViewRegistry) -> None:
        """Test navigation includes all view types."""

        class DataView(CustomView):
            name = "Data"
            category = "Data"
            columns = [ColumnDefinition(name="id")]

            async def get_list(self, **kwargs: Any) -> ListResult:
                return ListResult()

            async def get_one(self, item_id: str) -> dict[str, Any] | None:
                return None

        class MaintenanceAction(ActionView):
            name = "Maintenance"
            category = "Admin"

            async def execute(self, data: dict[str, Any]) -> ActionResult:
                return ActionResult(success=True, message="Done")

        class HelpPage(PageView):
            name = "Help"

        class DocsLink(LinkView):
            name = "Docs"
            url = "https://docs.example.com"
            category = "External"

        view_registry.register(DataView)
        view_registry.register(MaintenanceAction)
        view_registry.register(HelpPage)
        view_registry.register(DocsLink)

        nav = view_registry.get_navigation()

        assert "Data" in nav
        assert "Admin" in nav
        assert "default" in nav
        assert "External" in nav

        # Check view types in navigation
        data_items = nav["Data"]
        assert any(item["view_type"] == "custom" for item in data_items)

        admin_items = nav["Admin"]
        assert any(item["view_type"] == "action" for item in admin_items)

        external_items = nav["External"]
        assert any(item["view_type"] == "link" for item in external_items)

    def test_list_views_returns_all_types(self, view_registry: ViewRegistry) -> None:
        """Test list_views returns all registered view types."""

        class TestCustom(CustomView):
            name = "Custom"
            columns = [ColumnDefinition(name="id")]

            async def get_list(self, **kwargs: Any) -> ListResult:
                return ListResult()

            async def get_one(self, item_id: str) -> dict[str, Any] | None:
                return None

        class TestAction(ActionView):
            name = "Action"

            async def execute(self, data: dict[str, Any]) -> ActionResult:
                return ActionResult(success=True, message="Done")

        view_registry.register(TestCustom)
        view_registry.register(TestAction)

        all_views = view_registry.list_views()
        assert len(all_views) == 2

        view_types = {v.view_type for v in all_views}
        assert "custom" in view_types
        assert "action" in view_types
