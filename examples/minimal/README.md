# Minimal Example

The smallest working litestar-admin setup. Define models, add the plugin, let auto-discovery do the rest.

## Run It

```bash
uv sync  # if developing from the repo
uvicorn examples.minimal.app:app --reload
```

Open http://localhost:8000/admin.

## What's Happening

There's no `ModelView` subclass anywhere in `app.py`. The plugin finds the `User` model through SQLAlchemy's declarative registry and generates a view automatically — all columns visible, string columns searchable, auto-increment PKs excluded from the create form.

When you need to customize how a model appears (column lists, permissions, form widgets, lifecycle hooks), create a `ModelView` subclass. See `examples/full/` for that.
