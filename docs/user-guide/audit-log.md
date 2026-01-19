# Audit Log

litestar-admin includes a comprehensive audit logging system that tracks all administrative actions, providing accountability and a complete history of changes made through the admin panel.

## Overview

The audit log system provides:

- **Activity Tracking**: Automatic logging of create, update, delete, and login actions
- **Actor Information**: Records who performed each action (user ID and email)
- **Change Tracking**: Captures before/after values for update operations
- **Request Context**: Stores IP address and user agent for security auditing
- **Flexible Storage**: Database-backed storage with in-memory option for testing
- **Query Filters**: Filter logs by date range, model, user, action type, and more

## How Audit Logging Works

litestar-admin automatically logs administrative actions through two mechanisms:

### Automatic Middleware Logging

The `AuditMiddleware` intercepts requests to admin API endpoints and logs them based on the HTTP method:

| HTTP Method | Audit Action |
|-------------|--------------|
| POST | `create` |
| GET | `read` (disabled by default) |
| PUT/PATCH | `update` |
| DELETE | `delete` |

### Manual Logging

For fine-grained control, you can create audit entries programmatically:

```python
from litestar_admin.audit import AuditAction, audit_admin_action

# In a controller or service
entry = await audit_admin_action(
    connection=request,
    action=AuditAction.UPDATE,
    model_name="User",
    record_id=42,
    changes={"email": {"old": "old@example.com", "new": "new@example.com"}},
)
await audit_logger.log(entry)
```

## AuditAction Types

The system supports the following action types:

| Action | Description |
|--------|-------------|
| `create` | A new record was created |
| `read` | A record was viewed (disabled by default) |
| `update` | A record was modified |
| `delete` | A record was deleted |
| `export` | Data was exported |
| `login` | User logged into admin panel |
| `logout` | User logged out of admin panel |
| `bulk_delete` | Multiple records deleted at once |
| `bulk_action` | Bulk operation on multiple records |
| `password_change` | User password was changed |
| `password_reset_request` | Password reset was requested |
| `password_reset_complete` | Password reset was completed |

## Viewing the Audit Log UI

Access the audit log interface at `/admin/audit` (requires appropriate permissions).

### Activity Table

The audit log displays entries in a table with the following columns:

- **Time**: When the action occurred (with relative timestamps like "5m ago")
- **Action**: The type of action with color-coded badges
- **Model**: The affected model name
- **Record**: The ID of the affected record
- **User**: Who performed the action
- **Details**: Expandable view of field changes

### Action Badges

Actions are visually distinguished by color:

- **Create**: Green badge
- **Update**: Blue badge
- **Delete**: Red badge
- **Login**: Purple badge
- **Logout**: Gray badge
- **Export**: Yellow badge

## Filtering and Searching

The audit log UI provides several filtering options:

### Search

Use the search box to find entries matching:
- Model name
- User email
- Action type
- Record ID

### Action Filter

Filter by specific action type using the dropdown:
- All Actions
- Create
- Update
- Delete
- Login
- etc.

### Model Filter

Filter entries by model name to see all activity for a specific model.

### Clearing Filters

Click "Clear Filters" to reset all filter criteria.

## API Endpoints

### Get Recent Activity

```http
GET /admin/api/dashboard/activity?limit=50&model_name=User
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | int | Maximum entries to return (default: 50) |
| `model_name` | string | Filter by model name (optional) |
| `record_id` | string | Filter by record ID (optional) |

**Response:**
```json
[
    {
        "action": "update",
        "model": "User",
        "record_id": "42",
        "timestamp": "2024-01-15T14:30:00Z",
        "user": "admin@example.com",
        "details": {
            "email": {
                "old": "old@example.com",
                "new": "new@example.com"
            }
        }
    }
]
```

## AuditEntry Structure

Each audit entry contains comprehensive information:

```python
from litestar_admin.audit import AuditEntry, AuditAction

entry = AuditEntry(
    id="uuid-string",                    # Unique identifier
    timestamp=datetime.now(tz=utc),      # When action occurred
    action=AuditAction.UPDATE,           # Type of action
    actor_id="1",                        # User ID who performed action
    actor_email="admin@example.com",     # User email
    model_name="User",                   # Affected model
    record_id="42",                      # Affected record ID
    changes={"field": {"old": "a", "new": "b"}},  # Field changes
    metadata={"extra": "info"},          # Additional context
    ip_address="192.168.1.1",           # Client IP
    user_agent="Mozilla/5.0...",        # Client user agent
)
```

## Database Model

Audit entries are stored in the `admin_audit_log` table:

```python
from litestar_admin.audit.models import AuditLog

