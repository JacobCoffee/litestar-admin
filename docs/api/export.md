# Export API

The Export API provides endpoints for exporting model data in CSV, JSON, or Excel (XLSX) format. Supports both full exports and selective exports of specific records.

Export endpoints are under `/admin/api/models`.

## Endpoints

### Export All Records

Export all records from a model in CSV or JSON format.

```{rubric} GET /api/models/{model_name}/export
```

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `model_name` | string | The name of the registered model |

**Query Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `format` | string | "csv" | Export format: "csv", "json", or "xlsx" |

**Headers**

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes | `Bearer <access_token>` |

**Example Request (CSV)**

```http
GET /admin/api/models/User/export?format=csv HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Success Response (200 OK)**

Response is a streaming download with appropriate content type and headers:

```http
HTTP/1.1 200 OK
Content-Type: text/csv
Content-Disposition: attachment; filename="User_export.csv"

id,email,name,is_active,created_at
1,john@example.com,John Doe,true,2024-01-15T10:30:00
2,jane@example.com,Jane Smith,true,2024-01-14T09:15:00
3,bob@example.com,Bob Wilson,false,2024-01-13T08:00:00
```

**Example Request (JSON)**

```http
GET /admin/api/models/User/export?format=json HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Success Response (200 OK)**

```http
HTTP/1.1 200 OK
Content-Type: application/json
Content-Disposition: attachment; filename="User_export.json"

[
  {
    "id": 1,
    "email": "john@example.com",
    "name": "John Doe",
    "is_active": true,
    "created_at": "2024-01-15T10:30:00"
  },
  {
    "id": 2,
    "email": "jane@example.com",
    "name": "Jane Smith",
    "is_active": true,
    "created_at": "2024-01-14T09:15:00"
  }
]
```

**Error Responses**

| Status | Response |
|--------|----------|
| 404 | `{"detail": "Model 'InvalidModel' not found"}` |
| 422 | `{"detail": "Unsupported export format: 'xml'. Supported formats: csv, json"}` |
| 422 | `{"detail": "Export is not allowed for model 'SecretData'"}` |

---

### Export Selected Records

Export specific records by their primary key values.

```{rubric} POST /api/models/{model_name}/bulk/export
```

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `model_name` | string | The name of the registered model |

**Headers**

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes | `Bearer <access_token>` |
| `Content-Type` | Yes | `application/json` |

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ids` | array | Yes | List of primary key values to export |
| `format` | string | No | Export format: "csv", "json", or "xlsx" (default: "csv") |

**Example Request**

```http
POST /admin/api/models/User/bulk/export HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "ids": [1, 2, 5, 10],
  "format": "json"
}
```

**Success Response (200 OK)**

```http
HTTP/1.1 200 OK
Content-Type: application/json
Content-Disposition: attachment; filename="User_export.json"

[
  {
    "id": 1,
    "email": "john@example.com",
    "name": "John Doe",
    "is_active": true
  },
  {
    "id": 2,
    "email": "jane@example.com",
    "name": "Jane Smith",
    "is_active": true
  },
  {
    "id": 5,
    "email": "alice@example.com",
    "name": "Alice Brown",
    "is_active": true
  },
  {
    "id": 10,
    "email": "bob@example.com",
    "name": "Bob Wilson",
    "is_active": false
  }
]
```

**Error Responses**

| Status | Response |
|--------|----------|
| 404 | `{"detail": "Model 'InvalidModel' not found"}` |
| 422 | `{"detail": "No IDs provided for export"}` |
| 422 | `{"detail": "Export is not allowed for model 'SecretData'"}` |

---

## Export Formats

### CSV Format

CSV exports include:
- Header row with column names
- One row per record
- Values properly escaped and quoted

Special value handling:
- `null` values appear as empty strings
- Dates are formatted as ISO 8601 strings
- Booleans are lowercase `true`/`false`
- Complex objects are converted to string representation

### JSON Format

JSON exports are returned as a JSON array of objects:
- Each object represents one record
- Keys match column names
- Values preserve their types (numbers, booleans, null)
- Dates are ISO 8601 strings

### Excel (XLSX) Format

Excel exports create a proper `.xlsx` file with:
- A single worksheet named after the model
- Header row with column names
- Native Excel data types (numbers, dates, booleans)
- Proper formatting for dates and times

**Requirements:**

Excel export requires the `openpyxl` library. Install it with:

```bash
pip install litestar-admin[excel]
```

If `openpyxl` is not installed, XLSX export requests will return a helpful error message.

**Example Request (XLSX)**

```http
GET /admin/api/models/User/export?format=xlsx HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Success Response (200 OK)**

```http
HTTP/1.1 200 OK
Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
Content-Disposition: attachment; filename="User_export.xlsx"

[Binary Excel file content]
```

Special value handling in Excel:
- Dates and datetimes are native Excel dates
- UUIDs are converted to strings
- Lists and dicts are JSON-serialized
- `null` values are empty cells

---

## Streaming

Exports are streamed in chunks for memory efficiency:

1. Large datasets are processed in chunks of 1000 records
2. Each chunk is serialized and sent immediately
3. Client receives data progressively
4. Server memory usage stays constant regardless of dataset size

This means:
- Exports start immediately without waiting for all data
- Very large exports won't cause memory issues
- Network timeouts are less likely

---

## Export Permissions

Exports can be controlled at the model level:

```python
from litestar_admin import ModelView

class UserAdmin(ModelView, model=User):
    # Disable export for this model
    can_export = False


class OrderAdmin(ModelView, model=Order):
    # Export enabled (default)
    can_export = True
```

Additionally, the `models:export` permission is required for users to access export endpoints. Users with the `admin` or `superadmin` role have this permission by default.

---

## Column Selection

Exports include only the columns defined in `column_list` for the model view:

```python
class UserAdmin(ModelView, model=User):
    # Only these columns will be exported
    column_list = ["id", "email", "name", "is_active", "created_at"]

    # These columns exist in the model but won't be exported
    # password_hash, internal_notes, etc.
```

To export all columns, leave `column_list` empty or set it to all column names.

---

## Example: Exporting with Frontend

Here's how you might handle exports in a frontend application:

```javascript
// Export all records as CSV
async function exportAll(modelName, format = 'csv') {
  const response = await fetch(
    `/admin/api/models/${modelName}/export?format=${format}`,
    {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    }
  );

  // Get filename from Content-Disposition header
  const disposition = response.headers.get('Content-Disposition');
  const filename = disposition?.match(/filename="(.+)"/)?.[1] || `${modelName}.${format}`;

  // Download the file
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  window.URL.revokeObjectURL(url);
}

// Export selected records
async function exportSelected(modelName, ids, format = 'csv') {
  const response = await fetch(
    `/admin/api/models/${modelName}/bulk/export`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ ids, format })
    }
  );

  // Same download logic as above
  const blob = await response.blob();
  // ...
}
```

---

## Response Headers

Export responses include these headers:

| Header | Description | Example |
|--------|-------------|---------|
| `Content-Type` | MIME type of the export | `text/csv` or `application/json` |
| `Content-Disposition` | Suggests filename for download | `attachment; filename="User_export.csv"` |

:::{tip}
Use the `Content-Disposition` header to get the suggested filename when implementing download functionality.
:::
