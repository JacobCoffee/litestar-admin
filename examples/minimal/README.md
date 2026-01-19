# Minimal litestar-admin Example

This example demonstrates the simplest possible setup for litestar-admin with a single model and default configuration.

## What It Demonstrates

- Basic SQLAlchemy model definition using DeclarativeBase
- ModelView configuration with column lists and permissions
- AdminPlugin setup with minimal configuration
- In-memory SQLite database for easy testing

## Project Structure

```
examples/minimal/
    app.py      # Main application file
    README.md   # This file
```

## Requirements

Install litestar-admin with the required dependencies:

```bash
uv pip install litestar-admin aiosqlite
```

Or if you are developing locally from the repository root:

```bash
uv sync
```

## Running the Example

From the repository root directory:

```bash
uvicorn examples.minimal.app:app --reload
```

Then open your browser to: http://localhost:8000/admin

## Code Overview

### Model Definition

```python
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

### Admin View

```python
class UserAdmin(ModelView, model=User):
    column_list = ["id", "email", "name", "created_at"]
    column_searchable_list = ["email", "name"]
    column_sortable_list = ["id", "email", "name", "created_at"]
```

### Plugin Configuration

```python
app = Litestar(
    plugins=[
        SQLAlchemyPlugin(config=db_config),
        AdminPlugin(config=AdminConfig(
            title="Minimal Admin",
            views=[UserAdmin],
        )),
    ],
)
```

## Next Steps

- See the `examples/full/` directory for a more comprehensive example with authentication
- Check the documentation for advanced configuration options
- Explore RBAC guards for permission-based access control
