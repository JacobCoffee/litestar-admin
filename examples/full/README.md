# Full Admin Demo

A comprehensive example application demonstrating all features of litestar-admin.

## Features Demonstrated

This example showcases:

- **SQLAlchemy 2.x Integration**: Async models with proper relationships
- **JWT Authentication**: Secure token-based auth with JWTAuthBackend
- **Role-Based Access Control (RBAC)**: Four-tier role system (viewer, editor, admin, superadmin)
- **ModelView Configurations**:
  - Column display, search, and sort options
  - Form customization with excluded fields
  - Permission controls (can_create, can_edit, can_delete)
  - Category grouping in sidebar
  - Custom on_model_change hooks
- **Rate Limiting**: Built-in request rate limiting (with optional Redis backend)
- **Redis Integration** (Optional):
  - Distributed rate limiting across workers
  - Persistent session storage
  - General-purpose caching
- **Automatic Data Seeding**: Demo data created on startup

## Project Structure

```
examples/full/
├── models.py      # SQLAlchemy 2.x models (User, Article, Tag)
├── auth.py        # JWT authentication setup
├── views.py       # ModelView configurations
├── redis_store.py # Redis storage backends (rate limiting, sessions, cache)
├── app.py         # Main Litestar application
└── README.md      # This file
```

## Models

### User
- Fields: id, email, name, password_hash, role, is_active, created_at, updated_at
- Roles: viewer, editor, admin, superadmin
- Relationships: One-to-many with Article

### Article
- Fields: id, title, content, status, author_id, created_at, published_at
- Status: draft, review, published, archived
- Relationships: Many-to-one with User, Many-to-many with Tag

### Tag
- Fields: id, name, slug
- Relationships: Many-to-many with Article

## Running the Example

### Prerequisites

1. Install the package with JWT support:
   ```bash
   uv sync --all-extras
   ```

2. Or install just the required extras:
   ```bash
   uv add "litestar-admin[jwt]"
   ```

### Start the Application

Using Litestar CLI:
```bash
litestar --app examples.full.app:app run --reload
```

Using uvicorn:
```bash
uvicorn examples.full.app:app --reload
```

Using the Makefile (from project root):
```bash
make dev
# Then in another terminal:
litestar --app examples.full.app:app run --reload
```

### Start with Redis (Optional)

Redis enables distributed rate limiting, persistent sessions, and caching.
Without Redis, the application uses in-memory storage (suitable for single-worker deployments).

1. Start Redis:
   ```bash
   # macOS
   brew install redis && brew services start redis

   # Linux
   apt-get install redis-server && systemctl start redis

   # Docker
   docker run -d -p 6379:6379 redis:alpine
   ```

2. Install the Redis Python package:
   ```bash
   pip install redis[hiredis]
   # or with uv:
   uv add redis[hiredis]
   ```

3. Run with Redis enabled:
   ```bash
   REDIS_URL=redis://localhost:6379/0 litestar --app examples.full.app:app run --reload
   ```

4. Verify Redis is connected by checking the health endpoint:
   ```bash
   curl http://localhost:8000/health
   # Response: {"status": "healthy", "storage": {"database": "connected", "redis": "connected"}}
   ```

### Access the Application

- **Root API**: http://localhost:8000/
- **Admin Panel**: http://localhost:8000/admin
- **API Docs**: http://localhost:8000/schema

## Default Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@example.com | admin |
| Editor | editor@example.com | editor |
| Viewer | viewer@example.com | viewer |

## Role Permissions

| Permission | Viewer | Editor | Admin | Superadmin |
|------------|--------|--------|-------|------------|
| dashboard:view | Yes | Yes | Yes | Yes |
| models:read | Yes | Yes | Yes | Yes |
| models:write | No | Yes | Yes | Yes |
| models:delete | No | No | Yes | Yes |
| models:export | No | No | Yes | Yes |
| users:manage | No | No | Yes | Yes |
| audit:view | No | No | Yes | Yes |
| settings:manage | No | No | No | Yes |

## API Endpoints

### Authentication

```
POST /admin/api/auth/login
Content-Type: application/json

{
  "email": "admin@example.com",
  "password": "admin"
}
```

