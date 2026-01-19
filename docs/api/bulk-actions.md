# Bulk Actions API

The Bulk Actions API provides endpoints for performing batch operations on multiple records at once, including bulk delete and custom actions defined on model views.

Bulk action endpoints are under `/admin/api/models/{model_name}/bulk`.

## Endpoints

### Bulk Delete

Delete multiple records by their primary keys in a single transaction.

```{rubric} POST /api/models/{model_name}/bulk/delete
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
| `ids` | array | Yes | List of primary key values to delete |
| `soft_delete` | boolean | No | If true, perform soft delete (default: false) |

**Example Request**

```http
POST /admin/api/models/User/bulk/delete HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "ids": [5, 7, 12, 15],
  "soft_delete": false
}
```

**Success Response (200 OK)**

```json
{
  "deleted": 4,
  "success": true
}
```

**Response Fields**

| Field | Type | Description |
|-------|------|-------------|
| `deleted` | integer | Number of records successfully deleted |
| `success` | boolean | Whether the operation completed |

**Error Responses**

| Status | Response |
|--------|----------|
| 400 | `{"detail": "IDs array cannot be empty"}` |
| 403 | `{"detail": "Bulk delete is not allowed for model 'User'"}` |
| 403 | `{"detail": "Access denied to model 'User'"}` |
| 404 | `{"detail": "Model 'InvalidModel' not found"}` |

:::{note}
The bulk delete operation is atomic. If any deletion fails, the entire transaction is rolled back and no records are deleted.
:::

---

### Custom Bulk Action

Execute a custom bulk action defined on the model view.

```{rubric} POST /api/models/{model_name}/bulk/{action}
```

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `model_name` | string | The name of the registered model |
| `action` | string | The name of the custom action |

**Headers**

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes | `Bearer <access_token>` |
| `Content-Type` | Yes | `application/json` |

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ids` | array | Yes | List of primary key values to act on |
| `params` | object | No | Additional action-specific parameters |

**Example Request**

```http
POST /admin/api/models/User/bulk/activate HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "ids": [5, 7, 12, 15],
  "params": {
    "send_notification": true
  }
}
```

**Success Response (200 OK)**

```json
{
  "success": true,
  "affected": 4,
  "result": {
    "notifications_sent": 4
  }
}
```

**Response Fields**

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether the action completed successfully |
| `affected` | integer | Number of records affected |
| `result` | object | Action-specific result data |

**Error Responses**

| Status | Response |
|--------|----------|
| 400 | `{"detail": "IDs array cannot be empty"}` |
| 400 | `{"detail": "Bulk action 'activate' failed: Database error"}` |
| 403 | `{"detail": "Access denied to model 'User'"}` |
| 404 | `{"detail": "Model 'InvalidModel' not found"}` |
| 404 | `{"detail": "Bulk action 'invalid_action' not found on model 'User'"}` |

---

## Defining Custom Bulk Actions

Custom bulk actions are defined as class methods on your model view with the `bulk_` prefix:

```python
from litestar_admin import ModelView
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any

class UserAdmin(ModelView, model=User):
    column_list = ["id", "email", "name", "is_active"]

    @classmethod
    async def bulk_activate(
        cls,
        session: AsyncSession,
        ids: list[Any],
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Activate multiple users at once."""
        count = 0
        notifications_sent = 0

        for pk in ids:
            user = await session.get(User, pk)
            if user and not user.is_active:
                user.is_active = True
                count += 1

                # Optional: send notification based on params
                if params.get("send_notification"):
                    await send_activation_email(user)
                    notifications_sent += 1

        await session.flush()

        return {
            "affected": count,
            "notifications_sent": notifications_sent,
        }

    @classmethod
    async def bulk_deactivate(
        cls,
        session: AsyncSession,
        ids: list[Any],
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Deactivate multiple users at once."""
        count = 0

        for pk in ids:
            user = await session.get(User, pk)
            if user and user.is_active:
                user.is_active = False
                count += 1

        await session.flush()
        return {"affected": count}

    @classmethod
    async def bulk_assign_role(
        cls,
        session: AsyncSession,
        ids: list[Any],
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Assign a role to multiple users."""
        role = params.get("role")
        if not role:
            raise ValueError("Role parameter is required")

        count = 0
        for pk in ids:
            user = await session.get(User, pk)
            if user and role not in user.roles:
                user.roles.append(role)
                count += 1

        await session.flush()
        return {"affected": count, "role_assigned": role}
```

### Method Signature

Custom bulk action methods must follow this signature:

```python
@classmethod
async def bulk_{action_name}(
    cls,
    session: AsyncSession,
    ids: list[Any],
    params: dict[str, Any],
) -> dict[str, Any]:
    ...
```

