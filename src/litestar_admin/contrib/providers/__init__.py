"""Example data providers for CustomView.

This module provides ready-to-use CustomView implementations for common
data sources that don't use SQLAlchemy models.

Providers:
    - InMemoryView: Simple in-memory data store (useful for testing, caching)
    - JSONFileView: Read/write data from JSON files
    - HTTPAPIView: Fetch data from external HTTP APIs

Example Usage::

    from litestar_admin.contrib.providers import InMemoryView, ColumnDefinition


    class SettingsView(InMemoryView):
        name = "Settings"
        icon = "settings"
        pk_field = "key"
        columns = [
            ColumnDefinition(name="key", type="string", sortable=True),
            ColumnDefinition(name="value", type="string"),
            ColumnDefinition(name="description", type="text"),
        ]

        # Pre-populate with default settings
        _data = {
            "site_name": {
                "key": "site_name",
                "value": "My App",
                "description": "The application name",
            },
        }
"""

from __future__ import annotations

from litestar_admin.contrib.providers.http_api import HTTPAPIView
from litestar_admin.contrib.providers.in_memory import InMemoryView
from litestar_admin.contrib.providers.json_file import JSONFileView

# Re-export common types for convenience
from litestar_admin.views.custom import ColumnDefinition, ListResult

__all__ = [
    "ColumnDefinition",
    "HTTPAPIView",
    "InMemoryView",
    "JSONFileView",
    "ListResult",
]
