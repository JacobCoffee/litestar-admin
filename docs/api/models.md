# Models API

The Models API provides CRUD (Create, Read, Update, Delete) operations for all registered models in the admin panel.

All model endpoints are under `/admin/api/models`.

## Endpoints

### List Registered Models

Get a list of all models registered with the admin panel.

```{rubric} GET /api/models
```

**Headers**

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes | `Bearer <access_token>` |

**Example Request**

```http
GET /admin/api/models HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Success Response (200 OK)**

```json
[
  {
    "name": "User",
    "model_name": "User",
    "icon": "users",
    "category": "Authentication",
    "can_create": true,
    "can_edit": true,
    "can_delete": false,
    "can_view_details": true
  },
  {
    "name": "Product",
    "model_name": "Product",
    "icon": "box",
    "category": "Inventory",
    "can_create": true,
    "can_edit": true,
    "can_delete": true,
    "can_view_details": true
  }
]
```

**Response Fields**

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Display name of the model |
| `model_name` | string | Internal model class name |
| `icon` | string | Icon identifier for UI display |
| `category` | string or null | Category for grouping in sidebar |
| `can_create` | boolean | Whether new records can be created |
| `can_edit` | boolean | Whether records can be edited |
| `can_delete` | boolean | Whether records can be deleted |
| `can_view_details` | boolean | Whether record details can be viewed |

---

### List Records

Get paginated records for a specific model with optional filtering and sorting.

```{rubric} GET /api/models/{model_name}
```

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `model_name` | string | The name of the registered model |

**Query Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `offset` | integer | 0 | Number of records to skip |
| `limit` | integer | 50 | Max records to return (max 100) |
| `sort_by` | string | null | Column name to sort by |
| `sort_order` | string | "asc" | Sort direction: "asc" or "desc" |
| `search` | string | null | Search string for searchable columns |

**Example Request**

```http
GET /admin/api/models/User?offset=0&limit=10&sort_by=created_at&sort_order=desc&search=john HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Success Response (200 OK)**

```json
{
  "items": [
    {
      "id": 1,
      "email": "john@example.com",
      "name": "John Doe",
      "created_at": "2024-01-15T10:30:00"
    },
    {
      "id": 2,
      "email": "johnny@example.com",
      "name": "Johnny Smith",
      "created_at": "2024-01-14T09:15:00"
    }
  ],
  "total": 25,
  "offset": 0,
  "limit": 10
}
```

**Response Fields**

| Field | Type | Description |
|-------|------|-------------|
| `items` | array | List of serialized records |
| `total` | integer | Total count of matching records |
| `offset` | integer | Current offset in result set |
| `limit` | integer | Number of records requested |

**Error Responses**

| Status | Response |
|--------|----------|
| 404 | `{"detail": "Model 'InvalidModel' not found"}` |

---

### Get Single Record

Get a single record by its primary key.

```{rubric} GET /api/models/{model_name}/{record_id}
```

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `model_name` | string | The name of the registered model |
| `record_id` | string | The primary key value |

**Example Request**

```http
GET /admin/api/models/User/1 HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Success Response (200 OK)**

```json
{
  "id": 1,
  "email": "john@example.com",
  "name": "John Doe",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-15T10:30:00"
}
```

**Error Responses**

| Status | Response |
|--------|----------|
| 404 | `{"detail": "Model 'User' not found"}` |
| 404 | `{"detail": "Record '999' not found in 'User'"}` |

---

### Create Record

Create a new record for the specified model.

```{rubric} POST /api/models/{model_name}
```

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `model_name` | string | The name of the registered model |

**Request Body**

JSON object containing the field values for the new record. Required fields depend on the model definition.

**Example Request**

```http
POST /admin/api/models/User HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "email": "newuser@example.com",
  "name": "New User",
  "is_active": true
}
```

**Success Response (201 Created)**

```json
{
  "id": 3,
  "email": "newuser@example.com",
  "name": "New User",
  "is_active": true,
  "created_at": "2024-01-16T14:20:00",
  "updated_at": "2024-01-16T14:20:00"
}
```

**Error Responses**

| Status | Response |
|--------|----------|
| 404 | `{"detail": "Model 'User' not found"}` |
| 422 | `{"detail": "Validation error: email is required"}` |

---

### Full Update Record

Replace all fields of a record with the provided data.

```{rubric} PUT /api/models/{model_name}/{record_id}
```

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `model_name` | string | The name of the registered model |
| `record_id` | string | The primary key value |

**Request Body**

JSON object containing complete field values. All editable fields should be provided.

**Example Request**

```http
PUT /admin/api/models/User/1 HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "email": "updated@example.com",
  "name": "Updated Name",
  "is_active": false
}
```

**Success Response (200 OK)**

```json
{
  "id": 1,
  "email": "updated@example.com",
  "name": "Updated Name",
  "is_active": false,
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-16T14:25:00"
}
```

**Error Responses**

| Status | Response |
|--------|----------|
| 404 | `{"detail": "Model 'User' not found"}` |
| 404 | `{"detail": "Record '999' not found in 'User'"}` |

---

### Partial Update Record

Update only the provided fields of a record.

```{rubric} PATCH /api/models/{model_name}/{record_id}
```

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `model_name` | string | The name of the registered model |
| `record_id` | string | The primary key value |

**Request Body**

JSON object containing only the fields to update.

**Example Request**

```http
PATCH /admin/api/models/User/1 HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "name": "Partial Update"
}
```

**Success Response (200 OK)**

```json
{
  "id": 1,
  "email": "updated@example.com",
  "name": "Partial Update",
  "is_active": false,
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-16T14:30:00"
}
```

**Error Responses**

| Status | Response |
|--------|----------|
| 404 | `{"detail": "Model 'User' not found"}` |
| 404 | `{"detail": "Record '999' not found in 'User'"}` |

---

### Delete Record

Delete a record by its primary key.

```{rubric} DELETE /api/models/{model_name}/{record_id}
```

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `model_name` | string | The name of the registered model |
| `record_id` | string | The primary key value |

**Query Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `soft_delete` | boolean | false | If true, perform soft delete if supported |

**Example Request**

```http
DELETE /admin/api/models/User/1 HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Success Response (200 OK)**

