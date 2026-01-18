"""Tests for audit logging system."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from litestar_admin.audit import (
    AuditAction,
    AuditEntry,
    AuditLogger,
    AuditMiddlewareConfig,
    AuditQueryFilters,
    InMemoryAuditLogger,
    audit_admin_action,
    calculate_changes,
    extract_actor_info,
    extract_request_info,
)

if TYPE_CHECKING:
    pass


# ==============================================================================
# Test Fixtures
# ==============================================================================


@dataclass
class MockAdminUser:
    """Mock admin user for testing."""

    id: int
    email: str
    roles: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)


@pytest.fixture
def mock_user() -> MockAdminUser:
    """Return a mock admin user."""
    return MockAdminUser(
        id=1,
        email="admin@example.com",
        roles=["admin"],
        permissions=["models:read", "models:write"],
    )


@pytest.fixture
def mock_connection(mock_user: MockAdminUser) -> MagicMock:
    """Return a mock ASGI connection with user and headers."""
    conn = MagicMock()
    conn.user = mock_user
    conn.client = MagicMock()
    conn.client.host = "192.168.1.100"
    conn.headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Test Browser",
    }
    return conn


@pytest.fixture
def mock_connection_no_user() -> MagicMock:
    """Return a mock ASGI connection without a user."""
    conn = MagicMock()
    conn.user = None
    conn.client = None
    conn.headers = {}
    return conn


@pytest.fixture
def audit_logger() -> InMemoryAuditLogger:
    """Return an InMemoryAuditLogger instance."""
    return InMemoryAuditLogger()


@pytest.fixture
def sample_entry() -> AuditEntry:
    """Return a sample audit entry."""
    return AuditEntry(
        action=AuditAction.UPDATE,
        actor_id=1,
        actor_email="admin@example.com",
        model_name="User",
        record_id=42,
        changes={"email": {"old": "old@example.com", "new": "new@example.com"}},
        metadata={"source": "test"},
        ip_address="192.168.1.100",
        user_agent="Test Browser",
    )


# ==============================================================================
# AuditAction Enum Tests
# ==============================================================================


class TestAuditAction:
    """Tests for the AuditAction enum."""

    def test_action_values(self) -> None:
        """Verify all action values are correct."""
        assert AuditAction.CREATE.value == "create"
        assert AuditAction.READ.value == "read"
        assert AuditAction.UPDATE.value == "update"
        assert AuditAction.DELETE.value == "delete"
        assert AuditAction.EXPORT.value == "export"
        assert AuditAction.LOGIN.value == "login"
        assert AuditAction.LOGOUT.value == "logout"
        assert AuditAction.BULK_DELETE.value == "bulk_delete"
        assert AuditAction.BULK_ACTION.value == "bulk_action"

    def test_action_is_string_enum(self) -> None:
        """Verify actions can be used as strings."""
        assert AuditAction.CREATE == "create"
        assert AuditAction.CREATE.value == "create"

    def test_all_actions_defined(self) -> None:
        """Verify expected number of actions are defined."""
        assert len(AuditAction) == 9


# ==============================================================================
# AuditEntry Tests
# ==============================================================================


class TestAuditEntry:
    """Tests for the AuditEntry dataclass."""

    def test_entry_creation_minimal(self) -> None:
        """Test creating an entry with only required fields."""
        entry = AuditEntry(action=AuditAction.CREATE)

        assert entry.action == AuditAction.CREATE
        assert entry.id is not None
        assert entry.timestamp is not None
        assert entry.actor_id is None
        assert entry.actor_email is None
        assert entry.model_name is None
        assert entry.record_id is None
        assert entry.changes is None
        assert entry.metadata is None
        assert entry.ip_address is None
        assert entry.user_agent is None

    def test_entry_creation_full(self, sample_entry: AuditEntry) -> None:
        """Test creating an entry with all fields."""
        assert sample_entry.action == AuditAction.UPDATE
        assert sample_entry.actor_id == 1
        assert sample_entry.actor_email == "admin@example.com"
        assert sample_entry.model_name == "User"
        assert sample_entry.record_id == 42
        assert sample_entry.changes == {"email": {"old": "old@example.com", "new": "new@example.com"}}
        assert sample_entry.metadata == {"source": "test"}
        assert sample_entry.ip_address == "192.168.1.100"
        assert sample_entry.user_agent == "Test Browser"

    def test_entry_id_is_uuid(self) -> None:
        """Verify entry ID is a valid UUID string."""
        entry = AuditEntry(action=AuditAction.READ)
        # UUID format: 8-4-4-4-12 hex digits
        parts = entry.id.split("-")
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
        assert len(parts[2]) == 4
        assert len(parts[3]) == 4
        assert len(parts[4]) == 12

    def test_entry_timestamp_is_utc(self) -> None:
        """Verify entry timestamp is in UTC."""
        entry = AuditEntry(action=AuditAction.READ)
        assert entry.timestamp.tzinfo is not None
        assert entry.timestamp.tzinfo == timezone.utc

    def test_entry_to_dict(self, sample_entry: AuditEntry) -> None:
        """Test converting entry to dictionary."""
        result = sample_entry.to_dict()

        assert result["id"] == sample_entry.id
        assert result["action"] == "update"
        assert result["actor_id"] == 1
        assert result["actor_email"] == "admin@example.com"
        assert result["model_name"] == "User"
        assert result["record_id"] == 42
        assert result["changes"] == {"email": {"old": "old@example.com", "new": "new@example.com"}}
        assert result["metadata"] == {"source": "test"}
        assert result["ip_address"] == "192.168.1.100"
        assert result["user_agent"] == "Test Browser"
        assert "timestamp" in result  # ISO format string

    def test_entry_to_dict_timestamp_format(self) -> None:
        """Verify timestamp is ISO format in dict."""
        entry = AuditEntry(action=AuditAction.READ)
        result = entry.to_dict()
        # Should be parseable back to datetime
        parsed = datetime.fromisoformat(result["timestamp"])
        assert parsed == entry.timestamp


# ==============================================================================
# AuditQueryFilters Tests
# ==============================================================================


class TestAuditQueryFilters:
    """Tests for the AuditQueryFilters dataclass."""

    def test_default_filters(self) -> None:
        """Test default filter values."""
        filters = AuditQueryFilters()

        assert filters.action is None
        assert filters.actor_id is None
        assert filters.actor_email is None
        assert filters.model_name is None
        assert filters.record_id is None
        assert filters.start_date is None
        assert filters.end_date is None
        assert filters.ip_address is None
        assert filters.limit == 100
        assert filters.offset == 0

    def test_custom_filters(self) -> None:
        """Test creating filters with custom values."""
        start = datetime.now(tz=timezone.utc) - timedelta(days=7)
        end = datetime.now(tz=timezone.utc)

        filters = AuditQueryFilters(
            action=AuditAction.UPDATE,
            model_name="User",
            start_date=start,
            end_date=end,
            limit=50,
            offset=10,
        )

        assert filters.action == AuditAction.UPDATE
        assert filters.model_name == "User"
        assert filters.start_date == start
        assert filters.end_date == end
        assert filters.limit == 50
        assert filters.offset == 10


# ==============================================================================
# InMemoryAuditLogger Tests
# ==============================================================================


class TestInMemoryAuditLogger:
    """Tests for the InMemoryAuditLogger implementation."""

    @pytest.mark.asyncio
    async def test_log_entry(self, audit_logger: InMemoryAuditLogger, sample_entry: AuditEntry) -> None:
        """Test logging an entry."""
        await audit_logger.log(sample_entry)

        assert len(audit_logger.entries) == 1
        assert audit_logger.entries[0] == sample_entry

    @pytest.mark.asyncio
    async def test_log_multiple_entries(self, audit_logger: InMemoryAuditLogger) -> None:
        """Test logging multiple entries."""
        entry1 = AuditEntry(action=AuditAction.CREATE, model_name="User")
        entry2 = AuditEntry(action=AuditAction.UPDATE, model_name="Post")
        entry3 = AuditEntry(action=AuditAction.DELETE, model_name="User")

        await audit_logger.log(entry1)
        await audit_logger.log(entry2)
        await audit_logger.log(entry3)

        assert len(audit_logger.entries) == 3

    @pytest.mark.asyncio
    async def test_query_all(self, audit_logger: InMemoryAuditLogger) -> None:
        """Test querying all entries."""
        entry1 = AuditEntry(action=AuditAction.CREATE)
        entry2 = AuditEntry(action=AuditAction.UPDATE)

        await audit_logger.log(entry1)
        await audit_logger.log(entry2)

        results = await audit_logger.query(AuditQueryFilters())

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_query_by_action(self, audit_logger: InMemoryAuditLogger) -> None:
        """Test filtering by action."""
        await audit_logger.log(AuditEntry(action=AuditAction.CREATE))
        await audit_logger.log(AuditEntry(action=AuditAction.UPDATE))
        await audit_logger.log(AuditEntry(action=AuditAction.UPDATE))
        await audit_logger.log(AuditEntry(action=AuditAction.DELETE))

        results = await audit_logger.query(AuditQueryFilters(action=AuditAction.UPDATE))

        assert len(results) == 2
        assert all(e.action == AuditAction.UPDATE for e in results)

    @pytest.mark.asyncio
    async def test_query_by_actor_id(self, audit_logger: InMemoryAuditLogger) -> None:
        """Test filtering by actor ID."""
        await audit_logger.log(AuditEntry(action=AuditAction.CREATE, actor_id=1))
        await audit_logger.log(AuditEntry(action=AuditAction.UPDATE, actor_id=2))
        await audit_logger.log(AuditEntry(action=AuditAction.DELETE, actor_id=1))

        results = await audit_logger.query(AuditQueryFilters(actor_id=1))

        assert len(results) == 2
        assert all(e.actor_id == 1 for e in results)

    @pytest.mark.asyncio
    async def test_query_by_actor_email_partial(self, audit_logger: InMemoryAuditLogger) -> None:
        """Test filtering by actor email with partial match."""
        await audit_logger.log(AuditEntry(action=AuditAction.CREATE, actor_email="admin@example.com"))
        await audit_logger.log(AuditEntry(action=AuditAction.UPDATE, actor_email="user@example.com"))
        await audit_logger.log(AuditEntry(action=AuditAction.DELETE, actor_email="admin@other.com"))

        results = await audit_logger.query(AuditQueryFilters(actor_email="admin"))

        assert len(results) == 2
        assert all("admin" in (e.actor_email or "") for e in results)

    @pytest.mark.asyncio
    async def test_query_by_model_name(self, audit_logger: InMemoryAuditLogger) -> None:
        """Test filtering by model name."""
        await audit_logger.log(AuditEntry(action=AuditAction.CREATE, model_name="User"))
        await audit_logger.log(AuditEntry(action=AuditAction.UPDATE, model_name="Post"))
        await audit_logger.log(AuditEntry(action=AuditAction.DELETE, model_name="User"))

        results = await audit_logger.query(AuditQueryFilters(model_name="User"))

        assert len(results) == 2
        assert all(e.model_name == "User" for e in results)

    @pytest.mark.asyncio
    async def test_query_by_record_id(self, audit_logger: InMemoryAuditLogger) -> None:
        """Test filtering by record ID."""
        await audit_logger.log(AuditEntry(action=AuditAction.CREATE, record_id=1))
        await audit_logger.log(AuditEntry(action=AuditAction.UPDATE, record_id=2))
        await audit_logger.log(AuditEntry(action=AuditAction.UPDATE, record_id=1))

        results = await audit_logger.query(AuditQueryFilters(record_id=1))

        assert len(results) == 2
        assert all(e.record_id == 1 for e in results)

    @pytest.mark.asyncio
    async def test_query_by_date_range(self, audit_logger: InMemoryAuditLogger) -> None:
        """Test filtering by date range."""
        now = datetime.now(tz=timezone.utc)
        old = now - timedelta(days=10)
        recent = now - timedelta(days=1)

        # Create entries with specific timestamps
        old_entry = AuditEntry(action=AuditAction.CREATE)
        old_entry.timestamp = old

        recent_entry = AuditEntry(action=AuditAction.UPDATE)
        recent_entry.timestamp = recent

        await audit_logger.log(old_entry)
        await audit_logger.log(recent_entry)

        # Query for entries in the last 5 days
        filters = AuditQueryFilters(
            start_date=now - timedelta(days=5),
            end_date=now,
        )
        results = await audit_logger.query(filters)

        assert len(results) == 1
        assert results[0].action == AuditAction.UPDATE

    @pytest.mark.asyncio
    async def test_query_by_ip_address(self, audit_logger: InMemoryAuditLogger) -> None:
        """Test filtering by IP address."""
        await audit_logger.log(AuditEntry(action=AuditAction.CREATE, ip_address="192.168.1.1"))
        await audit_logger.log(AuditEntry(action=AuditAction.UPDATE, ip_address="10.0.0.1"))
        await audit_logger.log(AuditEntry(action=AuditAction.DELETE, ip_address="192.168.1.1"))

        results = await audit_logger.query(AuditQueryFilters(ip_address="192.168.1.1"))

        assert len(results) == 2
        assert all(e.ip_address == "192.168.1.1" for e in results)

    @pytest.mark.asyncio
    async def test_query_pagination(self, audit_logger: InMemoryAuditLogger) -> None:
        """Test query pagination."""
        for i in range(10):
            await audit_logger.log(AuditEntry(action=AuditAction.CREATE, record_id=i))

        # Get first page
        page1 = await audit_logger.query(AuditQueryFilters(limit=3, offset=0))
        assert len(page1) == 3

        # Get second page
        page2 = await audit_logger.query(AuditQueryFilters(limit=3, offset=3))
        assert len(page2) == 3

        # Entries should be different
        page1_ids = {e.record_id for e in page1}
        page2_ids = {e.record_id for e in page2}
        assert page1_ids.isdisjoint(page2_ids)

    @pytest.mark.asyncio
    async def test_query_sort_order(self, audit_logger: InMemoryAuditLogger) -> None:
        """Test that query results are sorted by timestamp descending."""
        now = datetime.now(tz=timezone.utc)

        entry1 = AuditEntry(action=AuditAction.CREATE)
        entry1.timestamp = now - timedelta(hours=2)

        entry2 = AuditEntry(action=AuditAction.UPDATE)
        entry2.timestamp = now - timedelta(hours=1)

        entry3 = AuditEntry(action=AuditAction.DELETE)
        entry3.timestamp = now

        # Log in non-chronological order
        await audit_logger.log(entry2)
        await audit_logger.log(entry1)
        await audit_logger.log(entry3)

        results = await audit_logger.query(AuditQueryFilters())

        # Should be sorted newest first
        assert results[0].action == AuditAction.DELETE
        assert results[1].action == AuditAction.UPDATE
        assert results[2].action == AuditAction.CREATE

    @pytest.mark.asyncio
    async def test_query_combined_filters(self, audit_logger: InMemoryAuditLogger) -> None:
        """Test combining multiple filters."""
        await audit_logger.log(AuditEntry(action=AuditAction.UPDATE, model_name="User", actor_id=1))
        await audit_logger.log(AuditEntry(action=AuditAction.UPDATE, model_name="Post", actor_id=1))
        await audit_logger.log(AuditEntry(action=AuditAction.UPDATE, model_name="User", actor_id=2))
        await audit_logger.log(AuditEntry(action=AuditAction.CREATE, model_name="User", actor_id=1))

        results = await audit_logger.query(
            AuditQueryFilters(
                action=AuditAction.UPDATE,
                model_name="User",
                actor_id=1,
            )
        )

        assert len(results) == 1
        assert results[0].action == AuditAction.UPDATE
        assert results[0].model_name == "User"
        assert results[0].actor_id == 1

    def test_clear(self, audit_logger: InMemoryAuditLogger) -> None:
        """Test clearing all entries."""
        audit_logger._entries.append(AuditEntry(action=AuditAction.CREATE))
        audit_logger._entries.append(AuditEntry(action=AuditAction.UPDATE))

        assert len(audit_logger.entries) == 2

        audit_logger.clear()

        assert len(audit_logger.entries) == 0

    def test_entries_returns_copy(self, audit_logger: InMemoryAuditLogger) -> None:
        """Test that entries property returns a copy."""
        entry = AuditEntry(action=AuditAction.CREATE)
        audit_logger._entries.append(entry)

        # Get entries and modify the list
        entries = audit_logger.entries
        entries.clear()

        # Original should be unchanged
        assert len(audit_logger._entries) == 1


# ==============================================================================
# AuditLogger Protocol Tests
# ==============================================================================


class TestAuditLoggerProtocol:
    """Tests for the AuditLogger protocol."""

    def test_inmemory_implements_protocol(self) -> None:
        """Verify InMemoryAuditLogger implements AuditLogger protocol."""
        logger = InMemoryAuditLogger()
        assert isinstance(logger, AuditLogger)


# ==============================================================================
# calculate_changes Tests
# ==============================================================================


class TestCalculateChanges:
    """Tests for the calculate_changes function."""

    def test_no_changes(self) -> None:
        """Test when data is identical."""
        old = {"name": "John", "age": 30}
        new = {"name": "John", "age": 30}

        changes = calculate_changes(old, new)

        assert changes == {}

    def test_value_changed(self) -> None:
        """Test when a value is modified."""
        old = {"email": "old@example.com", "name": "John"}
        new = {"email": "new@example.com", "name": "John"}

        changes = calculate_changes(old, new)

        assert changes == {"email": {"old": "old@example.com", "new": "new@example.com"}}

    def test_multiple_changes(self) -> None:
        """Test multiple field changes."""
        old = {"name": "John", "age": 30, "city": "NYC"}
        new = {"name": "Jane", "age": 31, "city": "NYC"}

        changes = calculate_changes(old, new)

        assert len(changes) == 2
        assert changes["name"] == {"old": "John", "new": "Jane"}
        assert changes["age"] == {"old": 30, "new": 31}

    def test_field_added(self) -> None:
        """Test when a field is added."""
        old = {"name": "John"}
        new = {"name": "John", "email": "john@example.com"}

        changes = calculate_changes(old, new)

        assert changes == {"email": {"old": None, "new": "john@example.com"}}

    def test_field_removed(self) -> None:
        """Test when a field is removed."""
        old = {"name": "John", "email": "john@example.com"}
        new = {"name": "John"}

        changes = calculate_changes(old, new)

        assert changes == {"email": {"old": "john@example.com", "new": None}}

    def test_include_unchanged(self) -> None:
        """Test including unchanged fields."""
        old = {"name": "John", "age": 30}
        new = {"name": "Jane", "age": 30}

        changes = calculate_changes(old, new, include_unchanged=True)

        assert len(changes) == 2
        assert changes["name"] == {"old": "John", "new": "Jane"}
        assert changes["age"] == {"old": 30, "new": 30}

    def test_none_values(self) -> None:
        """Test handling None values."""
        old = {"name": "John", "email": None}
        new = {"name": "John", "email": "john@example.com"}

        changes = calculate_changes(old, new)

        assert changes == {"email": {"old": None, "new": "john@example.com"}}

    def test_empty_dicts(self) -> None:
        """Test with empty dictionaries."""
        changes = calculate_changes({}, {})

        assert changes == {}

    def test_nested_objects(self) -> None:
        """Test with nested objects (shallow comparison)."""
        old = {"settings": {"theme": "dark"}}
        new = {"settings": {"theme": "light"}}

        changes = calculate_changes(old, new)

        # Nested objects are compared by reference/value
        assert "settings" in changes


# ==============================================================================
# extract_actor_info Tests
# ==============================================================================


class TestExtractActorInfo:
    """Tests for the extract_actor_info function."""

    def test_extract_from_user(self, mock_connection: MagicMock) -> None:
        """Test extracting actor info from connection with user."""
        actor_id, actor_email = extract_actor_info(mock_connection)

        assert actor_id == 1
        assert actor_email == "admin@example.com"

    def test_extract_no_user(self, mock_connection_no_user: MagicMock) -> None:
        """Test extracting actor info when no user present."""
        actor_id, actor_email = extract_actor_info(mock_connection_no_user)

        assert actor_id is None
        assert actor_email is None

    def test_extract_partial_user(self) -> None:
        """Test extracting actor info when user has only ID."""
        conn = MagicMock()
        conn.user = MagicMock()
        conn.user.id = 42
        del conn.user.email  # Remove email attribute

        actor_id, actor_email = extract_actor_info(conn)

        assert actor_id == 42
        assert actor_email is None


# ==============================================================================
# extract_request_info Tests
# ==============================================================================


class TestExtractRequestInfo:
    """Tests for the extract_request_info function."""

    def test_extract_from_connection(self, mock_connection: MagicMock) -> None:
        """Test extracting request info from connection."""
        ip_address, user_agent = extract_request_info(mock_connection)

        assert ip_address == "192.168.1.100"
        assert "Mozilla" in (user_agent or "")

    def test_extract_with_forwarded_for(self) -> None:
        """Test extracting IP from X-Forwarded-For header."""
        conn = MagicMock()
        conn.client = MagicMock()
        conn.client.host = "127.0.0.1"
        conn.headers = {
            "x-forwarded-for": "203.0.113.195, 70.41.3.18, 150.172.238.178",
            "user-agent": "Test Browser",
        }

        ip_address, _user_agent = extract_request_info(conn)

        # Should use first IP from X-Forwarded-For
        assert ip_address == "203.0.113.195"

    def test_extract_no_headers(self, mock_connection_no_user: MagicMock) -> None:
        """Test extracting request info with no headers."""
        ip_address, user_agent = extract_request_info(mock_connection_no_user)

        assert ip_address is None
        assert user_agent is None


# ==============================================================================
# audit_admin_action Tests
# ==============================================================================


class TestAuditAdminAction:
    """Tests for the audit_admin_action helper function."""

    @pytest.mark.asyncio
    async def test_create_entry(self, mock_connection: MagicMock) -> None:
        """Test creating an audit entry from connection."""
        entry = await audit_admin_action(
            connection=mock_connection,
            action=AuditAction.UPDATE,
            model_name="User",
            record_id=42,
            changes={"email": {"old": "a@b.com", "new": "c@d.com"}},
            metadata={"source": "api"},
        )

        assert entry.action == AuditAction.UPDATE
        assert entry.actor_id == 1
        assert entry.actor_email == "admin@example.com"
        assert entry.model_name == "User"
        assert entry.record_id == 42
        assert entry.changes == {"email": {"old": "a@b.com", "new": "c@d.com"}}
        assert entry.metadata == {"source": "api"}
        assert entry.ip_address == "192.168.1.100"
        assert entry.user_agent is not None

    @pytest.mark.asyncio
    async def test_create_entry_no_user(self, mock_connection_no_user: MagicMock) -> None:
        """Test creating an audit entry without user."""
        entry = await audit_admin_action(
            connection=mock_connection_no_user,
            action=AuditAction.LOGIN,
        )

        assert entry.action == AuditAction.LOGIN
        assert entry.actor_id is None
        assert entry.actor_email is None

    @pytest.mark.asyncio
    async def test_create_entry_minimal(self, mock_connection: MagicMock) -> None:
        """Test creating an entry with minimal parameters."""
        entry = await audit_admin_action(
            connection=mock_connection,
            action=AuditAction.READ,
        )

        assert entry.action == AuditAction.READ
        assert entry.model_name is None
        assert entry.record_id is None
        assert entry.changes is None
        assert entry.metadata is None


# ==============================================================================
# AuditMiddlewareConfig Tests
# ==============================================================================


class TestAuditMiddlewareConfig:
    """Tests for the AuditMiddlewareConfig dataclass."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = AuditMiddlewareConfig()

        assert config.log_reads is False
        assert len(config.log_path_patterns) > 0
        assert config.log_successful_only is True
        assert config.include_request_body is False
        assert config.max_body_size == 10240

    def test_custom_config(self) -> None:
        """Test custom configuration."""
        config = AuditMiddlewareConfig(
            log_reads=True,
            log_path_patterns=[r"/api/.*"],
            log_successful_only=False,
        )

        assert config.log_reads is True
        assert config.log_path_patterns == [r"/api/.*"]
        assert config.log_successful_only is False


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestAuditIntegration:
    """Integration tests for the audit logging system."""

    @pytest.mark.asyncio
    async def test_full_workflow(self, mock_connection: MagicMock) -> None:
        """Test complete audit workflow: create, log, query."""
        logger = InMemoryAuditLogger()

        # Create and log entries
        entry1 = await audit_admin_action(
            connection=mock_connection,
            action=AuditAction.CREATE,
            model_name="User",
            record_id=1,
        )
        await logger.log(entry1)

        entry2 = await audit_admin_action(
            connection=mock_connection,
            action=AuditAction.UPDATE,
            model_name="User",
            record_id=1,
            changes={"name": {"old": "John", "new": "Jane"}},
        )
        await logger.log(entry2)

        # Query entries for this user
        results = await logger.query(AuditQueryFilters(model_name="User", record_id=1))

        assert len(results) == 2
        assert results[0].action == AuditAction.UPDATE  # Most recent first
        assert results[1].action == AuditAction.CREATE

    @pytest.mark.asyncio
    async def test_audit_with_change_tracking(self, mock_connection: MagicMock) -> None:
        """Test audit with calculated changes."""
        logger = InMemoryAuditLogger()

        old_data = {"email": "old@example.com", "name": "John", "age": 30}
        new_data = {"email": "new@example.com", "name": "John", "age": 31}

        changes = calculate_changes(old_data, new_data)

        entry = await audit_admin_action(
            connection=mock_connection,
            action=AuditAction.UPDATE,
            model_name="User",
            record_id=42,
            changes=changes,
        )
        await logger.log(entry)

        results = await logger.query(AuditQueryFilters())

        assert len(results) == 1
        assert results[0].changes is not None
        assert "email" in results[0].changes
        assert "age" in results[0].changes
        assert "name" not in results[0].changes  # Unchanged
