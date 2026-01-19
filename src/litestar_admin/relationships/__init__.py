"""Relationship detection for SQLAlchemy models.

This module provides utilities for detecting and analyzing SQLAlchemy
ORM relationships to support admin form rendering and data display.

Example::

    from litestar_admin.relationships import RelationshipDetector, RelationshipType

    detector = RelationshipDetector()
    for rel in detector.detect_relationships(User):
        if rel.relationship_type == RelationshipType.MANY_TO_ONE:
            print(f"Foreign key field: {rel.foreign_key_column}")
"""

from __future__ import annotations

from litestar_admin.relationships.detector import (
    RelationshipDetector,
    get_relationship_detector,
)
from litestar_admin.relationships.types import (
    RelationshipInfo,
    RelationshipType,
)

__all__ = [
    "RelationshipDetector",
    "RelationshipInfo",
    "RelationshipType",
    "get_relationship_detector",
]
