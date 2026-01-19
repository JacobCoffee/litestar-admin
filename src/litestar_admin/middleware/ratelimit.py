"""Rate limiting middleware for the admin panel API.

This module provides middleware for throttling requests to prevent abuse.
It supports configurable rate limits per minute and per hour, with burst
allowances and multiple storage backends.

Example:
    Configure rate limiting with the admin plugin::

        from litestar_admin.middleware import RateLimitMiddleware, RateLimitConfig

        config = RateLimitConfig(
            requests_per_minute=60,
            requests_per_hour=1000,
            burst_size=10,
        )
        app = Litestar(middleware=[RateLimitMiddleware])
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Protocol, cast, runtime_checkable

from litestar.middleware import AbstractMiddleware
from litestar.status_codes import HTTP_429_TOO_MANY_REQUESTS

if TYPE_CHECKING:
    from collections.abc import Callable

    from litestar.connection import ASGIConnection
    from litestar.types import ASGIApp, Message, Receive, Scope, Send

__all__ = [
    "InMemoryRateLimitStore",
    "RateLimitConfig",
    "RateLimitMiddleware",
    "RateLimitStore",
    "get_client_ip",
    "get_rate_limit_key",
]


# ==============================================================================
# Configuration
# ==============================================================================


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting middleware.

    Attributes:
        requests_per_minute: Maximum requests allowed per minute (default: 60).
        requests_per_hour: Maximum requests allowed per hour (default: 1000).
        burst_size: Number of requests allowed in a short burst (default: 10).
        key_func: Optional custom function to extract rate limit key from connection.
        exclude_paths: List of path prefixes to exclude from rate limiting.
        include_paths: If set, only these paths will be rate limited (overrides exclude_paths).
        enabled: Whether rate limiting is enabled (default: True).
        headers_enabled: Whether to add rate limit headers to responses (default: True).

    Example:
        Basic configuration::

            config = RateLimitConfig(
                requests_per_minute=100,
                requests_per_hour=2000,
            )

        With custom key function::

            def custom_key(connection: ASGIConnection) -> str:
                return connection.user.id if connection.user else get_client_ip(connection)


            config = RateLimitConfig(key_func=custom_key)

        Exclude specific paths::

            config = RateLimitConfig(
                exclude_paths=["/admin/api/health", "/admin/api/status"],
            )
    """

    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_size: int = 10
    key_func: Callable[[ASGIConnection[Any, Any, Any, Any]], str] | None = None
    exclude_paths: list[str] = field(default_factory=list)
    include_paths: list[str] | None = None
    enabled: bool = True
    headers_enabled: bool = True

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if self.requests_per_minute < 1:
            msg = "requests_per_minute must be at least 1"
            raise ValueError(msg)

        if self.requests_per_hour < 1:
            msg = "requests_per_hour must be at least 1"
            raise ValueError(msg)

        if self.burst_size < 1:
            msg = "burst_size must be at least 1"
            raise ValueError(msg)

        if self.requests_per_hour < self.requests_per_minute:
            msg = "requests_per_hour must be greater than or equal to requests_per_minute"
            raise ValueError(msg)


# ==============================================================================
# Storage Protocol
# ==============================================================================


@runtime_checkable
class RateLimitStore(Protocol):
    """Protocol for rate limit storage backends.

    Implementations of this protocol handle storing and retrieving
    rate limit counts for different clients and time windows.

    The storage backend should handle automatic cleanup of expired entries.
    """

    async def get_count(self, key: str, window: str) -> int:
        """Get the current request count for a key within a time window.

        Args:
            key: The rate limit key (e.g., client IP or user ID).
            window: The time window identifier (e.g., "minute" or "hour").

        Returns:
            The current request count for the key in the window.
        """
        ...

    async def increment(self, key: str, window: str) -> int:
        """Increment the request count for a key within a time window.

        Args:
            key: The rate limit key (e.g., client IP or user ID).
            window: The time window identifier (e.g., "minute" or "hour").

        Returns:
            The new request count after incrementing.
        """
        ...

    async def reset(self, key: str) -> None:
        """Reset all rate limit counters for a key.

        Args:
            key: The rate limit key to reset.
        """
        ...

    async def get_remaining(self, key: str, window: str, limit: int) -> int:
        """Get the remaining requests allowed for a key in a time window.

        Args:
            key: The rate limit key (e.g., client IP or user ID).
            window: The time window identifier (e.g., "minute" or "hour").
            limit: The maximum requests allowed in the window.

        Returns:
            The number of remaining requests allowed.
        """
        ...

    async def get_reset_time(self, key: str, window: str) -> int:
        """Get the Unix timestamp when the rate limit window resets.

        Args:
            key: The rate limit key (e.g., client IP or user ID).
            window: The time window identifier (e.g., "minute" or "hour").

        Returns:
            Unix timestamp when the window resets.
        """
        ...


