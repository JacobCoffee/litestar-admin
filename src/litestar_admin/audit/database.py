"""Database-backed audit logger using SQLAlchemy.

This module provides a persistent audit logging implementation that stores
audit entries in a database using SQLAlchemy async sessions.

Example:
    Using DatabaseAuditLogger in your application::

        from sqlalchemy.ext.asyncio import AsyncSession
        from litestar_admin.audit import AuditAction, audit_admin_action
        from litestar_admin.audit.database import DatabaseAuditLogger


        async def log_action(session: AsyncSession, request: Request) -> None:
            logger = DatabaseAuditLogger(session)
            entry = await audit_admin_action(
                connection=request,
                action=AuditAction.CREATE,
                model_name="User",
                record_id=1,
            )
            await logger.log(entry)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from litestar_admin.audit.logger import AuditAction, AuditEntry, AuditQueryFilters
from litestar_admin.audit.models import AuditLog

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

__all__ = ["DatabaseAuditLogger"]


class DatabaseAuditLogger:
    """Database-backed implementation of AuditLogger.

    Stores audit entries in a database using SQLAlchemy async sessions.
    Designed for production use where persistent audit logs are required.

    The session is not managed by this class - it should be provided by the
    application's dependency injection system and committed as part of the
    request transaction.

    Attributes:
        session: The SQLAlchemy async session for database operations.

    Example:
        Using with Litestar dependency injection::

            from litestar import get
            from sqlalchemy.ext.asyncio import AsyncSession


            @get("/")
            async def handler(db_session: AsyncSession) -> dict:
                logger = DatabaseAuditLogger(db_session)
                # ... use logger
    """

    __slots__ = ("_session",)

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the database audit logger.

        Args:
            session: An async SQLAlchemy session for database operations.
        """
        self._session = session

    async def log(self, entry: AuditEntry) -> None:
        """Log an audit entry to the database.

        Converts the AuditEntry dataclass to an AuditLog model instance
        and adds it to the session. The caller is responsible for committing
        the transaction.

        Args:
            entry: The audit entry to store.

        Example:
            Log a create action::

                entry = AuditEntry(
                    action=AuditAction.CREATE,
                    actor_id="1",
                    model_name="User",
                    record_id="42",
                )
                await logger.log(entry)
                await session.commit()
        """
        audit_log = self._entry_to_model(entry)
        self._session.add(audit_log)
        await self._session.flush()

    async def query(self, filters: AuditQueryFilters) -> list[AuditEntry]:
        """Query audit entries based on filters.

        Builds and executes a SQLAlchemy query based on the provided filters,
        returning matching audit entries sorted by timestamp descending.

        Args:
            filters: The query filters to apply.

        Returns:
            List of matching audit entries, sorted by timestamp descending.

        Example:
            Query recent user updates::

                filters = AuditQueryFilters(
                    model_name="User",
                    action=AuditAction.UPDATE,
                    limit=50,
                )
                entries = await logger.query(filters)
        """
        stmt = select(AuditLog)

        # Apply filters
        if filters.action is not None:
            stmt = stmt.where(AuditLog.action == filters.action.value)

        if filters.actor_id is not None:
            stmt = stmt.where(AuditLog.actor_id == str(filters.actor_id))

        if filters.actor_email is not None:
            stmt = stmt.where(AuditLog.actor_email.ilike(f"%{filters.actor_email}%"))

        if filters.model_name is not None:
            stmt = stmt.where(AuditLog.model_name == filters.model_name)

        if filters.record_id is not None:
            stmt = stmt.where(AuditLog.record_id == str(filters.record_id))

        if filters.start_date is not None:
            stmt = stmt.where(AuditLog.timestamp >= filters.start_date)

        if filters.end_date is not None:
            stmt = stmt.where(AuditLog.timestamp <= filters.end_date)

        if filters.ip_address is not None:
            stmt = stmt.where(AuditLog.ip_address == filters.ip_address)

        # Order by timestamp descending (most recent first)
        stmt = stmt.order_by(AuditLog.timestamp.desc())

        # Apply pagination
        stmt = stmt.offset(filters.offset).limit(filters.limit)

        result = await self._session.execute(stmt)
        logs = result.scalars().all()

        return [self._model_to_entry(log) for log in logs]

    async def get_recent_activity(
        self,
        limit: int = 50,
        model_name: str | None = None,
    ) -> list[AuditEntry]:
        """Get recent audit activity.

        Convenience method for fetching recent activity, commonly used
        for dashboard displays.

        Args:
            limit: Maximum number of entries to return.
            model_name: Optional filter by model name.

        Returns:
            List of recent audit entries.
        """
        filters = AuditQueryFilters(
            model_name=model_name,
            limit=limit,
        )
        return await self.query(filters)

    async def count(self, filters: AuditQueryFilters | None = None) -> int:
        """Count audit entries matching the filters.

        Args:
            filters: Optional filters to apply. If None, counts all entries.

        Returns:
            Number of matching audit entries.
        """
        from sqlalchemy import func

        stmt = select(func.count()).select_from(AuditLog)

        if filters is not None:
            if filters.action is not None:
                stmt = stmt.where(AuditLog.action == filters.action.value)

            if filters.actor_id is not None:
                stmt = stmt.where(AuditLog.actor_id == str(filters.actor_id))

            if filters.actor_email is not None:
                stmt = stmt.where(AuditLog.actor_email.ilike(f"%{filters.actor_email}%"))

            if filters.model_name is not None:
                stmt = stmt.where(AuditLog.model_name == filters.model_name)

            if filters.record_id is not None:
                stmt = stmt.where(AuditLog.record_id == str(filters.record_id))

            if filters.start_date is not None:
                stmt = stmt.where(AuditLog.timestamp >= filters.start_date)

            if filters.end_date is not None:
                stmt = stmt.where(AuditLog.timestamp <= filters.end_date)

            if filters.ip_address is not None:
                stmt = stmt.where(AuditLog.ip_address == filters.ip_address)

        result = await self._session.execute(stmt)
        count = result.scalar()
        return count if count is not None else 0

    @staticmethod
    def _entry_to_model(entry: AuditEntry) -> AuditLog:
        """Convert an AuditEntry dataclass to an AuditLog model.

        Args:
            entry: The audit entry to convert.

        Returns:
            An AuditLog model instance.
        """
        return AuditLog(
            id=entry.id,
            timestamp=entry.timestamp,
            action=entry.action.value,
            actor_id=str(entry.actor_id) if entry.actor_id is not None else None,
            actor_email=entry.actor_email,
            model_name=entry.model_name,
            record_id=str(entry.record_id) if entry.record_id is not None else None,
            changes=entry.changes,
            metadata_=entry.metadata,
            ip_address=entry.ip_address,
            user_agent=entry.user_agent,
        )

    @staticmethod
    def _model_to_entry(log: AuditLog) -> AuditEntry:
        """Convert an AuditLog model to an AuditEntry dataclass.

        Args:
            log: The audit log model to convert.

        Returns:
            An AuditEntry dataclass instance.
        """
        return AuditEntry(
            id=log.id,
            timestamp=log.timestamp,
            action=AuditAction(log.action),
            actor_id=log.actor_id,
            actor_email=log.actor_email,
            model_name=log.model_name,
            record_id=log.record_id,
            changes=log.changes,
            metadata=log.metadata_,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
        )

    @staticmethod
    def entry_to_activity_dict(entry: AuditEntry) -> dict[str, Any]:
        """Convert an AuditEntry to a dictionary for activity display.

        This format is suitable for the dashboard activity endpoint.

        Args:
            entry: The audit entry to convert.

        Returns:
            A dictionary suitable for activity display.
        """
        return {
            "action": entry.action.value,
            "model": entry.model_name or "System",
            "record_id": entry.record_id,
            "timestamp": entry.timestamp.isoformat(),
            "user": entry.actor_email,
            "details": entry.changes or {},
        }
