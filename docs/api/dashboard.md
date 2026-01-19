# Dashboard API

The Dashboard API provides endpoints for retrieving admin panel statistics, recent activity, and custom widget data.

All dashboard endpoints are under `/admin/api/dashboard`.

## Endpoints

### Get Dashboard Statistics

Get statistics for all registered models including record counts.

```{rubric} GET /api/dashboard/stats
```

**Headers**

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes | `Bearer <access_token>` |

**Example Request**

```http
GET /admin/api/dashboard/stats HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Success Response (200 OK)**

```json
{
  "models": [
    {
      "name": "User",
      "model_name": "User",
      "count": 150,
      "icon": "users",
      "category": "Authentication"
    },
    {
      "name": "Product",
      "model_name": "Product",
      "count": 42,
      "icon": "box",
      "category": "Inventory"
    },
    {
      "name": "Order",
      "model_name": "Order",
      "count": 328,
      "icon": "shopping-cart",
      "category": "Sales"
    }
  ],
  "total_records": 520,
  "total_models": 3,
  "widgets": []
}
```

**Response Fields**

| Field | Type | Description |
|-------|------|-------------|
| `models` | array | Statistics for each registered model |
| `models[].name` | string | Display name of the model |
| `models[].model_name` | string | Internal model class name |
| `models[].count` | integer | Total number of records |
| `models[].icon` | string | Icon identifier for UI display |
| `models[].category` | string or null | Category for grouping |
| `total_records` | integer | Sum of all records across models |
| `total_models` | integer | Number of registered models |
| `widgets` | array | Custom dashboard widget data |

---

### Get Recent Activity

Get recent admin activity from the audit log.

```{rubric} GET /api/dashboard/activity
```

**Headers**

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes | `Bearer <access_token>` |

**Query Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 50 | Maximum number of entries to return |

**Example Request**

```http
GET /admin/api/dashboard/activity?limit=20 HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Success Response (200 OK)**

```json
[
  {
    "action": "create",
    "model": "User",
    "record_id": 151,
    "timestamp": "2024-01-16T14:30:00",
    "user": "admin@example.com",
    "details": {
      "fields": ["email", "name", "is_active"]
    }
  },
  {
    "action": "update",
    "model": "Product",
    "record_id": 42,
    "timestamp": "2024-01-16T14:25:00",
    "user": "editor@example.com",
    "details": {
      "changed_fields": ["price", "description"]
    }
  },
  {
    "action": "delete",
    "model": "Order",
    "record_id": 100,
    "timestamp": "2024-01-16T14:20:00",
    "user": "admin@example.com",
    "details": {}
  }
]
```

**Response Fields**

| Field | Type | Description |
|-------|------|-------------|
| `action` | string | Action performed: "create", "update", "delete", etc. |
| `model` | string | Name of the affected model |
| `record_id` | string, integer, or null | ID of the affected record |
| `timestamp` | string | ISO 8601 timestamp of the action |
| `user` | string or null | User who performed the action |
| `details` | object | Additional action-specific information |

**Available Action Types**

| Action | Description |
|--------|-------------|
| `create` | A new record was created |
| `update` | An existing record was updated |
| `delete` | A record was deleted |
| `bulk_delete` | Multiple records were deleted |
| `export` | Data was exported |
| `login` | User logged in |
| `logout` | User logged out |

:::{note}
The activity endpoint returns an empty array if audit logging is not configured. Configure an `AuditLogger` in your `AdminConfig` to enable activity tracking.
:::

---

### Get Custom Widgets

Get custom dashboard widget configurations.

```{rubric} GET /api/dashboard/widgets
```

**Headers**

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes | `Bearer <access_token>` |

**Example Request**

