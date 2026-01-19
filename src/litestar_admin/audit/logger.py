"""Audit logging system for admin actions.

This module provides comprehensive audit logging capabilities for the admin panel,
including action tracking, change detection, and flexible storage backends.

Example:
    Basic usage with the InMemoryAuditLogger::

        from litestar_admin.audit import AuditLogger, InMemoryAuditLogger, AuditAction

        logger = InMemoryAuditLogger()
        entry = await audit_admin_action(
            connection=conn,
            action=AuditAction.CREATE,
            model_name="User",
            record_id=1,
        )
        await logger.log(entry)

    Query audit entries::

        from litestar_admin.audit import AuditQueryFilters

        filters = AuditQueryFilters(
            model_name="User",
            action=AuditAction.UPDATE,
        )
        entries = await logger.query(filters)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from litestar.connection import ASGIConnection

__all__ = [
    "AuditAction",
    "AuditEntry",
    "AuditLogger",
    "AuditQueryFilters",
    "InMemoryAuditLogger",
    "audit_admin_action",
    "calculate_changes",
    "extract_actor_info",
]


class AuditAction(str, Enum):
    """Enumeration of auditable admin actions.

    Actions follow a consistent naming pattern for clarity and consistency
    in audit logs.

    Attributes:
        CREATE: A new record was created.
        READ: A record was viewed/accessed.
        UPDATE: A record was modified.
        DELETE: A record was deleted.
        EXPORT: Data was exported.
        LOGIN: A user logged into the admin panel.
        LOGOUT: A user logged out of the admin panel.
        BULK_DELETE: Multiple records were deleted at once.
        BULK_ACTION: A bulk operation was performed on multiple records.
    """

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXPORT = "export"
    LOGIN = "login"
    LOGOUT = "logout"
    BULK_DELETE = "bulk_delete"
    BULK_ACTION = "bulk_action"


@dataclass
class AuditEntry:
    """Represents a single audit log entry.

    Captures comprehensive information about an admin action including
    who performed it, what was affected, and any changes made.

    Attributes:
        id: Unique identifier for the audit entry (UUID).
        timestamp: When the action occurred.
        action: The type of action performed.
        actor_id: ID of the user who performed the action (if known).
        actor_email: Email of the user who performed the action (if known).
        model_name: Name of the affected model (for CRUD operations).
        record_id: ID of the affected record (for single-record operations).
        changes: Dictionary of field changes for UPDATE actions.
        metadata: Additional context about the action.
        ip_address: IP address of the request origin.
        user_agent: User agent string of the client.

    Example:
        Create an audit entry manually::

            entry = AuditEntry(
                action=AuditAction.UPDATE,
                actor_id=1,
                actor_email="admin@example.com",
                model_name="User",
                record_id=42,
                changes={"email": {"old": "old@example.com", "new": "new@example.com"}},
            )
    """

    action: AuditAction
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    actor_id: str | int | None = None
    actor_email: str | None = None
    model_name: str | None = None
    record_id: str | int | None = None
    changes: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    ip_address: str | None = None
    user_agent: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert the audit entry to a dictionary.

        Returns:
            Dictionary representation of the audit entry with all fields.
        """
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "action": self.action.value,
            "actor_id": self.actor_id,
            "actor_email": self.actor_email,
            "model_name": self.model_name,
            "record_id": self.record_id,
            "changes": self.changes,
            "metadata": self.metadata,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
        }


@dataclass
class AuditQueryFilters:
    """Filters for querying audit log entries.

    Provides flexible filtering options for retrieving audit entries
    based on various criteria.

    Attributes:
        action: Filter by specific action type.
        actor_id: Filter by actor ID.
        actor_email: Filter by actor email (partial match).
        model_name: Filter by model name.
        record_id: Filter by record ID.
        start_date: Filter entries on or after this timestamp.
        end_date: Filter entries on or before this timestamp.
        ip_address: Filter by IP address.
        limit: Maximum number of entries to return.
        offset: Number of entries to skip (for pagination).

    Example:
        Query recent updates to User records::

            filters = AuditQueryFilters(
                model_name="User",
                action=AuditAction.UPDATE,
                start_date=datetime.now(tz=timezone.utc) - timedelta(days=7),
                limit=100,
            )
    """

    action: AuditAction | None = None
    actor_id: str | int | None = None
    actor_email: str | None = None
    model_name: str | None = None
    record_id: str | int | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    ip_address: str | None = None
    limit: int = 100
    offset: int = 0