# ==============================================================================
# In-Memory Store Implementation
# ==============================================================================


@dataclass
class _WindowData:
    """Internal data structure for tracking requests in a time window."""

    count: int = 0
    window_start: float = field(default_factory=time.time)


class InMemoryRateLimitStore:
    """In-memory implementation of the rate limit store.

    This implementation uses a dictionary to store request counts with
    automatic cleanup of expired entries. It is thread-safe and suitable
    for single-process deployments.

    For multi-process or distributed deployments, consider using a
    Redis-backed implementation instead.

    Attributes:
        minute_window: Duration of the minute window in seconds.
        hour_window: Duration of the hour window in seconds.
        cleanup_interval: Interval between automatic cleanups in seconds.

    Example:
        Basic usage::

            store = InMemoryRateLimitStore()
            count = await store.increment("192.168.1.1", "minute")
            remaining = await store.get_remaining("192.168.1.1", "minute", 60)
    """

    minute_window: int = 60
    hour_window: int = 3600
    cleanup_interval: int = 300  # 5 minutes

    def __init__(
        self,
        minute_window: int = 60,
        hour_window: int = 3600,
        cleanup_interval: int = 300,
    ) -> None:
        """Initialize the in-memory rate limit store.

        Args:
            minute_window: Duration of the minute window in seconds.
            hour_window: Duration of the hour window in seconds.
            cleanup_interval: Interval between automatic cleanups in seconds.
        """
        self.minute_window = minute_window
        self.hour_window = hour_window
        self.cleanup_interval = cleanup_interval

        # Store: {key: {window: _WindowData}}
        self._data: dict[str, dict[str, _WindowData]] = defaultdict(dict)
        self._lock = asyncio.Lock()
        self._last_cleanup = time.time()

    def _get_window_duration(self, window: str) -> int:
        """Get the duration for a named window.

        Args:
            window: The window name ("minute" or "hour").

        Returns:
            The window duration in seconds.
        """
        if window == "minute":
            return self.minute_window
        if window == "hour":
            return self.hour_window
        return self.minute_window  # Default to minute

    def _is_window_expired(self, window_data: _WindowData, window_duration: int) -> bool:
        """Check if a time window has expired.

        Args:
            window_data: The window data to check.
            window_duration: The window duration in seconds.

        Returns:
            True if the window has expired.
        """
        return time.time() - window_data.window_start >= window_duration

    async def _maybe_cleanup(self) -> None:
        """Perform cleanup if the cleanup interval has passed."""
        current_time = time.time()
        if current_time - self._last_cleanup < self.cleanup_interval:
            return

        async with self._lock:
            # Double-check after acquiring lock
            if current_time - self._last_cleanup < self.cleanup_interval:
                return

            self._last_cleanup = current_time
            keys_to_remove: list[str] = []

            for key, windows in self._data.items():
                windows_to_remove: list[str] = []
                for window_name, window_data in windows.items():
                    window_duration = self._get_window_duration(window_name)
                    if self._is_window_expired(window_data, window_duration):
                        windows_to_remove.append(window_name)

                for window_name in windows_to_remove:
                    del windows[window_name]

                if not windows:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del self._data[key]

    async def get_count(self, key: str, window: str) -> int:
        """Get the current request count for a key within a time window.

        Args:
            key: The rate limit key (e.g., client IP or user ID).
            window: The time window identifier ("minute" or "hour").

        Returns:
            The current request count for the key in the window.
        """
        await self._maybe_cleanup()

        async with self._lock:
            if key not in self._data or window not in self._data[key]:
                return 0

            window_data = self._data[key][window]
            window_duration = self._get_window_duration(window)

            if self._is_window_expired(window_data, window_duration):
                return 0

            return window_data.count

    async def increment(self, key: str, window: str) -> int:
        """Increment the request count for a key within a time window.

        If the window has expired, it is reset before incrementing.

        Args:
            key: The rate limit key (e.g., client IP or user ID).
            window: The time window identifier ("minute" or "hour").

        Returns:
            The new request count after incrementing.
        """
        await self._maybe_cleanup()

        async with self._lock:
            window_duration = self._get_window_duration(window)

            if key not in self._data:
                self._data[key] = {}

            if window not in self._data[key]:
                self._data[key][window] = _WindowData(count=1, window_start=time.time())
                return 1

            window_data = self._data[key][window]

            if self._is_window_expired(window_data, window_duration):
                # Reset window
                self._data[key][window] = _WindowData(count=1, window_start=time.time())
                return 1

            window_data.count += 1
            return window_data.count

    async def reset(self, key: str) -> None:
        """Reset all rate limit counters for a key.

        Args:
            key: The rate limit key to reset.
        """
        async with self._lock:
            if key in self._data:
                del self._data[key]

    async def get_remaining(self, key: str, window: str, limit: int) -> int:
        """Get the remaining requests allowed for a key in a time window.

        Args:
            key: The rate limit key (e.g., client IP or user ID).
            window: The time window identifier ("minute" or "hour").
            limit: The maximum requests allowed in the window.

        Returns:
            The number of remaining requests allowed (minimum 0).
        """
        count = await self.get_count(key, window)
        return max(0, limit - count)

    async def get_reset_time(self, key: str, window: str) -> int:
        """Get the Unix timestamp when the rate limit window resets.

        Args:
            key: The rate limit key (e.g., client IP or user ID).
            window: The time window identifier ("minute" or "hour").

        Returns:
            Unix timestamp when the window resets.
        """
        async with self._lock:
            if key not in self._data or window not in self._data[key]:
                return int(time.time()) + self._get_window_duration(window)

            window_data = self._data[key][window]
            window_duration = self._get_window_duration(window)
            return int(window_data.window_start + window_duration)

    def clear(self) -> None:
        """Clear all stored rate limit data.

        This method is primarily useful for testing.
        """
        self._data.clear()

    @property
    def keys(self) -> list[str]:
        """Return a list of all tracked keys.

        This property is primarily useful for debugging and testing.

        Returns:
            List of all keys being tracked.
        """
        return list(self._data.keys())


