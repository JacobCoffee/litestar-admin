# Framework Bridge Examples

This directory contains examples demonstrating how to integrate `litestar-admin` with other Python web frameworks using ASGI mounting patterns.

## Overview

Since Litestar is a fully compliant ASGI framework, it can be mounted as a sub-application within other ASGI frameworks like Starlette or FastAPI. This allows you to add a powerful admin panel to existing applications without a full framework migration.

## Examples

### 1. Starlette Mount (`starlette_mount.py`)

Demonstrates mounting litestar-admin within a Starlette application.

```bash
# Install dependencies
pip install starlette litestar litestar-admin sqlalchemy[asyncio] aiosqlite uvicorn

# Run the example
uvicorn examples.framework_bridge.starlette_mount:app --reload
```

**Key points:**
- Uses Starlette's `Mount` class to embed the Litestar admin app
- Shares SQLAlchemy async engine between Starlette and admin
- Starlette manages the application lifecycle (startup/shutdown)
- Admin panel available at `/admin`

### 2. FastAPI Integration (`fastapi_integration.py`)

Demonstrates mounting litestar-admin within a FastAPI application.

```bash
# Install dependencies
pip install fastapi litestar litestar-admin sqlalchemy[asyncio] aiosqlite uvicorn

# Run the example
uvicorn examples.framework_bridge.fastapi_integration:app --reload
```

**Key points:**
- Uses FastAPI's `mount()` method to embed the Litestar admin app
- Shows Pydantic models coexisting with SQLAlchemy models
- FastAPI OpenAPI docs remain fully functional at `/docs`
- Admin panel available at `/admin`
- Demonstrates multiple admin panel mounts for different use cases

## ASGI Mounting Patterns

### Basic Pattern

All ASGI frameworks support mounting other ASGI applications as sub-applications:

```python
# Starlette
from starlette.routing import Mount
routes = [Mount("/admin", app=litestar_admin_app)]

# FastAPI
fastapi_app.mount("/admin", litestar_admin_app)
```

### Important Considerations

1. **Base URL Configuration**: When mounting Litestar at a sub-path, set `base_url="/"` in `AdminConfig` since the mount point handles the prefix.

2. **Lifecycle Management**: The parent application typically manages startup/shutdown. Consider disabling Litestar's own lifecycle hooks to avoid duplication:
   ```python
   Litestar(
       plugins=[AdminPlugin(config=config)],
       on_startup=[],
       on_shutdown=[],
   )
   ```

3. **Database Session Sharing**: Create the SQLAlchemy engine at the module level and share it between frameworks. Both can use the same `async_sessionmaker`.

4. **Static Files**: Litestar serves admin static files automatically. Ensure no route conflicts with the parent application.

5. **Authentication**: If using auth, you may need to bridge authentication between frameworks or use a shared session/token system.

## When to Use Framework Bridging

**Good use cases:**
- Adding admin functionality to an existing FastAPI/Starlette application
- Gradual migration from FastAPI to Litestar
- Teams familiar with FastAPI who want litestar-admin's features
- Microservices where admin is one component

**When to use native Litestar instead:**
- New applications (start with Litestar from day one)
- When you need deep integration with Litestar features (guards, dependencies)
- Performance-critical admin operations
- Full-stack Litestar applications

## Architecture Diagram

```
+--------------------------------------------------+
|              Parent ASGI Application              |
|              (FastAPI / Starlette)                |
|                                                   |
|  +----------------+     +----------------------+  |
|  | Main Routes    |     | Mounted at /admin    |  |
|  | /api/v1/*      |     |                      |  |
|  | /docs          |     |  +----------------+  |  |
|  | /health        |     |  | Litestar App   |  |  |
|  +----------------+     |  | AdminPlugin    |  |  |
|                         |  | - Controllers  |  |  |
|                         |  | - Static Files |  |  |
|                         |  +----------------+  |  |
|                         +----------------------+  |
|                                                   |
|  +----------------------------------------------+ |
|  |         Shared SQLAlchemy Engine              | |
|  |   async_sessionmaker / AsyncEngine            | |
|  +----------------------------------------------+ |
+--------------------------------------------------+
```

## Caveats and Limitations

1. **Request Context**: Request objects differ between frameworks. Litestar uses its own `Request` class within the admin panel.

2. **Dependency Injection**: Each framework has its own DI system. Dependencies don't automatically transfer across mount boundaries.

3. **Middleware**: Parent application middleware applies to mounted apps, but Litestar-specific middleware must be configured on the Litestar app.

4. **Error Handling**: Errors within the mounted admin app are handled by Litestar's error handlers, not the parent framework's.

5. **OpenAPI Schema**: The mounted Litestar app's OpenAPI schema is separate from FastAPI's. Admin API endpoints won't appear in FastAPI's `/docs`.

6. **Testing**: Integration tests may need to handle both frameworks' test clients depending on what's being tested.

## Performance Considerations

ASGI mounting adds minimal overhead. The ASGI interface passes requests directly to the sub-application without extra serialization. For most admin use cases, this overhead is negligible.

## Further Reading

- [ASGI Specification](https://asgi.readthedocs.io/)
- [Litestar Documentation](https://docs.litestar.dev/)
- [Starlette Routing](https://www.starlette.io/routing/)
- [FastAPI Sub Applications](https://fastapi.tiangolo.com/advanced/sub-applications/)
