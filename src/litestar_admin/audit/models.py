"""SQLAlchemy models for audit logging.

This module provides database models for persistent audit log storage,
designed for use with Advanced-Alchemy and SQLAlchemy 2.x.

Example:
    Using the AuditLog model::

        from litestar_admin.audit.models import AuditLog
        from sqlalchemy.ext.asyncio import AsyncSession


        async def create_audit_entry(session: AsyncSession) -> None:
            entry = AuditLog(
                action="create",
                actor_id="1",
                actor_email="admin@example.com",
                model_name="User",
                record_id="42",
            )
            session.add(entry)
            await session.commit()
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, Index, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

__all__ = ["AuditLog", "AuditLogBase"]


class AuditLogBase(DeclarativeBase):
    """Base class for audit log models.

    Use this as the base for the AuditLog model if you need a separate
    metadata/base from your main application models.
    """


class AuditLog(AuditLogBase):
    """SQLAlchemy model for storing audit log entries.

    This model stores comprehensive information about admin actions including
    who performed them, what was affected, and any changes made.

    Attributes:
        id: Unique identifier (UUID string).
        timestamp: When the action occurred (UTC).
        action: The type of action (create, read, update, delete, etc.).
        actor_id: ID of the user who performed the action.
        actor_email: Email of the user who performed the action.
        model_name: Name of the affected model.
        record_id: ID of the affected record.
        changes: JSON field containing field changes for updates.
        metadata_: JSON field for additional context.
        ip_address: IP address of the request origin.
        user_agent: User agent string of the client.

    Example:
        Query recent audit entries::

            from sqlalchemy import select

            stmt = (
                select(AuditLog)
                .where(AuditLog.model_name == "User")
                .order_by(AuditLog.timestamp.desc())
                .limit(50)
            )
            result = await session.execute(stmt)
            entries = result.scalars().all()
    """

    __tablename__ = "admin_audit_log"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=timezone.utc),
        nullable=False,
        index=True,
    )

    # Action type
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    # Actor information
    actor_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    actor_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    # Target information
    model_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    record_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    # Change tracking (JSON)
    changes: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    # Additional metadata (JSON)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
    )

    # Request information
    ip_address: Mapped[str | None] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True,
        index=True,
    )
    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Indexes for common queries
    __table_args__ = (
        Index("ix_audit_log_actor_action", "actor_id", "action"),
        Index("ix_audit_log_model_record", "model_name", "record_id"),
        Index("ix_audit_log_timestamp_action", "timestamp", "action"),
    )

    def __repr__(self) -> str:
        """Return string representation of the audit log entry."""
        return (
            f"<AuditLog(id={self.id!r}, action={self.action!r}, model={self.model_name!r}, record={self.record_id!r})>"
        )