# ==============================================================================
# Helper Functions
# ==============================================================================


def get_client_ip(connection: ASGIConnection[Any, Any, Any, Any]) -> str:
    """Extract the client IP address from a connection.

    This function checks common proxy headers (X-Forwarded-For, X-Real-IP)
    before falling back to the direct client address.

    Args:
        connection: The ASGI connection.

    Returns:
        The client IP address, or "unknown" if it cannot be determined.

    Example:
        Get client IP from request::

            @get("/test")
            async def handler(request: Request) -> str:
                ip = get_client_ip(request)
                return f"Your IP: {ip}"
    """
    # Check X-Forwarded-For header (most common proxy header)
    forwarded_for = connection.headers.get("x-forwarded-for")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs: client, proxy1, proxy2, ...
        # The first IP is the original client
        return forwarded_for.split(",")[0].strip()

    # Check X-Real-IP header (used by nginx)
    real_ip = connection.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    # Fall back to direct client connection
    if connection.client and connection.client.host:
        return connection.client.host

    return "unknown"


def get_rate_limit_key(connection: ASGIConnection[Any, Any, Any, Any], config: RateLimitConfig) -> str:
    """Generate a rate limit key for a connection.

    If a custom key function is provided in the config, it is used.
    Otherwise, the client IP address is used as the key.

    Args:
        connection: The ASGI connection.
        config: The rate limit configuration.

    Returns:
        A string key for rate limiting.

    Example:
        Generate key with custom function::

            def user_key(conn: ASGIConnection) -> str:
                if hasattr(conn, "user") and conn.user:
                    return f"user:{conn.user.id}"
                return f"ip:{get_client_ip(conn)}"


            config = RateLimitConfig(key_func=user_key)
            key = get_rate_limit_key(request, config)
    """
    if config.key_func is not None:
        return config.key_func(connection)

    return get_client_ip(connection)


# ==============================================================================
# Middleware
# ==============================================================================