```json
{
  "success": true,
  "message": "Record '1' deleted successfully"
}
```

**Error Responses**

| Status | Response |
|--------|----------|
| 404 | `{"detail": "Model 'User' not found"}` |
| 404 | `{"detail": "Record '999' not found in 'User'"}` |

:::{note}
When `soft_delete=true` is passed, the record is marked as deleted (via a `deleted_at` timestamp) rather than being removed from the database. This only works if the model supports soft deletes.
:::

---

### Get Model Schema

Get the JSON schema for a model's fields, useful for dynamic form generation.

```{rubric} GET /api/models/{model_name}/schema
```

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `model_name` | string | The name of the registered model |

**Example Request**

```http
GET /admin/api/models/User/schema HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Success Response (200 OK)**

```json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "integer",
      "readOnly": true
    },
    "email": {
      "type": "string",
      "format": "email",
      "maxLength": 255
    },
    "name": {
      "type": "string",
      "maxLength": 100
    },
    "is_active": {
      "type": "boolean",
      "default": true
    },
    "created_at": {
      "type": "string",
      "format": "date-time",
      "readOnly": true
    }
  },
  "required": ["email", "name"]
}
```

**Error Responses**

| Status | Response |
|--------|----------|
| 404 | `{"detail": "Model 'User' not found"}` |

---

## Data Serialization

Records are automatically serialized to JSON with type conversions:

| Python Type | JSON Type |
|-------------|-----------|
| `datetime`, `date` | ISO 8601 string |
| `Decimal` | float |
| `UUID` | string |
| `bytes` | UTF-8 string |
| `None` | null |

## Pagination

All list endpoints use offset-based pagination:

- `offset`: Number of records to skip (default: 0)
- `limit`: Maximum records to return (default: 50, max: 100)

To paginate through large datasets:

```text
# First page
GET /api/models/User?offset=0&limit=50

# Second page
GET /api/models/User?offset=50&limit=50

# Third page
GET /api/models/User?offset=100&limit=50
```

Use the `total` field in the response to determine the total number of pages:

```python
total_pages = ceil(response["total"] / limit)
```

## Filtering and Search

The `search` parameter performs a case-insensitive search across all columns marked as searchable in the model view configuration:

```python
class UserAdmin(ModelView, model=User):
    column_searchable_list = ["email", "name"]
```

With this configuration, `?search=john` would match:
- `email: "john@example.com"`
- `name: "John Doe"`

## Sorting

Use `sort_by` and `sort_order` to control the order of results:

```text
# Sort by name ascending
GET /api/models/User?sort_by=name&sort_order=asc

# Sort by created_at descending (newest first)
GET /api/models/User?sort_by=created_at&sort_order=desc
```

:::{note}
Only sortable columns can be used with `sort_by`. Attempting to sort by a non-sortable column will be ignored.
:::

## Primary Key Types

The API automatically handles different primary key types:

| Type | Example URL |
|------|-------------|
| Integer | `/api/models/User/123` |
| UUID | `/api/models/Order/550e8400-e29b-41d4-a716-446655440000` |
| String | `/api/models/Setting/theme` |

The primary key value in the URL is automatically converted to the appropriate type based on the model's primary key column definition.
