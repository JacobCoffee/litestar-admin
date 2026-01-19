# Import API

The Import API provides endpoints for importing model data from CSV files. The import process is designed as a multi-step wizard with preview, validation, and execution phases.

Import endpoints are under `/admin/api/models`.

## Overview

The import workflow consists of three steps:

1. **Preview** - Upload CSV, auto-detect format, preview data
2. **Validate** - Map columns, validate all rows
3. **Execute** - Import data with error handling

## Endpoints

### Preview Import

Upload a CSV file and get a preview with auto-detected format and column types.

```{rubric} POST /api/models/{model_name}/import/preview
```

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `model_name` | string | The name of the registered model |

**Headers**

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes | `Bearer <access_token>` |
| `Content-Type` | Yes | `multipart/form-data` |

**Request Body**

Upload a CSV file as `data` in a multipart form.

**Example Request**

```http
POST /admin/api/models/User/import/preview HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: multipart/form-data; boundary=----FormBoundary

------FormBoundary
Content-Disposition: form-data; name="data"; filename="users.csv"
Content-Type: text/csv

email,name,is_active
john@example.com,John Doe,true
jane@example.com,Jane Smith,true
------FormBoundary--
```

**Success Response (200 OK)**

```json
{
  "headers": ["email", "name", "is_active"],
  "preview_rows": [
    {"email": "john@example.com", "name": "John Doe", "is_active": "true"},
    {"email": "jane@example.com", "name": "Jane Smith", "is_active": "true"}
  ],
  "column_types": [
    {"csv_column": "email", "detected_type": "string", "sample_values": ["john@example.com", "jane@example.com"], "nullable": false},
    {"csv_column": "name", "detected_type": "string", "sample_values": ["John Doe", "Jane Smith"], "nullable": false},
    {"csv_column": "is_active", "detected_type": "boolean", "sample_values": ["true", "true"], "nullable": false}
  ],
  "model_schema": [
    {"name": "id", "type": "integer", "format": null, "nullable": false, "required": false, "primary_key": true},
    {"name": "email", "type": "string", "format": null, "nullable": false, "required": true, "primary_key": false, "max_length": 255},
    {"name": "name", "type": "string", "format": null, "nullable": true, "required": false, "primary_key": false, "max_length": 100},
    {"name": "is_active", "type": "boolean", "format": null, "nullable": false, "required": false, "primary_key": false}
  ],
  "delimiter": ",",
  "encoding": "utf-8",
  "total_rows": 2
}
```

**Auto-Detection Features**

The preview endpoint automatically detects:

- **Delimiter**: Comma (`,`), semicolon (`;`), tab (`\t`), or pipe (`|`)
- **Encoding**: UTF-8, UTF-8 with BOM, Latin-1, or Windows-1252
- **Column Types**: string, integer, float, boolean, date, datetime

---

### Validate Import

Validate all CSV rows against the model schema with provided column mappings.

```{rubric} POST /api/models/{model_name}/import/validate
```

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `model_name` | string | The name of the registered model |

**Headers**

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes | `Bearer <access_token>` |
| `Content-Type` | Yes | `multipart/form-data` |

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `data` | file | Yes | The CSV file |
| `column_mappings` | array | Yes | Column mapping configuration |

**Column Mapping Structure**

```json
{
  "csv_column": "email",
  "model_field": "email",
  "transform": "lowercase"
}
```

Available transforms:
- `none` - No transformation (default)
- `lowercase` - Convert to lowercase
- `uppercase` - Convert to uppercase
- `trim` - Trim whitespace

**Example Request**

```http
POST /admin/api/models/User/import/validate HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "column_mappings": [
    {"csv_column": "email", "model_field": "email", "transform": "lowercase"},
    {"csv_column": "name", "model_field": "name", "transform": "trim"},
    {"csv_column": "is_active", "model_field": "is_active"}
  ]
}
```

**Success Response (200 OK)**

