"""Type definitions for SQLAlchemy relationship detection."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

__all__ = [
    "RelationshipInfo",
    "RelationshipType",
]


class RelationshipType(Enum):
    """Enumeration of SQLAlchemy relationship types.

    Attributes:
        MANY_TO_ONE: Foreign key on this model pointing to another (e.g., Post.author_id -> User).
        ONE_TO_MANY: Foreign key on related model pointing to this one (e.g., User.posts).
        MANY_TO_MANY: Association table linking two models (e.g., User.roles via user_roles table).
        ONE_TO_ONE: Single reference with uselist=False (e.g., User.profile).
    """

    MANY_TO_ONE = "many_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_MANY = "many_to_many"
    ONE_TO_ONE = "one_to_one"


@dataclass
class RelationshipInfo:
    """Information about a detected SQLAlchemy relationship.

    This dataclass captures all relevant metadata about a relationship
    for use in admin forms and display logic.

    Attributes:
        name: The relationship attribute name on the model.
        related_model: The target model class of the relationship.
        relationship_type: The type of relationship (MANY_TO_ONE, ONE_TO_MANY, etc.).
        foreign_key_column: The foreign key column name if applicable (for MANY_TO_ONE).
        back_populates: The back-reference name on the related model, if defined.
        nullable: Whether the relationship is optional (for MANY_TO_ONE via FK nullable).
        uselist: True for to-many relationships, False for to-one.
        related_model_name: String name of the related model class.
        local_columns: List of local column names involved in the relationship.
        remote_columns: List of remote column names involved in the relationship.
        secondary_table: Name of the association table for MANY_TO_MANY relationships.

    Example::

        info = RelationshipInfo(
            name="author",
            related_model=User,
            relationship_type=RelationshipType.MANY_TO_ONE,
            foreign_key_column="author_id",
            back_populates="posts",
            nullable=True,
            uselist=False,
        )
    """

    name: str
    related_model: type[Any]
    relationship_type: RelationshipType
    foreign_key_column: str | None = None
    back_populates: str | None = None
    nullable: bool = True
    uselist: bool = False
    related_model_name: str = ""
    local_columns: list[str] = field(default_factory=list)
    remote_columns: list[str] = field(default_factory=list)
    secondary_table: str | None = None

    def __post_init__(self) -> None:
        """Set derived fields after initialization."""
        if not self.related_model_name:
            self.related_model_name = self.related_model.__name__

    @property
    def is_to_many(self) -> bool:
        """Check if this is a to-many relationship.

        Returns:
            True if this relationship returns multiple related objects.
        """
        return self.uselist

    @property
    def is_to_one(self) -> bool:
        """Check if this is a to-one relationship.

        Returns:
            True if this relationship returns a single related object.
        """
        return not self.uselist

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation for JSON serialization.

        Returns:
            Dictionary containing relationship metadata.
        """
        return {
            "name": self.name,
            "related_model_name": self.related_model_name,
            "relationship_type": self.relationship_type.value,
            "foreign_key_column": self.foreign_key_column,
            "back_populates": self.back_populates,
            "nullable": self.nullable,
            "uselist": self.uselist,
            "local_columns": self.local_columns,
            "remote_columns": self.remote_columns,
            "secondary_table": self.secondary_table,
        }
