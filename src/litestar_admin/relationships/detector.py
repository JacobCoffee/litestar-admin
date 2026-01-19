"""Relationship detection logic for SQLAlchemy models."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sqlalchemy import inspect as sa_inspect

from litestar_admin.relationships.types import RelationshipInfo, RelationshipType

if TYPE_CHECKING:
    from sqlalchemy.orm import Mapper, RelationshipProperty

__all__ = ["RelationshipDetector", "get_relationship_detector"]

# Common display column names in order of preference
_DISPLAY_COLUMN_CANDIDATES = [
    "name",
    "title",
    "label",
    "display_name",
    "full_name",
    "username",
    "email",
    "slug",
    "code",
    "__str__",
]

_logger = logging.getLogger(__name__)


class RelationshipDetector:
    """Detects and analyzes SQLAlchemy model relationships.

    This class inspects SQLAlchemy ORM models to extract relationship metadata
    that can be used for admin form rendering and data display.

    Example::

        from myapp.models import User
        from litestar_admin.relationships import RelationshipDetector

        detector = RelationshipDetector()
        relationships = detector.detect_relationships(User)
        for rel in relationships:
            print(f"{rel.name}: {rel.relationship_type.value} -> {rel.related_model_name}")
    """

    def __init__(self) -> None:
        """Initialize the relationship detector."""
        # Cache for detected relationships per model
        self._cache: dict[type[Any], list[RelationshipInfo]] = {}
        # Cache for display columns
        self._display_column_cache: dict[type[Any], str] = {}

    def detect_relationships(self, model: type[Any]) -> list[RelationshipInfo]:
        """Detect all relationships on a SQLAlchemy model.

        Args:
            model: The SQLAlchemy model class to inspect.

        Returns:
            List of RelationshipInfo objects describing each relationship.
        """
        # Return cached result if available
        if model in self._cache:
            return self._cache[model]

        relationships: list[RelationshipInfo] = []

        try:
            mapper: Mapper[Any] = sa_inspect(model)
        except Exception:
            # Model might not be properly configured
            return relationships

        # Iterate through all relationships defined on the mapper
        for rel_prop in mapper.relationships:
            rel_info = self._analyze_relationship(model, rel_prop)
            if rel_info is not None:
                relationships.append(rel_info)

        # Cache the result
        self._cache[model] = relationships
        return relationships

    def _analyze_relationship(
        self,
        model: type[Any],
        rel_prop: RelationshipProperty[Any],
    ) -> RelationshipInfo | None:
        """Analyze a single relationship property.

        Args:
            model: The source model class.
            rel_prop: The SQLAlchemy relationship property.

        Returns:
            RelationshipInfo if analysis succeeds, None otherwise.
        """
        try:
            # Get the related model class
            related_model = rel_prop.mapper.class_

            # Determine relationship type
            relationship_type = self._determine_relationship_type(rel_prop)

            # Extract foreign key information
            foreign_key_column = self._get_foreign_key_column_for_relationship(model, rel_prop)

            # Get local and remote columns
            local_columns, remote_columns = self._get_join_columns(rel_prop)

            # Check if nullable (for MANY_TO_ONE relationships)
            nullable = self._is_relationship_nullable(model, foreign_key_column)

            # Get secondary table for MANY_TO_MANY
            secondary_table = None
            if rel_prop.secondary is not None:
                secondary_table = rel_prop.secondary.name

            return RelationshipInfo(
                name=rel_prop.key,
                related_model=related_model,
                relationship_type=relationship_type,
                foreign_key_column=foreign_key_column,
                back_populates=rel_prop.back_populates,
                nullable=nullable,
                uselist=rel_prop.uselist or False,
                local_columns=local_columns,
                remote_columns=remote_columns,
                secondary_table=secondary_table,
            )
        except Exception:
            # Skip relationships that can't be analyzed
            return None

    def _determine_relationship_type(
        self,
        rel_prop: RelationshipProperty[Any],
    ) -> RelationshipType:
        """Determine the type of a relationship.

        Args:
            rel_prop: The SQLAlchemy relationship property.

        Returns:
            The determined RelationshipType.
        """
        # Many-to-many: has a secondary association table
        if rel_prop.secondary is not None:
            return RelationshipType.MANY_TO_MANY

        # Check uselist to distinguish to-one vs to-many
        if rel_prop.uselist:
            # This is a to-many relationship
            return RelationshipType.ONE_TO_MANY
        # This is a to-one relationship
        # Check if it's truly one-to-one or many-to-one
        # by examining the direction and foreign keys
        local_columns = [lc.name for lc in rel_prop.local_columns]
        if local_columns:
            # Foreign key is on this side, so it's MANY_TO_ONE
            return RelationshipType.MANY_TO_ONE
        # Foreign key is on the other side with uselist=False
        return RelationshipType.ONE_TO_ONE

    def _get_foreign_key_column_for_relationship(
        self,
        model: type[Any],
        rel_prop: RelationshipProperty[Any],
    ) -> str | None:
        """Get the foreign key column name for a relationship.

        Args:
            model: The source model class.
            rel_prop: The SQLAlchemy relationship property.

        Returns:
            The foreign key column name if found, None otherwise.
        """
        # Get local columns from the relationship
        local_columns = list(rel_prop.local_columns)

        if local_columns:
            # Return the first local column (most relationships have one FK)
            return local_columns[0].name

        # For relationships defined the other way, check synchronize_pairs
        if rel_prop.synchronize_pairs:
            for local_col, _ in rel_prop.synchronize_pairs:
                # Check if this column belongs to our model
                if hasattr(model, local_col.name):
                    return local_col.name

        return None

    def _get_join_columns(
        self,
        rel_prop: RelationshipProperty[Any],
    ) -> tuple[list[str], list[str]]:
        """Get the local and remote column names involved in a relationship.

        Args:
            rel_prop: The SQLAlchemy relationship property.

        Returns:
            Tuple of (local_columns, remote_columns) as lists of column names.
        """
        local_cols: list[str] = []
        remote_cols: list[str] = []

        # Get from local_columns and remote_side
        for col in rel_prop.local_columns:
            local_cols.append(col.name)

        for col in rel_prop.remote_side:
            remote_cols.append(col.name)

        return local_cols, remote_cols

    def _is_relationship_nullable(
        self,
        model: type[Any],
        foreign_key_column: str | None,
    ) -> bool:
        """Check if a relationship is nullable based on its foreign key.

        Args:
            model: The source model class.
            foreign_key_column: The foreign key column name.

        Returns:
            True if the relationship is nullable, False otherwise.
        """
        if foreign_key_column is None:
            # No FK on this side means it's likely nullable (reverse relationship)
            return True

        try:
            mapper = sa_inspect(model)
            for column in mapper.columns:
                if column.name == foreign_key_column:
                    return column.nullable or False
        except Exception as exc:
            _logger.debug("Failed to check nullable for %s.%s: %s", model, foreign_key_column, exc)

        return True

    def get_foreign_key_column(
        self,
        model: type[Any],
        relationship_name: str,
    ) -> str | None:
        """Get the foreign key column for a specific relationship.

        Args:
            model: The model class.
            relationship_name: The name of the relationship attribute.

        Returns:
            The foreign key column name if found, None otherwise.
        """
        relationships = self.detect_relationships(model)
        for rel in relationships:
            if rel.name == relationship_name:
                return rel.foreign_key_column
        return None

    def get_related_model(
        self,
        model: type[Any],
        relationship_name: str,
    ) -> type[Any] | None:
        """Get the related model class for a specific relationship.

        Args:
            model: The model class.
            relationship_name: The name of the relationship attribute.

        Returns:
            The related model class if found, None otherwise.
        """
        relationships = self.detect_relationships(model)
        for rel in relationships:
            if rel.name == relationship_name:
                return rel.related_model
        return None

    def get_relationship_info(
        self,
        model: type[Any],
        relationship_name: str,
    ) -> RelationshipInfo | None:
        """Get relationship info for a specific relationship.

        Args:
            model: The model class.
            relationship_name: The name of the relationship attribute.

        Returns:
            RelationshipInfo if found, None otherwise.
        """
        relationships = self.detect_relationships(model)
        for rel in relationships:
            if rel.name == relationship_name:
                return rel
        return None

    def get_display_column(self, model: type[Any]) -> str:
        """Determine the best column to use for displaying records of a model.

        This is useful for showing related records in dropdowns or display fields.
        The method tries common naming patterns and falls back to the primary key.

        Args:
            model: The model class.

        Returns:
            The column name to use for display purposes.
        """
        # Check cache first
        if model in self._display_column_cache:
            return self._display_column_cache[model]

        result = self._compute_display_column(model)
        self._display_column_cache[model] = result
        return result

    def _compute_display_column(self, model: type[Any]) -> str:
        """Compute the display column for a model (uncached).

        Args:
            model: The model class.

        Returns:
            The column name to use for display purposes.
        """
        try:
            mapper = sa_inspect(model)
            column_names = {c.name for c in mapper.columns}

            # Check for common display column names
            for candidate in _DISPLAY_COLUMN_CANDIDATES:
                if candidate in column_names:
                    return candidate

            # Check if model has __str__ method that might use a specific column
            # (we can't introspect this, so skip)

            # Fall back to primary key
            pk_columns = mapper.primary_key
            if pk_columns:
                return pk_columns[0].name

        except Exception as exc:
            _logger.debug("Failed to compute display column for %s: %s", model, exc)

        # Last resort fallback
        return "id"

    def clear_cache(self) -> None:
        """Clear the relationship detection cache.

        Call this if models have been modified and need re-analysis.
        """
        self._cache.clear()
        self._display_column_cache.clear()

    def is_relationship(self, model: type[Any], field_name: str) -> bool:
        """Check if a field is a relationship.

        Args:
            model: The model class.
            field_name: The field name to check.

        Returns:
            True if the field is a relationship, False otherwise.
        """
        try:
            mapper = sa_inspect(model)
            return field_name in mapper.relationships
        except Exception:
            return False

    def get_relationship_names(self, model: type[Any]) -> list[str]:
        """Get all relationship names for a model.

        Args:
            model: The model class.

        Returns:
            List of relationship attribute names.
        """
        relationships = self.detect_relationships(model)
        return [rel.name for rel in relationships]


class _DetectorHolder:
    """Holds the singleton RelationshipDetector instance."""

    instance: RelationshipDetector | None = None


def get_relationship_detector() -> RelationshipDetector:
    """Get the default RelationshipDetector instance.

    Returns:
        The global RelationshipDetector singleton.
    """
    if _DetectorHolder.instance is None:
        _DetectorHolder.instance = RelationshipDetector()
    return _DetectorHolder.instance