Response:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": "3600"
}
```

### Using the Token

Include the access token in subsequent requests:
```
Authorization: Bearer eyJ...
```

### Model API Endpoints

All model endpoints require authentication:

- `GET /admin/api/models/{model_name}` - List records
- `GET /admin/api/models/{model_name}/{id}` - Get record
- `POST /admin/api/models/{model_name}` - Create record
- `PUT /admin/api/models/{model_name}/{id}` - Update record
- `DELETE /admin/api/models/{model_name}/{id}` - Delete record

## Customization Examples

### Custom Model Hook

The ArticleAdmin view demonstrates automatic published_at timestamp:

```python
@classmethod
async def on_model_change(
    cls,
    data: dict[str, Any],
    record: Any | None,
    *,
    is_create: bool,
) -> dict[str, Any]:
    if data.get("status") == ArticleStatus.PUBLISHED:
        if "published_at" not in data:
            data["published_at"] = datetime.now(timezone.utc)
    return data
```

### Restricting Delete Operations

The UserAdmin view shows how to disable delete (use deactivation instead):

```python
class UserAdmin(ModelView, model=User):
    can_delete = False  # Users should be deactivated, not deleted
```

### Category Grouping

Group related views in the sidebar:

```python
class ArticleAdmin(ModelView, model=Article):
    category = "Content"

class TagAdmin(ModelView, model=Tag):
    category = "Content"
```

## Redis Integration

This example includes optional Redis support for distributed rate limiting, persistent sessions, and caching.

### Why Use Redis?

| Feature | In-Memory (Default) | Redis |
|---------|---------------------|-------|
| Rate Limiting | Per-process only | Shared across workers |
| Sessions | Lost on restart | Persist across restarts |
| Cache | Per-process only | Shared across workers |
| Multi-worker | Limited | Full support |

### Redis Storage Backends

The `redis_store.py` module provides three Redis-backed storage classes:

#### RedisRateLimitStore

Implements the `RateLimitStore` protocol for distributed rate limiting:

```python
from examples.full.redis_store import create_redis_rate_limit_store

# Create store (returns None if Redis unavailable)
store = await create_redis_rate_limit_store("redis://localhost:6379/0")

if store:
    # Increment request count for a client
    count = await store.increment("192.168.1.1", "minute")

    # Check remaining requests
    remaining = await store.get_remaining("192.168.1.1", "minute", limit=100)
```

#### RedisSessionStore

Provides session/token storage with automatic expiration:

```python
from examples.full.redis_store import create_redis_session_store

store = await create_redis_session_store("redis://localhost:6379/0")

if store:
    # Store a session
    await store.set("token123", {
        "user_id": "1",
        "email": "user@example.com",
        "role": "admin"
    })

    # Retrieve session
    session = await store.get("token123")

    # Delete session (logout)
    await store.delete("token123")

    # Logout from all devices
    await store.delete_all_user_sessions("1")
```

#### RedisCache

General-purpose caching with TTL support:

```python
from examples.full.redis_store import create_redis_cache

cache = await create_redis_cache("redis://localhost:6379/0")

if cache:
    # Cache a value (default TTL: 5 minutes)
    await cache.set("user:1:profile", {"name": "John", "email": "john@example.com"})

    # Cache with custom TTL (10 minutes)
    await cache.set("expensive_query", result, ttl=600)

    # Get or compute pattern
    stats = await cache.get_or_set(
        "user:1:stats",
        lambda: expensive_database_query(),
        ttl=300
    )
```

### Configuration

Redis is configured via the `REDIS_URL` environment variable:

```bash
# Local Redis (default port, database 0)
export REDIS_URL="redis://localhost:6379/0"

# Remote Redis with password
export REDIS_URL="redis://:password@redis.example.com:6379/0"

# Redis with username and password
export REDIS_URL="redis://username:password@redis.example.com:6379/0"
```

### Graceful Fallback

All Redis stores are optional. If Redis is not available:

1. The application logs a warning message
2. In-memory storage is used automatically
3. The application continues to work normally

This makes local development easy (no Redis required) while supporting production deployments with Redis.

## Security Notes

This example uses simplified password hashing (SHA-256) for demonstration purposes.
**For production use:**

- Use bcrypt, argon2, or similar secure password hashing
- Store the JWT secret key in environment variables
- Enable `cookie_secure=True` for HTTPS
- Use a proper database (PostgreSQL recommended)
- Configure appropriate CORS settings
- Use Redis for multi-worker deployments

## Troubleshooting

### Database Issues

If you encounter database issues, delete the `demo.db` file and restart:
```bash
rm demo.db
litestar --app examples.full.app:app run --reload
```

### Import Errors

Ensure you're running from the project root and have installed dependencies:
```bash
cd /path/to/litestar-admin
uv sync --all-extras
```

### Token Expiration

Access tokens expire after 1 hour. Use the refresh endpoint or login again:
```
POST /admin/api/auth/refresh
Authorization: Bearer {refresh_token}
```