# AuditLog columns:
# - id: Primary key (UUID string)
# - timestamp: When the action occurred (UTC, indexed)
# - action: Action type (indexed)
# - actor_id: User ID (indexed)
# - actor_email: User email (indexed)
# - model_name: Affected model (indexed)
# - record_id: Affected record ID (indexed)
# - changes: JSON field for field changes
# - metadata_: JSON field for additional context
# - ip_address: Client IP address (indexed)
# - user_agent: Client user agent
```

The table includes composite indexes for common query patterns:
- `(actor_id, action)` - Find actions by user
- `(model_name, record_id)` - Find changes to specific records
- `(timestamp, action)` - Time-based queries

## Configuration

### Enabling Audit Logging

Audit logging is enabled by default when you configure authentication. To customize:

```python
from litestar import Litestar
from litestar_admin import AdminPlugin, AdminConfig
from litestar_admin.audit import (
    AuditMiddleware,
    AuditMiddlewareConfig,
    DatabaseAuditLogger,
)

# Configure audit middleware
audit_config = AuditMiddlewareConfig(
    log_reads=False,                    # Don't log GET requests
    log_successful_only=True,           # Only log 2xx responses
    log_path_patterns=[r"/admin/api/models/.*"],  # Paths to audit
    exclude_path_patterns=[r".*schema$"],  # Paths to exclude
)

# Create admin plugin
admin_plugin = AdminPlugin(
    config=AdminConfig(
        title="My Admin",
        # ... other config
    )
)

# Note: Middleware is typically added automatically by AdminPlugin
# when audit logging is enabled in the config
```

### Middleware Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `log_reads` | bool | `False` | Log GET requests (can be verbose) |
| `log_successful_only` | bool | `True` | Only log successful (2xx) responses |
| `log_path_patterns` | list[str] | `[r"/admin/api/models/.*"]` | Regex patterns for paths to audit |
| `exclude_path_patterns` | list[str] | `[r".*schema$"]` | Regex patterns for paths to exclude |
| `include_request_body` | bool | `False` | Include request body in metadata |
| `max_body_size` | int | `10240` | Max body size to include (bytes) |

## Code Examples

### Custom Audit Queries

Query audit entries programmatically using filters:

```python
from datetime import datetime, timedelta, timezone
from litestar_admin.audit import (
    AuditAction,
    AuditQueryFilters,
)
from litestar_admin.audit.database import DatabaseAuditLogger

async def get_recent_user_changes(session: AsyncSession) -> list:
    """Get all user model changes from the past week."""
    logger = DatabaseAuditLogger(session)

    filters = AuditQueryFilters(
        model_name="User",
        action=AuditAction.UPDATE,
        start_date=datetime.now(tz=timezone.utc) - timedelta(days=7),
        limit=100,
    )

    return await logger.query(filters)
```

### Query by Actor

Find all actions by a specific user:

```python
async def get_user_activity(
    session: AsyncSession,
    user_email: str,
) -> list:
    """Get all actions performed by a specific user."""
    logger = DatabaseAuditLogger(session)

    filters = AuditQueryFilters(
        actor_email=user_email,  # Partial match supported
        limit=200,
    )

    return await logger.query(filters)
```

### Query by Date Range

Find actions within a specific time period:

```python
async def get_activity_for_period(
    session: AsyncSession,
    start: datetime,
    end: datetime,
) -> list:
    """Get all activity within a date range."""
    logger = DatabaseAuditLogger(session)

    filters = AuditQueryFilters(
        start_date=start,
        end_date=end,
        limit=500,
    )

    return await logger.query(filters)
```

### Count Audit Entries

Get counts for reporting:

```python
async def get_action_counts(session: AsyncSession) -> dict:
    """Get counts of different action types."""
    logger = DatabaseAuditLogger(session)
    counts = {}

    for action in AuditAction:
        filters = AuditQueryFilters(action=action)
        counts[action.value] = await logger.count(filters)

    return counts
```

### Calculate Changes Manually

When building custom update logic, calculate field changes:

```python
from litestar_admin.audit import calculate_changes

old_data = {"email": "old@example.com", "name": "John", "role": "viewer"}
new_data = {"email": "new@example.com", "name": "John", "role": "admin"}

