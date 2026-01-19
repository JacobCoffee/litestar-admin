"""Audit logging system for admin panel actions.

This module provides comprehensive audit logging capabilities for the admin panel,
including action tracking, change detection, and flexible storage backends.

Components:
    - AuditAction: Enum of auditable actions (CREATE, READ, UPDATE, DELETE, etc.)
    - AuditEntry: Dataclass representing a single audit log entry
    - AuditLogger: Protocol for audit logging backends
    - InMemoryAuditLogger: In-memory implementation for testing
    - AuditMiddleware: Middleware for automatic request logging
    - Helper functions for creating audit entries

Example:
    Basic usage with manual logging::

        from litestar_admin.audit import (
            AuditAction,
            InMemoryAuditLogger,
            audit_admin_action,
        )

        # Create a logger (use database backend in production)
        logger = InMemoryAuditLogger()

        # In a controller, create and log an entry
        entry = await audit_admin_action(
            connection=request,
            action=AuditAction.UPDATE,
            model_name="User",
            record_id=42,
            changes={"email": {"old": "a@b.com", "new": "c@d.com"}},
        )
        await logger.log(entry)

    Using automatic middleware logging::

        from litestar import Litestar
        from litestar_admin.audit import AuditMiddleware, InMemoryAuditLogger

        logger = InMemoryAuditLogger()
        middleware = AuditMiddleware(logger)

        app = Litestar(
            route_handlers=[...],
            middleware=[middleware],
        )

    Querying audit entries::

        from litestar_admin.audit import AuditQueryFilters, AuditAction

        # Query recent user updates
        filters = AuditQueryFilters(
            model_name="User",
            action=AuditAction.UPDATE,
            limit=50,
        )
        entries = await logger.query(filters)
"""

from __future__ import annotations

from litestar_admin.audit.database import DatabaseAuditLogger
from litestar_admin.audit.logger import (
    AuditAction,
    AuditEntry,
    AuditLogger,
    AuditQueryFilters,
    InMemoryAuditLogger,
    audit_admin_action,
    calculate_changes,
    extract_actor_info,
    extract_request_info,
)
from litestar_admin.audit.middleware import (
    AuditMiddleware,
    AuditMiddlewareConfig,
)
from litestar_admin.audit.models import AuditLog, AuditLogBase

__all__ = [
    # Core types
    "AuditAction",
    "AuditEntry",
    "AuditLogger",
    "AuditQueryFilters",
    # Implementations
    "DatabaseAuditLogger",
    "InMemoryAuditLogger",
    # Models
    "AuditLog",
    "AuditLogBase",
    # Middleware
    "AuditMiddleware",
    "AuditMiddlewareConfig",
    # Helper functions
    "audit_admin_action",
    "calculate_changes",
    "extract_actor_info",
    "extract_request_info",
]