@runtime_checkable
class AuditLogger(Protocol):
    """Protocol for audit logging backends.

    Implementations of this protocol handle storing and retrieving
    audit log entries. Different backends can be used for different
    deployment scenarios (e.g., in-memory for testing, database for
    production, external service for compliance).

    Example:
        Implement a custom audit logger::

            class DatabaseAuditLogger:
                def __init__(self, session: AsyncSession) -> None:
                    self._session = session

                async def log(self, entry: AuditEntry) -> None:
                    audit_record = AuditRecord(**entry.to_dict())
                    self._session.add(audit_record)
                    await self._session.flush()

                async def query(
                    self,
                    filters: AuditQueryFilters,
                ) -> list[AuditEntry]:
                    # Build and execute query
                    ...
    """

    async def log(self, entry: AuditEntry) -> None:
        """Log an audit entry.

        Args:
            entry: The audit entry to store.
        """
        ...

    async def query(self, filters: AuditQueryFilters) -> list[AuditEntry]:
        """Query audit entries based on filters.

        Args:
            filters: The query filters to apply.

        Returns:
            List of matching audit entries, sorted by timestamp descending.
        """
        ...


class InMemoryAuditLogger:
    """In-memory implementation of AuditLogger for testing and development.

    Stores audit entries in a list in memory. Useful for testing and
    development environments where persistence is not required.

    Attributes:
        entries: List of stored audit entries.

    Example:
        Use in tests::

            logger = InMemoryAuditLogger()
            await logger.log(entry)
            entries = await logger.query(AuditQueryFilters())
            assert len(entries) == 1
    """

    __slots__ = ("_entries",)

    def __init__(self) -> None:
        """Initialize the in-memory audit logger."""
        self._entries: list[AuditEntry] = []

    @property
    def entries(self) -> list[AuditEntry]:
        """Return a copy of all stored entries.

        Returns:
            Copy of the entries list to prevent external modification.
        """
        return list(self._entries)

    async def log(self, entry: AuditEntry) -> None:
        """Log an audit entry to memory.

        Args:
            entry: The audit entry to store.
        """
        self._entries.append(entry)

    async def query(self, filters: AuditQueryFilters) -> list[AuditEntry]:
        """Query audit entries based on filters.

        Args:
            filters: The query filters to apply.

        Returns:
            List of matching audit entries, sorted by timestamp descending.
        """
        results = list(self._entries)

        # Apply filters
        if filters.action is not None:
            results = [e for e in results if e.action == filters.action]

        if filters.actor_id is not None:
            results = [e for e in results if e.actor_id == filters.actor_id]

        if filters.actor_email is not None:
            results = [
                e for e in results if e.actor_email is not None and filters.actor_email.lower() in e.actor_email.lower()
            ]

        if filters.model_name is not None:
            results = [e for e in results if e.model_name == filters.model_name]

        if filters.record_id is not None:
            results = [e for e in results if e.record_id == filters.record_id]

        if filters.start_date is not None:
            results = [e for e in results if e.timestamp >= filters.start_date]

        if filters.end_date is not None:
            results = [e for e in results if e.timestamp <= filters.end_date]

        if filters.ip_address is not None:
            results = [e for e in results if e.ip_address == filters.ip_address]

        # Sort by timestamp descending (most recent first)
        results.sort(key=lambda e: e.timestamp, reverse=True)

        # Apply pagination
        return results[filters.offset : filters.offset + filters.limit]

    def clear(self) -> None:
        """Clear all stored entries.

        Useful for test cleanup.
        """
        self._entries.clear()