changes = calculate_changes(old_data, new_data)
# Returns:
# {
#     "email": {"old": "old@example.com", "new": "new@example.com"},
#     "role": {"old": "viewer", "new": "admin"}
# }
# Note: "name" is not included because it didn't change
```

### Manual Audit Entry Creation

Create audit entries in custom controllers:

```python
from litestar import post
from litestar.connection import Request
from litestar_admin.audit import (
    AuditAction,
    AuditEntry,
    audit_admin_action,
    extract_actor_info,
    extract_request_info,
)
from litestar_admin.audit.database import DatabaseAuditLogger

@post("/admin/api/custom-action")
async def custom_action(
    request: Request,
    db_session: AsyncSession,
) -> dict:
    """Perform a custom action with audit logging."""

    # Perform your action
    result = await do_something_important()

    # Create and log audit entry
    entry = await audit_admin_action(
        connection=request,
        action=AuditAction.BULK_ACTION,
        model_name="CustomModel",
        metadata={"custom_field": "custom_value"},
    )

    logger = DatabaseAuditLogger(db_session)
    await logger.log(entry)

    return {"status": "success"}
```

### Using In-Memory Logger for Testing

```python
import pytest
from litestar_admin.audit import (
    AuditAction,
    AuditEntry,
    AuditQueryFilters,
    InMemoryAuditLogger,
)

@pytest.fixture
def audit_logger():
    return InMemoryAuditLogger()

async def test_audit_logging(audit_logger):
    # Create an entry
    entry = AuditEntry(
        action=AuditAction.CREATE,
        actor_id="1",
        actor_email="test@example.com",
        model_name="User",
        record_id="42",
    )

    # Log it
    await audit_logger.log(entry)

    # Query it back
    filters = AuditQueryFilters(model_name="User")
    results = await audit_logger.query(filters)

    assert len(results) == 1
    assert results[0].action == AuditAction.CREATE
    assert results[0].record_id == "42"

    # Clean up
    audit_logger.clear()
```

## Direct Database Queries

For advanced reporting, you can query the `AuditLog` model directly:

```python
from sqlalchemy import select, func
from litestar_admin.audit.models import AuditLog

async def get_activity_summary(session: AsyncSession) -> list:
    """Get activity counts grouped by model and action."""
    stmt = (
        select(
            AuditLog.model_name,
            AuditLog.action,
            func.count().label("count"),
        )
        .group_by(AuditLog.model_name, AuditLog.action)
        .order_by(func.count().desc())
    )

    result = await session.execute(stmt)
    return result.all()

async def get_most_active_users(session: AsyncSession, limit: int = 10) -> list:
    """Get the most active admin users."""
    stmt = (
        select(
            AuditLog.actor_email,
            func.count().label("action_count"),
        )
        .where(AuditLog.actor_email.isnot(None))
        .group_by(AuditLog.actor_email)
        .order_by(func.count().desc())
        .limit(limit)
    )

    result = await session.execute(stmt)
    return result.all()
```

## Security Considerations

### Data Retention

Consider implementing a retention policy for audit logs:

```python
from datetime import datetime, timedelta, timezone

async def cleanup_old_audit_logs(
    session: AsyncSession,
    days_to_keep: int = 90,
) -> int:
    """Delete audit logs older than specified days."""
    from sqlalchemy import delete
    from litestar_admin.audit.models import AuditLog

    cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=days_to_keep)

    stmt = delete(AuditLog).where(AuditLog.timestamp < cutoff_date)
    result = await session.execute(stmt)
    await session.commit()

    return result.rowcount
```

### Sensitive Data

Audit logs may contain sensitive information. Consider:

- Excluding password fields from change tracking
- Masking sensitive values in the changes dictionary
- Restricting access to audit log endpoints with appropriate permissions

```python
# Example: Mask sensitive fields before logging
SENSITIVE_FIELDS = {"password", "password_hash", "secret_key", "api_key"}

def mask_sensitive_changes(changes: dict) -> dict:
    """Mask sensitive field values in change tracking."""
    masked = {}
    for field, values in changes.items():
        if field.lower() in SENSITIVE_FIELDS:
            masked[field] = {"old": "***", "new": "***"}
        else:
            masked[field] = values
    return masked
```

### Access Control

Audit log viewing requires appropriate permissions. By default, only Admin and Superadmin roles can access `/admin/audit`.

## See Also

- [User Management](user-management.md) - User CRUD with audit integration
- [Custom Views](custom-views.md) - Building custom admin views