| Argument | Type | Description |
|----------|------|-------------|
| `cls` | type | The model view class |
| `session` | AsyncSession | Database session for queries |
| `ids` | list[Any] | Primary keys of records to act on |
| `params` | dict[str, Any] | Additional parameters from request |

### Return Value

The method should return a dictionary. Special keys:

| Key | Description |
|-----|-------------|
| `affected` | Will be used as the `affected` count in response (otherwise defaults to `len(ids)`) |

Any other keys are included in the `result` object of the response.

---

## Transaction Handling

All bulk operations run within a database transaction:

1. Transaction starts before the operation
2. All changes are made within the transaction
3. On success, transaction is committed
4. On failure, transaction is rolled back

This ensures data consistency - either all records are affected or none are.

```python
@classmethod
async def bulk_process_orders(
    cls,
    session: AsyncSession,
    ids: list[Any],
    params: dict[str, Any],
) -> dict[str, Any]:
    """Process multiple orders - all succeed or all fail."""
    processed = 0

    for pk in ids:
        order = await session.get(Order, pk)
        if order:
            # This might raise an exception
            await process_order(order)
            processed += 1

    await session.flush()

    # If we reach here, all orders were processed successfully
    # If any raised an exception, the entire batch is rolled back
    return {"affected": processed}
```

---

## Permission Requirements

Bulk actions inherit the model view's permission requirements:

| Action | Required Permission |
|--------|---------------------|
| `bulk/delete` | `models:delete` + model's `can_delete=True` |
| `bulk/{custom}` | Model accessibility check via `is_accessible()` |

You can add custom permission checks within your action:

```python
@classmethod
async def bulk_archive(
    cls,
    session: AsyncSession,
    ids: list[Any],
    params: dict[str, Any],
) -> dict[str, Any]:
    # Custom permission check
    user = params.get("_current_user")
    if user and "admin" not in user.roles:
        raise PermissionError("Only admins can archive records")

    # ... perform action
```

---

## Soft Delete

When `soft_delete=True` is passed to the bulk delete endpoint:

1. Records are marked as deleted (typically via a `deleted_at` timestamp)
2. Records remain in the database but are excluded from normal queries
3. Records can potentially be restored later

This only works if the model supports soft deletes (e.g., uses Advanced-Alchemy's `AuditColumns` mixin or similar):

```python
from advanced_alchemy.base import CommonTableAttributes

class User(CommonTableAttributes, Base):
    """User model with soft delete support."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255))
    # deleted_at column is automatically included from CommonTableAttributes
```

---

## Examples

### Frontend Integration

```javascript
// Bulk delete
async function bulkDelete(modelName, ids, softDelete = false) {
  const response = await fetch(
    `/admin/api/models/${modelName}/bulk/delete`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ ids, soft_delete: softDelete })
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }

  return response.json();
}

// Custom bulk action
async function bulkAction(modelName, action, ids, params = {}) {
  const response = await fetch(
    `/admin/api/models/${modelName}/bulk/${action}`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ ids, params })
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }

  return response.json();
}

// Usage examples
await bulkDelete('User', [1, 2, 3]);
await bulkAction('User', 'activate', [5, 6, 7], { send_notification: true });
await bulkAction('User', 'assign_role', [10, 11], { role: 'editor' });
```

### Common Bulk Actions

Here are examples of common bulk actions you might implement:

```python
class ProductAdmin(ModelView, model=Product):
    @classmethod
    async def bulk_publish(cls, session, ids, params):
        """Publish multiple products."""
        count = 0
        for pk in ids:
            product = await session.get(Product, pk)
            if product and not product.is_published:
                product.is_published = True
                product.published_at = datetime.utcnow()
                count += 1
        await session.flush()
        return {"affected": count}

    @classmethod
    async def bulk_set_category(cls, session, ids, params):
        """Move products to a category."""
        category_id = params.get("category_id")
        if not category_id:
            raise ValueError("category_id is required")

        count = 0
        for pk in ids:
            product = await session.get(Product, pk)
            if product:
                product.category_id = category_id
                count += 1
        await session.flush()
        return {"affected": count}

    @classmethod
    async def bulk_apply_discount(cls, session, ids, params):
        """Apply a percentage discount to products."""
        discount = params.get("discount", 0)
        if not 0 <= discount <= 100:
            raise ValueError("Discount must be between 0 and 100")

        multiplier = 1 - (discount / 100)
        count = 0
        original_total = 0
        discounted_total = 0

        for pk in ids:
            product = await session.get(Product, pk)
            if product:
                original_total += product.price
                product.price = round(product.price * multiplier, 2)
                discounted_total += product.price
                count += 1

        await session.flush()
        return {
            "affected": count,
            "original_total": original_total,
            "discounted_total": discounted_total,
            "savings": original_total - discounted_total,
        }
```