def calculate_changes(
    old_data: dict[str, Any],
    new_data: dict[str, Any],
    *,
    include_unchanged: bool = False,
) -> dict[str, dict[str, Any]]:
    """Calculate the differences between old and new data dictionaries.

    Computes a diff between two dictionaries, identifying fields that
    were added, removed, or modified.

    Args:
        old_data: The original data before changes.
        new_data: The new data after changes.
        include_unchanged: If True, include fields that didn't change.

    Returns:
        Dictionary mapping field names to their old and new values.
        Each field entry contains "old" and "new" keys.

    Example:
        Calculate changes for an update::

            old = {"email": "old@example.com", "name": "John"}
            new = {"email": "new@example.com", "name": "John"}
            changes = calculate_changes(old, new)
            # Returns: {"email": {"old": "old@example.com", "new": "new@example.com"}}
    """
    changes: dict[str, dict[str, Any]] = {}

    # Get all keys from both dictionaries
    all_keys = set(old_data.keys()) | set(new_data.keys())

    for key in all_keys:
        old_value = old_data.get(key)
        new_value = new_data.get(key)

        if old_value != new_value or include_unchanged:
            changes[key] = {
                "old": old_value,
                "new": new_value,
            }

    return changes


def extract_actor_info(connection: ASGIConnection) -> tuple[str | int | None, str | None]:
    """Extract actor information from an ASGI connection.

    Retrieves the user ID and email from the connection's user object,
    if available.

    Args:
        connection: The ASGI connection containing user information.

    Returns:
        Tuple of (actor_id, actor_email). Either or both may be None
        if user information is not available.

    Example:
        Extract actor info in a controller::

            actor_id, actor_email = extract_actor_info(request)
            entry = AuditEntry(
                action=AuditAction.CREATE,
                actor_id=actor_id,
                actor_email=actor_email,
                ...
            )
    """
    user = getattr(connection, "user", None)
    if user is None:
        return None, None

    actor_id = getattr(user, "id", None)
    actor_email = getattr(user, "email", None)

    return actor_id, actor_email


def extract_request_info(connection: ASGIConnection) -> tuple[str | None, str | None]:
    """Extract request information from an ASGI connection.

    Retrieves the client IP address and user agent from the connection.

    Args:
        connection: The ASGI connection.

    Returns:
        Tuple of (ip_address, user_agent). Either may be None if
        information is not available.

    Example:
        Extract request info for audit entry::

            ip_address, user_agent = extract_request_info(request)
    """
    # Get IP address from client
    ip_address: str | None = None
    if hasattr(connection, "client") and connection.client:
        ip_address = connection.client.host if hasattr(connection.client, "host") else connection.client[0]

    # Check for X-Forwarded-For header (proxy scenarios)
    if hasattr(connection, "headers"):
        forwarded_for = connection.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in the chain (original client)
            ip_address = forwarded_for.split(",")[0].strip()

    # Get user agent
    user_agent: str | None = None
    if hasattr(connection, "headers"):
        user_agent = connection.headers.get("user-agent")

    return ip_address, user_agent


async def audit_admin_action(
    connection: ASGIConnection,
    action: AuditAction,
    model_name: str | None = None,
    record_id: str | int | None = None,
    changes: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditEntry:
    """Create an audit entry for an admin action.

    Convenience function that creates a fully populated AuditEntry by
    extracting actor and request information from the connection.

    Args:
        connection: The ASGI connection.
        action: The type of action being performed.
        model_name: Name of the affected model (for CRUD operations).
        record_id: ID of the affected record.
        changes: Dictionary of field changes (for UPDATE actions).
        metadata: Additional context about the action.

    Returns:
        A populated AuditEntry ready for logging.

    Example:
        Create and log an audit entry::

            entry = await audit_admin_action(
                connection=request,
                action=AuditAction.UPDATE,
                model_name="User",
                record_id=42,
                changes={"email": {"old": "a@b.com", "new": "c@d.com"}},
            )
            await audit_logger.log(entry)
    """
    actor_id, actor_email = extract_actor_info(connection)
    ip_address, user_agent = extract_request_info(connection)

    return AuditEntry(
        action=action,
        actor_id=actor_id,
        actor_email=actor_email,
        model_name=model_name,
        record_id=record_id,
        changes=changes,
        metadata=metadata,
        ip_address=ip_address,
        user_agent=user_agent,
    )