```json
{
  "errors": [
    {"row_number": 5, "field": "email", "value": "invalid-email", "error": "Invalid email format"},
    {"row_number": 8, "field": "is_active", "value": "maybe", "error": "Expected boolean, got 'maybe'"}
  ],
  "valid_count": 98,
  "invalid_count": 2,
  "total_rows": 100,
  "sample_valid_rows": [
    {"email": "john@example.com", "name": "John Doe", "is_active": "true"},
    {"email": "jane@example.com", "name": "Jane Smith", "is_active": "true"}
  ]
}
```

---

### Execute Import

Execute the import with batch processing and error handling.

```{rubric} POST /api/models/{model_name}/import/execute
```

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `model_name` | string | The name of the registered model |

**Headers**

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes | `Bearer <access_token>` |
| `Content-Type` | Yes | `multipart/form-data` |

**Request Body**

Same as validate endpoint - CSV file and column mappings.

**Example Request**

```http
POST /admin/api/models/User/import/execute HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "column_mappings": [
    {"csv_column": "email", "model_field": "email"},
    {"csv_column": "name", "model_field": "name"}
  ]
}
```

**Success Response (200 OK)**

```json
{
  "success": true,
  "message": "Import completed: 98 rows imported, 2 failed",
  "job_id": null,
  "imported_count": 98,
  "failed_count": 2,
  "errors": [
    {"row_number": 5, "field": "email", "value": "duplicate@example.com", "error": "Duplicate entry for key 'email'"},
    {"row_number": 8, "field": "name", "value": null, "error": "Field 'name' is required"}
  ]
}
```

---

## Import Features

### Batch Processing

Imports are processed in batches of 100 rows for memory efficiency:

1. Rows are read and validated in chunks
2. Valid rows are inserted in batches
3. Database commits after each batch
4. Processing continues even if some rows fail

### Type Conversions

The import system automatically converts string values to appropriate types:

| Target Type | Accepted Formats |
|-------------|-----------------|
| integer | `123`, `-456` |
| float | `123.45`, `-67.89`, `.5` |
| boolean | `true`, `false`, `yes`, `no`, `1`, `0` |
| date | `YYYY-MM-DD`, `DD/MM/YYYY`, `MM/DD/YYYY` |
| datetime | ISO 8601, `YYYY-MM-DD HH:MM:SS` |

### Error Handling

The import system handles various error types:

- **Validation errors**: Type mismatches, required fields, format errors
- **Constraint violations**: Unique key violations, foreign key errors
- **Database errors**: Connection issues, transaction failures

Errors are collected per row with:
- Row number (1-indexed, after header)
- Field name that caused the error
- Original value
- Error description

The response includes at most 100 errors to prevent response size issues.

---

## Example: Frontend Import Workflow

```javascript
// Step 1: Preview
const previewResponse = await fetch(
  `/admin/api/models/${modelName}/import/preview`,
  {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: formData  // CSV file
  }
);
const preview = await previewResponse.json();

// Step 2: Build mappings from UI
const mappings = preview.headers.map(header => ({
  csv_column: header,
  model_field: selectedMapping[header],
  transform: selectedTransform[header] || 'none'
}));

// Step 3: Validate
const validateResponse = await fetch(
  `/admin/api/models/${modelName}/import/validate`,
  {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ column_mappings: mappings })
  }
);
const validation = await validateResponse.json();

// Step 4: Execute (if validation looks good)
if (validation.valid_count > 0) {
  const executeResponse = await fetch(
    `/admin/api/models/${modelName}/import/execute`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ column_mappings: mappings })
    }
  );
  const result = await executeResponse.json();
  console.log(`Imported: ${result.imported_count}, Failed: ${result.failed_count}`);
}
```

---

## Import Permissions

Imports require the `models:create` permission. Users with `admin` or `superadmin` roles have this permission by default.

Additionally, the model view must have `can_create = True` (the default).

:::{tip}
Always validate before executing imports, especially for large files. This allows users to review and fix issues before committing data.
:::
