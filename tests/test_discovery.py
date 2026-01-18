"""Tests for auto-discovery functionality."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from litestar_admin.discovery import (
    create_default_view,
    discover_models,
    is_advanced_alchemy_model,
)
from litestar_admin.views import BaseModelView

if TYPE_CHECKING:
    pass


# ==============================================================================
# Test Models for Discovery
# ==============================================================================


class DiscoveryBase(DeclarativeBase):
    """Base class for discovery test models."""


class DiscoveredUser(DiscoveryBase):
    """A user model for discovery testing."""

    __tablename__ = "discovered_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=True)


class DiscoveredPost(DiscoveryBase):
    """A post model for discovery testing."""

    __tablename__ = "discovered_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=True)


class AbstractModel(DiscoveryBase):
    """An abstract model that should be skipped."""

    __abstract__ = True


# Model with timestamp columns (simulating Advanced-Alchemy patterns)
class TimestampedModel(DiscoveryBase):
    """A model with timestamp columns."""

    __tablename__ = "timestamped_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# ==============================================================================
# Tests for discover_models
# ==============================================================================


class TestDiscoverModels:
    """Tests for the discover_models function."""

    def test_discover_models_from_base(self) -> None:
        """Test discovering models from a DeclarativeBase."""
        models = discover_models([DiscoveryBase])

        # Should discover all non-abstract models
        model_names = {m.__name__ for m in models}
        assert "DiscoveredUser" in model_names
        assert "DiscoveredPost" in model_names
        assert "TimestampedModel" in model_names

    def test_discover_models_excludes_abstract(self) -> None:
        """Test that abstract models are not discovered."""
        models = discover_models([DiscoveryBase])

        model_names = {m.__name__ for m in models}
        assert "AbstractModel" not in model_names

    def test_discover_models_with_exclusions(self) -> None:
        """Test discovering models with exclusions."""
        models = discover_models(
            [DiscoveryBase],
            exclude_models={DiscoveredUser},
        )

        model_names = {m.__name__ for m in models}
        assert "DiscoveredUser" not in model_names
        assert "DiscoveredPost" in model_names

    def test_discover_models_empty_bases(self) -> None:
        """Test with no bases provided."""
        models = discover_models([])
        assert models == []

    def test_discover_models_no_duplicates(self) -> None:
        """Test that models are not duplicated when passing same base twice."""
        models = discover_models([DiscoveryBase, DiscoveryBase])

        # Count occurrences of each model
        model_names = [m.__name__ for m in models]
        assert model_names.count("DiscoveredUser") == 1
        assert model_names.count("DiscoveredPost") == 1


# ==============================================================================
# Tests for create_default_view
# ==============================================================================


class TestCreateDefaultView:
    """Tests for the create_default_view function."""

    def test_creates_view_class(self) -> None:
        """Test that a view class is created correctly."""
        view_class = create_default_view(DiscoveredUser)

        assert issubclass(view_class, BaseModelView)
        assert view_class.model is DiscoveredUser
        assert view_class.name == "DiscoveredUser"
        assert view_class.name_plural == "DiscoveredUsers"

    def test_auto_detects_columns(self) -> None:
        """Test that columns are auto-detected."""
        view_class = create_default_view(DiscoveredUser, auto_columns=True)

        assert "id" in view_class.column_list
        assert "email" in view_class.column_list
        assert "name" in view_class.column_list

    def test_auto_detects_searchable_columns(self) -> None:
        """Test that string columns are marked as searchable."""
        view_class = create_default_view(DiscoveredUser, auto_columns=True)

        # String columns should be searchable
        assert "email" in view_class.column_searchable_list
        assert "name" in view_class.column_searchable_list
        # Integer columns should not be searchable
        assert "id" not in view_class.column_searchable_list

    def test_auto_detects_sortable_columns(self) -> None:
        """Test that all columns are marked as sortable."""
        view_class = create_default_view(DiscoveredUser, auto_columns=True)

        # All columns should be sortable
        assert "id" in view_class.column_sortable_list
        assert "email" in view_class.column_sortable_list
        assert "name" in view_class.column_sortable_list

    def test_excludes_auto_pk_from_forms(self) -> None:
        """Test that auto-increment primary keys are excluded from forms."""
        view_class = create_default_view(DiscoveredUser, auto_columns=True)

        assert "id" in view_class.form_excluded_columns

    def test_excludes_timestamps_from_forms(self) -> None:
        """Test that timestamp columns with defaults are excluded from forms."""
        view_class = create_default_view(TimestampedModel, auto_columns=True)

        assert "created_at" in view_class.form_excluded_columns
        assert "updated_at" in view_class.form_excluded_columns

    def test_sets_default_sort(self) -> None:
        """Test that default sort is set correctly."""
        view_class = create_default_view(DiscoveredUser, auto_columns=True)

        assert view_class.column_default_sort == ("id", "desc")

    def test_creates_view_without_auto_columns(self) -> None:
        """Test creating a view without auto column detection."""
        view_class = create_default_view(DiscoveredUser, auto_columns=False)

        assert view_class.model is DiscoveredUser
        # Should use defaults from BaseModelView
        assert view_class.column_list == []

    def test_view_class_name_format(self) -> None:
        """Test that the generated class name follows the expected format."""
        view_class = create_default_view(DiscoveredUser)

        assert view_class.__name__ == "DiscoveredUserAdmin"


# ==============================================================================
# Tests for is_advanced_alchemy_model
# ==============================================================================


class TestIsAdvancedAlchemyModel:
    """Tests for the is_advanced_alchemy_model function."""

    def test_regular_model_is_not_aa(self) -> None:
        """Test that a regular SQLAlchemy model is not detected as AA."""
        result = is_advanced_alchemy_model(DiscoveredUser)
        assert result is False

    def test_model_with_timestamps_but_no_uuid(self) -> None:
        """Test that timestamp columns alone don't make it an AA model."""
        result = is_advanced_alchemy_model(TimestampedModel)
        # Has created_at/updated_at but id is not UUID, so should be False
        assert result is False

    def test_model_with_aa_mixin_name(self) -> None:
        """Test detection when model has AA mixin in MRO."""
        # Create a mock class with AA mixin (without SQLAlchemy inheritance
        # to avoid needing full model setup)
        mock_mixin = type("CommonTableAttributes", (), {})
        mock_model = type(
            "MockAAModel",
            (mock_mixin,),
            {"__tablename__": "mock_aa_models"},
        )

        # Test the MRO check for AA mixin names
        result = is_advanced_alchemy_model(mock_model)
        assert result is True

    def test_model_with_other_aa_mixin_names(self) -> None:
        """Test detection for other AA mixin names."""
        for mixin_name in ("UUIDPrimaryKey", "BigIntPrimaryKey", "AuditColumns", "SlugKey"):
            mock_mixin = type(mixin_name, (), {})
            mock_model = type(
                f"Mock{mixin_name}Model",
                (mock_mixin,),
                {},
            )
            result = is_advanced_alchemy_model(mock_model)
            assert result is True, f"Failed to detect {mixin_name}"


