# API Reference

This section provides complete API documentation for litestar-admin, including both the REST API and Python API.

```{toctree}
:maxdepth: 1
:hidden:

authentication
models
dashboard
export
bulk-actions
```

## REST API

Complete REST API reference for litestar-admin. All endpoints are prefixed with `/admin` by default (configurable via `AdminConfig.base_url`).

### Base URL

```
{your-app-url}/admin/api
```

### Authentication

Most endpoints require authentication. Include the access token in the `Authorization` header:

```text
Authorization: Bearer <access_token>
```

Alternatively, tokens can be sent via cookies if configured in your auth backend.

### Response Format

All responses use JSON format. Successful responses return the requested data directly. Error responses follow this structure:

```json
{
  "detail": "Error message describing what went wrong",
  "status_code": 400
}
```

### Quick Reference

#### Authentication Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Authenticate with credentials |
| POST | `/api/auth/logout` | End current session |
| POST | `/api/auth/refresh` | Refresh access token |
| GET | `/api/auth/me` | Get current user info |

#### Model Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/models` | List registered models |
| GET | `/api/models/{model}` | List records |
| POST | `/api/models/{model}` | Create record |
| GET | `/api/models/{model}/{id}` | Get single record |
| PUT | `/api/models/{model}/{id}` | Full update |
| PATCH | `/api/models/{model}/{id}` | Partial update |
| DELETE | `/api/models/{model}/{id}` | Delete record |
| GET | `/api/models/{model}/schema` | Get JSON schema |

#### Dashboard Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard/stats` | Get model statistics |
| GET | `/api/dashboard/activity` | Get recent activity |

#### Export Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/models/{model}/export` | Export all records |
| POST | `/api/models/{model}/bulk/export` | Export selected records |