class RateLimitMiddleware(AbstractMiddleware):
    """Litestar middleware for request rate limiting.

    This middleware throttles requests based on client IP or a custom key.
    It supports per-minute and per-hour limits with burst allowances.

    When rate limits are exceeded, the middleware returns a 429 Too Many Requests
    response with standard rate limit headers.

    Attributes:
        config: The rate limit configuration.
        store: The storage backend for rate limit counts.

    Example:
        Basic usage with default configuration::

            from litestar import Litestar
            from litestar_admin.middleware import RateLimitMiddleware, RateLimitConfig

            app = Litestar(
                middleware=[RateLimitMiddleware],
            )

        With custom configuration::

            config = RateLimitConfig(
                requests_per_minute=100,
                requests_per_hour=2000,
                exclude_paths=["/health"],
            )
            store = InMemoryRateLimitStore()

            app = Litestar(
                middleware=[
                    create_rate_limit_middleware(config, store),
                ],
            )
    """

    scopes: ClassVar[set[str]] = {"http"}

    def __init__(
        self,
        app: ASGIApp,
        config: RateLimitConfig | None = None,
        store: RateLimitStore | None = None,
    ) -> None:
        """Initialize the rate limit middleware.

        Args:
            app: The ASGI application.
            config: Rate limit configuration. Uses defaults if not provided.
            store: Storage backend for rate limits. Uses InMemoryRateLimitStore if not provided.
        """
        super().__init__(app)
        self._config = config or RateLimitConfig()
        self._store = store or InMemoryRateLimitStore()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process the request and apply rate limiting.

        Args:
            scope: The ASGI scope.
            receive: The ASGI receive callable.
            send: The ASGI send callable.
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if not self._config.enabled:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # Check path exclusions/inclusions
        if not self._should_rate_limit(path):
            await self.app(scope, receive, send)
            return

        # Get rate limit key from scope
        key = self._get_key_from_scope(scope)

        # Check rate limits
        is_limited, limit_info = await self._check_rate_limit(key)

        if is_limited:
            # Return 429 response
            await self._send_rate_limit_response(send, limit_info)
            return

        # Increment counters
        await self._store.increment(key, "minute")
        await self._store.increment(key, "hour")

        # Get updated remaining counts for headers
        minute_remaining = await self._store.get_remaining(key, "minute", self._config.requests_per_minute)
        hour_remaining = await self._store.get_remaining(key, "hour", self._config.requests_per_hour)
        reset_time = await self._store.get_reset_time(key, "minute")

        # Wrap send to add rate limit headers
        if self._config.headers_enabled:
            send = self._wrap_send_with_headers(send, minute_remaining, hour_remaining, reset_time)

        await self.app(scope, receive, send)

    def _should_rate_limit(self, path: str) -> bool:
        """Determine if a path should be rate limited.

        Args:
            path: The request path.

        Returns:
            True if the path should be rate limited.
        """
        # If include_paths is set, only those paths are rate limited
        if self._config.include_paths is not None:
            return any(path.startswith(p) for p in self._config.include_paths)

        # Otherwise, check exclude_paths
        return not any(path.startswith(p) for p in self._config.exclude_paths)

    def _get_key_from_scope(self, scope: Scope) -> str:
        """Extract rate limit key from ASGI scope.

        If a custom key function is provided in the config, a connection
        wrapper is created and passed to it. Otherwise, the client IP
        is extracted directly from the scope.

        Args:
            scope: The ASGI scope.

        Returns:
            A string key for rate limiting.
        """
        if self._config.key_func is not None:
            # Create connection wrapper for custom key function
            from litestar.connection import ASGIConnection

            connection = ASGIConnection(scope)
            return self._config.key_func(connection)

        # Extract IP directly from scope
        return self._get_client_ip_from_scope(scope)

    def _get_client_ip_from_scope(self, scope: Scope) -> str:
        """Extract client IP address from ASGI scope.

        Args:
            scope: The ASGI scope.

        Returns:
            The client IP address, or "unknown" if it cannot be determined.
        """
        # Get headers as a dict for easier access
        headers = dict(scope.get("headers", []))

        # Check X-Forwarded-For header
        forwarded_for = headers.get(b"x-forwarded-for")
        if forwarded_for:
            return forwarded_for.decode("utf-8").split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = headers.get(b"x-real-ip")
        if real_ip:
            return real_ip.decode("utf-8").strip()

        # Fall back to direct client connection
        client = scope.get("client")
        if client:
            return client[0] if isinstance(client, tuple) else "unknown"

        return "unknown"

    async def _check_rate_limit(self, key: str) -> tuple[bool, dict[str, Any]]:
        """Check if a key has exceeded rate limits.

        Args:
            key: The rate limit key.

        Returns:
            Tuple of (is_limited, limit_info).
        """
        minute_count = await self._store.get_count(key, "minute")
        hour_count = await self._store.get_count(key, "hour")
        reset_time = await self._store.get_reset_time(key, "minute")

        limit_info = {
            "limit": self._config.requests_per_minute,
            "remaining": max(0, self._config.requests_per_minute - minute_count),
            "reset": reset_time,
            "retry_after": max(0, reset_time - int(time.time())),
        }

        # Check minute limit
        if minute_count >= self._config.requests_per_minute:
            return True, limit_info

        # Check hour limit
        if hour_count >= self._config.requests_per_hour:
            hour_reset_time = await self._store.get_reset_time(key, "hour")
            limit_info = {
                "limit": self._config.requests_per_hour,
                "remaining": 0,
                "reset": hour_reset_time,
                "retry_after": max(0, hour_reset_time - int(time.time())),
            }
            return True, limit_info

        return False, limit_info

    async def _send_rate_limit_response(self, send: Send, limit_info: dict[str, Any]) -> None:
        """Send a 429 Too Many Requests response.

        Args:
            send: The ASGI send callable.
            limit_info: Information about the rate limit.
        """
        import json

        body = json.dumps({"error": "Too Many Requests", "retry_after": limit_info["retry_after"]}).encode("utf-8")

        headers: list[tuple[bytes, bytes]] = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode()),
            (b"X-RateLimit-Limit", str(limit_info["limit"]).encode()),
            (b"X-RateLimit-Remaining", str(limit_info["remaining"]).encode()),
            (b"X-RateLimit-Reset", str(limit_info["reset"]).encode()),
            (b"Retry-After", str(limit_info["retry_after"]).encode()),
        ]

        await send(
            cast(
                "Message",
                {
                    "type": "http.response.start",
                    "status": HTTP_429_TOO_MANY_REQUESTS,
                    "headers": headers,
                },
            )
        )
        await send(
            cast(
                "Message",
                {
                    "type": "http.response.body",
                    "body": body,
                },
            )
        )

    def _wrap_send_with_headers(
        self,
        send: Send,
        minute_remaining: int,
        hour_remaining: int,
        reset_time: int,
    ) -> Send:
        """Wrap the send callable to add rate limit headers.

        Args:
            send: The original ASGI send callable.
            minute_remaining: Remaining requests in the minute window.
            hour_remaining: Remaining requests in the hour window.
            reset_time: Unix timestamp when the window resets.

        Returns:
            A wrapped send callable that adds headers.
        """
        # Use the lower of the two remaining values
        remaining = min(minute_remaining, hour_remaining)

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(
                    [
                        (b"x-ratelimit-limit", str(self._config.requests_per_minute).encode()),
                        (b"x-ratelimit-remaining", str(remaining).encode()),
                        (b"x-ratelimit-reset", str(reset_time).encode()),
                    ]
                )
                updated_message = cast("Message", {**message, "headers": headers})
                await send(updated_message)
            else:
                await send(message)

        return send_wrapper


def create_rate_limit_middleware(
    config: RateLimitConfig | None = None,
    store: RateLimitStore | None = None,
) -> type[RateLimitMiddleware]:
    """Create a rate limit middleware class with pre-configured settings.

    This factory function allows you to create a middleware class with
    specific configuration that can be passed directly to Litestar's
    middleware list.

    Args:
        config: Rate limit configuration. Uses defaults if not provided.
        store: Storage backend for rate limits. Uses InMemoryRateLimitStore if not provided.

    Returns:
        A configured RateLimitMiddleware class.

    Example:
        Create middleware with custom settings::

            config = RateLimitConfig(requests_per_minute=100)
            store = InMemoryRateLimitStore()

            app = Litestar(
                middleware=[create_rate_limit_middleware(config, store)],
            )
    """
    _config = config or RateLimitConfig()
    _store = store or InMemoryRateLimitStore()

    class ConfiguredRateLimitMiddleware(RateLimitMiddleware):
        def __init__(self, app: ASGIApp) -> None:
            super().__init__(app, config=_config, store=_store)

    return ConfiguredRateLimitMiddleware
