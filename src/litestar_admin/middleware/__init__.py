"""Middleware components for the admin panel.

This module provides middleware for various cross-cutting concerns
such as rate limiting and request tracking.

Example:
    Using rate limit middleware::

        from litestar import Litestar
        from litestar_admin.middleware import (
            RateLimitConfig,
            RateLimitMiddleware,
            create_rate_limit_middleware,
        )

        # Option 1: Use factory function for custom config
        config = RateLimitConfig(
            requests_per_minute=100,
            requests_per_hour=2000,
        )
        app = Litestar(
            middleware=[create_rate_limit_middleware(config)],
        )

        # Option 2: Use default configuration
        app = Litestar(
            middleware=[RateLimitMiddleware],
        )
"""

from __future__ import annotations

from litestar_admin.middleware.ratelimit import (
    InMemoryRateLimitStore,
    RateLimitConfig,
    RateLimitMiddleware,
    RateLimitStore,
    create_rate_limit_middleware,
    get_client_ip,
    get_rate_limit_key,
)

__all__ = [
    # Configuration
    "RateLimitConfig",
    # Storage
    "InMemoryRateLimitStore",
    "RateLimitStore",
    # Middleware
    "RateLimitMiddleware",
    "create_rate_limit_middleware",
    # Helpers
    "get_client_ip",
    "get_rate_limit_key",
]