#### Bulk Action Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/models/{model}/bulk/delete` | Bulk delete records |
| POST | `/api/models/{model}/bulk/{action}` | Custom bulk action |

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created (for POST creating new records) |
| 400 | Bad Request (invalid input) |
| 401 | Unauthorized (not authenticated) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Not Found (model or record doesn't exist) |
| 422 | Validation Error |
| 429 | Too Many Requests (rate limited) |
| 500 | Internal Server Error |

### Rate Limiting

When rate limiting is enabled, responses include these headers:

```text
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640000000
```

If the limit is exceeded, you'll receive a 429 status code:

```json
{
  "error": "Too Many Requests",
  "retry_after": 60
}
```

### OpenAPI Schema

The API is fully documented with OpenAPI 3.0. Access the interactive documentation at:

- **Swagger UI**: `/schema/swagger`
- **ReDoc**: `/schema/redoc`
- **OpenAPI JSON**: `/schema/openapi.json`

These are provided by Litestar's built-in OpenAPI support.

---

## Python API

### Core Classes

| Class | Description |
|-------|-------------|
| {class}`~litestar_admin.AdminPlugin` | Main plugin implementing Litestar's InitPluginProtocol |
| {class}`~litestar_admin.AdminConfig` | Configuration dataclass for the admin panel |
| {class}`~litestar_admin.ModelView` | Base class for model views with model binding |
| {class}`~litestar_admin.BaseModelView` | Foundation class for model views |
| {class}`~litestar_admin.ModelRegistry` | Registry for managing model views |
| {class}`~litestar_admin.AdminService` | Service layer for CRUD operations |

### Authentication

| Class | Description |
|-------|-------------|
| {class}`~litestar_admin.auth.JWTAuthBackend` | JWT-based authentication backend |
| {class}`~litestar_admin.auth.JWTConfig` | Configuration for JWT authentication |
| {class}`~litestar_admin.auth.AuthBackend` | Protocol for authentication backends |
| {class}`~litestar_admin.auth.AdminUser` | Protocol for admin user objects |

### Guards & Permissions

| Item | Description |
|------|-------------|
| {class}`~litestar_admin.guards.Permission` | Enum of available permissions |
| {class}`~litestar_admin.guards.Role` | Enum of available roles |
| {class}`~litestar_admin.guards.PermissionGuard` | Guard that checks permissions |
| {class}`~litestar_admin.guards.RoleGuard` | Guard that checks roles |
| {func}`~litestar_admin.guards.require_permission` | Factory for permission guards |
| {func}`~litestar_admin.guards.require_role` | Factory for role guards |

### Audit Logging

| Class | Description |
|-------|-------------|
| {class}`~litestar_admin.audit.AuditAction` | Enum of auditable actions |
| {class}`~litestar_admin.audit.AuditEntry` | Single audit log entry |
| {class}`~litestar_admin.audit.AuditLogger` | Protocol for audit backends |
| {class}`~litestar_admin.audit.InMemoryAuditLogger` | In-memory audit logger |
| {func}`~litestar_admin.audit.audit_admin_action` | Helper to create audit entries |

### Rate Limiting

| Class | Description |
|-------|-------------|
| {class}`~litestar_admin.middleware.RateLimitMiddleware` | Rate limiting middleware |
| {class}`~litestar_admin.middleware.RateLimitConfig` | Rate limit configuration |
| {class}`~litestar_admin.middleware.InMemoryRateLimitStore` | In-memory rate limit store |

---

## Module Documentation

### litestar_admin

```{eval-rst}
.. automodule:: litestar_admin
   :members:
   :undoc-members:
   :show-inheritance:
```

### litestar_admin.plugin

```{eval-rst}
.. automodule:: litestar_admin.plugin
   :members:
   :undoc-members:
   :show-inheritance:
```

### litestar_admin.config

```{eval-rst}
.. automodule:: litestar_admin.config
   :members:
   :undoc-members:
   :show-inheritance:
```

### litestar_admin.registry

```{eval-rst}
.. automodule:: litestar_admin.registry
   :members:
   :undoc-members:
   :show-inheritance:
```

### litestar_admin.service

```{eval-rst}
.. automodule:: litestar_admin.service
   :members:
   :undoc-members:
   :show-inheritance:
```

### litestar_admin.views

```{eval-rst}
.. automodule:: litestar_admin.views
   :members:
   :undoc-members:
   :show-inheritance:
```

```{eval-rst}
.. automodule:: litestar_admin.views.base
   :members:
   :undoc-members:
   :show-inheritance:
```

```{eval-rst}
.. automodule:: litestar_admin.views.model
   :members:
   :undoc-members:
   :show-inheritance:
```

### litestar_admin.auth

```{eval-rst}
.. automodule:: litestar_admin.auth
   :members:
   :undoc-members:
   :show-inheritance:
```

```{eval-rst}
.. automodule:: litestar_admin.auth.protocols
   :members:
   :undoc-members:
   :show-inheritance:
```

```{eval-rst}
.. automodule:: litestar_admin.auth.jwt
   :members:
   :undoc-members:
   :show-inheritance:
```

### litestar_admin.guards

```{eval-rst}
.. automodule:: litestar_admin.guards
   :members:
   :undoc-members:
   :show-inheritance:
```

```{eval-rst}
.. automodule:: litestar_admin.guards.permissions
   :members:
   :undoc-members:
   :show-inheritance:
```

### litestar_admin.audit

```{eval-rst}
.. automodule:: litestar_admin.audit
   :members:
   :undoc-members:
   :show-inheritance:
```

```{eval-rst}
.. automodule:: litestar_admin.audit.logger
   :members:
   :undoc-members:
   :show-inheritance:
```

### litestar_admin.middleware

```{eval-rst}
.. automodule:: litestar_admin.middleware
   :members:
   :undoc-members:
   :show-inheritance:
```

```{eval-rst}
.. automodule:: litestar_admin.middleware.ratelimit
   :members:
   :undoc-members:
   :show-inheritance:
```
