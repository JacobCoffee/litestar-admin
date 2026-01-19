# Raw ASGI Example

This example demonstrates using litestar-admin with raw ASGI middleware and application wrappers.

## Overview

Litestar applications are fully ASGI-compatible, which means they can be:
- Wrapped with custom ASGI middleware
- Composed with other ASGI applications
- Extended using standard ASGI patterns

This example shows several patterns for working with Litestar at the ASGI level.

## ASGI Compatibility

The ASGI (Asynchronous Server Gateway Interface) specification defines a standard interface between async Python web servers and applications. Every Litestar application is an ASGI application, following the signature:

```python
async def app(scope: dict, receive: Callable, send: Callable) -> None:
    ...
```

Where:
- `scope`: A dict containing request metadata (type, path, headers, etc.)
- `receive`: An async callable to receive incoming messages
- `send`: An async callable to send outgoing messages

## What This Example Shows

### 1. Custom ASGI Middleware

Two example middleware classes demonstrate wrapping Litestar apps:

```python
class RequestLoggingMiddleware:
    """Logs all incoming HTTP requests."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "http":
            print(f"[ASGI] {scope['method']} {scope['path']}")
        await self.app(scope, receive, send)
```

### 2. Middleware Composition

Middleware can be stacked in any order:

```python
def create_wrapped_app() -> ASGIApp:
    app = litestar_app
    app = RequestLoggingMiddleware(app)  # Inner layer
    app = TimingMiddleware(app)           # Outer layer
    return app
```

### 3. Lifespan Event Handling

The example demonstrates proper lifespan handling using Litestar's context manager pattern:

```python
@asynccontextmanager
async def lifespan(app: Litestar) -> AsyncIterator[None]:
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()
```

### 4. Direct ASGI Wrapper

The `DirectASGIWrapper` class shows how to create a custom ASGI application that wraps Litestar with fine-grained control over lifespan events.

## Running the Example

### Prerequisites

Ensure you have the required dependencies:

```bash
pip install litestar litestar-admin uvicorn aiosqlite sqlalchemy
```

Or using uv:

```bash
uv pip install litestar litestar-admin uvicorn aiosqlite sqlalchemy
```

### Start the Server

Run directly with Python:

```bash
python app.py
```

Or with uvicorn:

```bash
uvicorn app:app --reload
```

For production:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

### Endpoints

| URL | Description |
|-----|-------------|
| http://127.0.0.1:8000/ | Root endpoint with API info |
| http://127.0.0.1:8000/health | Health check endpoint |
| http://127.0.0.1:8000/admin | Admin panel interface |
| http://127.0.0.1:8000/schema | OpenAPI documentation |

## When to Use This Pattern

Use raw ASGI patterns when you need:

1. **Custom Request Processing**: Add behavior before/after every request at the lowest level.

2. **Third-Party Middleware Integration**: Integrate ASGI middleware from other frameworks (Starlette, FastAPI, etc.).

3. **Multi-Application Composition**: Mount multiple ASGI apps under different paths.

4. **Protocol-Level Access**: Handle WebSocket upgrades, HTTP/2 streams, or custom protocols.

5. **Performance Optimization**: Bypass higher-level abstractions for critical paths.

## Alternative Patterns

For most use cases, prefer Litestar's built-in middleware and hooks:

```python
# Built-in middleware (easier to use)
from litestar.middleware import AbstractMiddleware

class MyMiddleware(AbstractMiddleware):
    async def __call__(self, scope, receive, send):
        # Litestar handles the ASGI details
        ...

app = Litestar(middleware=[MyMiddleware])
```

Use raw ASGI only when Litestar's abstractions don't meet your specific needs.

## Project Structure

```
examples/asgi_raw/
├── app.py          # Main application with ASGI patterns
└── README.md       # This file
```

## Related Resources

- [ASGI Specification](https://asgi.readthedocs.io/)
- [Litestar Middleware Documentation](https://docs.litestar.dev/latest/usage/middleware/)
- [Uvicorn Documentation](https://www.uvicorn.org/)