```http
GET /admin/api/dashboard/widgets HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Success Response (200 OK)**

```json
[
  {
    "id": "revenue-chart",
    "type": "chart",
    "title": "Monthly Revenue",
    "data": {
      "labels": ["Jan", "Feb", "Mar", "Apr"],
      "values": [12500, 15000, 14200, 18000]
    },
    "config": {
      "chartType": "line",
      "color": "#3B82F6"
    }
  },
  {
    "id": "active-users",
    "type": "metric",
    "title": "Active Users",
    "data": {
      "value": 1250,
      "change": 12.5,
      "period": "last 7 days"
    },
    "config": {
      "format": "number",
      "showTrend": true
    }
  }
]
```

**Response Fields**

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier for the widget |
| `type` | string | Widget type (see types below) |
| `title` | string | Display title |
| `data` | object | Widget-specific data payload |
| `config` | object | Optional rendering configuration |

**Widget Types**

| Type | Description |
|------|-------------|
| `metric` | Single value with optional trend indicator |
| `chart` | Line, bar, or pie chart |
| `list` | List of items |
| `custom` | Custom component type |

---

## Configuring Custom Widgets

Custom widgets are configured via `AdminConfig.extra["widgets"]`:

```python
from litestar_admin import AdminConfig, AdminPlugin

config = AdminConfig(
    title="My Admin",
    extra={
        "widgets": [
            {
                "id": "sales-metric",
                "type": "metric",
                "title": "Total Sales",
                "data": {
                    "value": 45000,
                    "change": 8.3,
                },
                "config": {
                    "format": "currency",
                    "currency": "USD",
                },
            },
            {
                "id": "orders-chart",
                "type": "chart",
                "title": "Orders This Week",
                "data": {
                    "labels": ["Mon", "Tue", "Wed", "Thu", "Fri"],
                    "values": [45, 52, 48, 61, 55],
                },
                "config": {
                    "chartType": "bar",
                },
            },
        ]
    }
)
```

For dynamic widget data, you can create a custom endpoint that fetches data and updates the widget configuration at runtime:

```python
from litestar import get
from litestar.di import Provide

@get("/api/dashboard/custom-widgets")
async def get_custom_widgets(db_session: AsyncSession) -> list[dict]:
    # Fetch dynamic data
    sales = await get_total_sales(db_session)
    orders = await get_weekly_orders(db_session)

    return [
        {
            "id": "sales-metric",
            "type": "metric",
            "title": "Total Sales",
            "data": {"value": sales, "change": calculate_change(sales)},
            "config": {"format": "currency"},
        },
        # ... more widgets
    ]
```

---

## Dashboard Data Flow

Here's how the dashboard fetches and displays data:

```text
Frontend                  Dashboard API              Database
  |                            |                         |
  |-- GET /dashboard/stats --->|                         |
  |                            |-- COUNT each model ---->|
  |                            |<-- record counts -------|
  |<-- stats with counts ------|                         |
  |                            |                         |
  |-- GET /dashboard/activity->|                         |
  |                            |-- query audit log ----->|
  |                            |<-- activity entries ----|
  |<-- activity feed ----------|                         |
  |                            |                         |
  |-- GET /dashboard/widgets ->|                         |
  |<-- widget configurations --|                         |
```

## Performance Considerations

The `/dashboard/stats` endpoint queries the database for each registered model's count. For large databases with many models, consider:

1. **Caching**: Cache the counts with a short TTL (e.g., 60 seconds)
2. **Approximate Counts**: Use database-specific approximate count functions
3. **Background Updates**: Precompute counts in a background task

Example with caching:

```python
from litestar.stores.redis import RedisStore

# In your custom stats endpoint
@get("/api/dashboard/stats")
async def get_cached_stats(
    cache: RedisStore,
    db_session: AsyncSession,
) -> DashboardStats:
    cached = await cache.get("dashboard_stats")
    if cached:
        return DashboardStats(**cached)

    stats = await compute_stats(db_session)
    await cache.set("dashboard_stats", stats.dict(), expires_in=60)
    return stats
```