# ==============================================================================
# Integration Tests for Auto-Discovery
# ==============================================================================


class TestAutoDiscoveryIntegration:
    """Integration tests for auto-discovery with the plugin."""

    def test_discovered_view_is_valid(self) -> None:
        """Test that discovered views can be used like manually created ones."""
        view_class = create_default_view(DiscoveredUser)

        # Should be able to call view methods
        columns = view_class.get_list_columns()
        assert len(columns) > 0

    def test_discovered_view_form_columns(self) -> None:
        """Test that form columns work correctly for discovered views."""
        view_class = create_default_view(DiscoveredUser)

        # Should work for create (excludes auto-increment PK)
        create_columns = view_class.get_form_columns(is_create=True)
        assert "id" not in create_columns
        assert "email" in create_columns

        # Should work for edit (may include PK)
        edit_columns = view_class.get_form_columns(is_create=False)
        assert "email" in edit_columns

    def test_discovered_view_column_info(self) -> None:
        """Test that column info is available for discovered views."""
        view_class = create_default_view(DiscoveredUser)

        info = view_class.get_column_info("email")
        assert info["name"] == "email"
        assert info["sortable"] is True
        assert info["searchable"] is True

    def test_multiple_models_discovery(self) -> None:
        """Test discovering multiple models and creating views for all."""
        models = discover_models([DiscoveryBase])
        views = [create_default_view(m) for m in models]

        # All views should be valid
        for view in views:
            assert issubclass(view, BaseModelView)
            assert hasattr(view, "model")
            assert view.name != ""


# ==============================================================================
# Edge Cases
# ==============================================================================


class TestDiscoveryEdgeCases:
    """Tests for edge cases in discovery."""

    def test_model_without_table(self) -> None:
        """Test that models without __table__ are handled gracefully."""
        # Create a mock model without __table__
        mock_model = type("NoTableModel", (), {"__name__": "NoTableModel"})

        # Should not crash
        view_class = create_default_view(mock_model, auto_columns=True)
        assert view_class.column_list == []

    def test_discovery_with_none_exclude(self) -> None:
        """Test that None exclude_models is handled."""
        models = discover_models([DiscoveryBase], exclude_models=None)
        assert len(models) > 0

    def test_base_without_registry(self) -> None:
        """Test handling of a base without a registry."""
        # Create a mock base without _sa_registry
        mock_base = MagicMock(spec=[])
        mock_base.__name__ = "MockBase"

        # Should return empty list without error
        models = discover_models([mock_base])
        assert models == []
