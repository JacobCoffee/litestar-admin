"""Redis-based storage backends for the admin panel.

This module provides Redis implementations for rate limiting, session storage,
and caching. These are optional alternatives to the in-memory defaults,
recommended for production deployments with multiple workers or processes.

Benefits of Redis storage:
- Persistence across application restarts
- Shared state across multiple workers/processes
- Distributed rate limiting in load-balanced environments
- TTL-based automatic expiration (no manual cleanup needed)

Usage:
    Set the REDIS_URL environment variable and import the stores::

        export REDIS_URL="redis://localhost:6379/0"

    Then in your application::

        from examples.full.redis_store import (
            create_redis_rate_limit_store,
            create_redis_session_store,
            create_redis_cache,
        )

        # Create stores with automatic fallback to in-memory if Redis unavailable
        rate_limit_store = await create_redis_rate_limit_store()
        session_store = await create_redis_session_store()
        cache = await create_redis_cache()
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from litestar_admin import get_logger

if TYPE_CHECKING:
    from redis.asyncio import Redis

__all__ = [
    "RedisRateLimitStore",
    "RedisSessionStore",
    "RedisCache",
    "create_redis_rate_limit_store",
    "create_redis_session_store",
    "create_redis_cache",
    "get_redis_client",
    "REDIS_URL",
]

# Redis configuration from environment
# Set this to connect to Redis, e.g., "redis://localhost:6379/0"
# If not set, all stores will gracefully fall back to in-memory implementations
REDIS_URL: str | None = os.environ.get("REDIS_URL")

logger = get_logger(__name__)


# ==============================================================================
# Redis Client Factory
# ==============================================================================


async def get_redis_client(url: str | None = None) -> Redis | None:
    """Create and test a Redis async client connection.

    This function attempts to create a Redis client and verify connectivity.
    If Redis is not available or the connection fails, it returns None,
    allowing the application to gracefully fall back to in-memory storage.

    Args:
        url: Redis connection URL. If None, uses REDIS_URL environment variable.
             Format: redis://[[username]:[password]@]host[:port][/database]

    Returns:
        A connected Redis client if successful, None otherwise.

    Example:
        Basic usage::

            client = await get_redis_client("redis://localhost:6379/0")
            if client:
                await client.set("key", "value")
                value = await client.get("key")
    """
    redis_url = url or REDIS_URL

    if not redis_url:
        logger.debug("REDIS_URL not configured, Redis client not created")
        return None

    try:
        # Import redis.asyncio only when needed (optional dependency)
        from redis.asyncio import Redis as RedisClient

        client: Redis = RedisClient.from_url(
            redis_url,
            decode_responses=True,  # Return strings instead of bytes
            socket_connect_timeout=5.0,  # Connection timeout in seconds
            socket_timeout=5.0,  # Operation timeout in seconds
        )

        # Test the connection
        await client.ping()
        logger.info("Redis connection established", url=redis_url.split("@")[-1])  # Log without credentials
        return client

    except ImportError:
        logger.warning(
            "redis package not installed. Install with: pip install redis[hiredis]",
            hint="Run: uv add redis[hiredis]",
        )
        return None

    except Exception as e:
        logger.warning(
            "Redis connection failed, falling back to in-memory storage",
            error=str(e),
            url=redis_url.split("@")[-1] if redis_url else None,
        )
        return None


# ==============================================================================
# Redis Rate Limit Store
# ==============================================================================


class RedisRateLimitStore:
    """Redis implementation of the rate limit store.

    This implementation uses Redis sorted sets for efficient sliding window
    rate limiting. It supports automatic key expiration and is suitable for
    distributed deployments with multiple workers or processes.

    Advantages over in-memory storage:
    - Shared state across all workers/processes
    - Persistence across application restarts
    - Automatic cleanup via Redis TTL
    - Atomic operations for accurate counting

    Attributes:
        client: The Redis async client.
        key_prefix: Prefix for all rate limit keys in Redis.
        minute_window: Duration of the minute window in seconds.
        hour_window: Duration of the hour window in seconds.

    Example:
        Basic usage::

            client = await get_redis_client("redis://localhost:6379/0")
            store = RedisRateLimitStore(client)
            count = await store.increment("192.168.1.1", "minute")
            remaining = await store.get_remaining("192.168.1.1", "minute", 60)
    """

    def __init__(
        self,
        client: Redis,
        key_prefix: str = "ratelimit",
        minute_window: int = 60,
        hour_window: int = 3600,
    ) -> None:
        """Initialize the Redis rate limit store.

        Args:
            client: The Redis async client.
            key_prefix: Prefix for all rate limit keys in Redis.
            minute_window: Duration of the minute window in seconds.
            hour_window: Duration of the hour window in seconds.
        """
        self._client = client
        self._key_prefix = key_prefix
        self._minute_window = minute_window
        self._hour_window = hour_window

    def _get_window_duration(self, window: str) -> int:
        """Get the duration for a named window.

        Args:
            window: The window name ("minute" or "hour").

        Returns:
            The window duration in seconds.
        """
        if window == "minute":
            return self._minute_window
        if window == "hour":
            return self._hour_window
        return self._minute_window

    def _make_key(self, key: str, window: str) -> str:
        """Create a Redis key for the given rate limit key and window.

        Args:
            key: The rate limit key (e.g., client IP).
            window: The time window identifier.

        Returns:
            A fully qualified Redis key.
        """
        return f"{self._key_prefix}:{window}:{key}"

    async def get_count(self, key: str, window: str) -> int:
        """Get the current request count for a key within a time window.

        Uses a sliding window approach with sorted sets. Only counts requests
        within the current time window.

        Args:
            key: The rate limit key (e.g., client IP or user ID).
            window: The time window identifier ("minute" or "hour").

        Returns:
            The current request count for the key in the window.
        """
        redis_key = self._make_key(key, window)
        window_duration = self._get_window_duration(window)
        now = time.time()
        window_start = now - window_duration

        # Remove expired entries and count remaining
        await self._client.zremrangebyscore(redis_key, 0, window_start)
        count = await self._client.zcard(redis_key)
        return int(count)

    async def increment(self, key: str, window: str) -> int:
        """Increment the request count for a key within a time window.

        Adds the current timestamp to a sorted set. Old entries are automatically
        cleaned up based on the window duration.

        Args:
            key: The rate limit key (e.g., client IP or user ID).
            window: The time window identifier ("minute" or "hour").

        Returns:
            The new request count after incrementing.
        """
        redis_key = self._make_key(key, window)
        window_duration = self._get_window_duration(window)
        now = time.time()
        window_start = now - window_duration

        # Use a pipeline for atomic operations
        async with self._client.pipeline(transaction=True) as pipe:
            # Remove expired entries
            pipe.zremrangebyscore(redis_key, 0, window_start)
            # Add current request with timestamp as score
            # Use timestamp + microseconds to ensure uniqueness
            pipe.zadd(redis_key, {f"{now}": now})
            # Set TTL to auto-expire the key
            pipe.expire(redis_key, window_duration + 60)  # Extra buffer
            # Get the count
            pipe.zcard(redis_key)
            results = await pipe.execute()

        return int(results[-1])  # zcard result is last

    async def reset(self, key: str) -> None:
        """Reset all rate limit counters for a key.

        Args:
            key: The rate limit key to reset.
        """
        minute_key = self._make_key(key, "minute")
        hour_key = self._make_key(key, "hour")
        await self._client.delete(minute_key, hour_key)

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

        For Redis, this returns when the oldest entry in the window will expire.

        Args:
            key: The rate limit key (e.g., client IP or user ID).
            window: The time window identifier ("minute" or "hour").

        Returns:
            Unix timestamp when the window resets.
        """
        redis_key = self._make_key(key, window)
        window_duration = self._get_window_duration(window)

        # Get the oldest entry in the current window
        oldest = await self._client.zrange(redis_key, 0, 0, withscores=True)

        if oldest:
            oldest_timestamp = oldest[0][1]
            return int(oldest_timestamp + window_duration)

        # No entries, window resets after duration from now
        return int(time.time()) + window_duration

    async def close(self) -> None:
        """Close the Redis connection."""
        await self._client.close()

    async def ping(self) -> bool:
        """Check if Redis is connected.

        Returns:
            True if connected, False otherwise.
        """
        try:
            await self._client.ping()
            return True
        except Exception:
            return False


# ==============================================================================
# Redis Session Store
# ==============================================================================


@dataclass
class SessionData:
    """Data structure for session storage."""

    user_id: str
    email: str
    role: str
    created_at: float
    last_accessed: float
    extra: dict[str, Any] | None = None


class RedisSessionStore:
    """Redis implementation for session/token storage.

    This provides a Redis-backed session store as an alternative to in-memory
    token storage. Sessions are stored as Redis hashes with automatic TTL-based
    expiration.

    Benefits:
    - Sessions persist across application restarts
    - Shared across multiple workers/processes
    - Automatic expiration via Redis TTL
    - Efficient session lookups and updates

    Attributes:
        client: The Redis async client.
        key_prefix: Prefix for all session keys in Redis.
        default_ttl: Default session TTL in seconds (1 hour).

    Example:
        Basic usage::

            client = await get_redis_client("redis://localhost:6379/0")
            store = RedisSessionStore(client)

            # Store a session
            await store.set("token123", {"user_id": "1", "email": "user@example.com"})

            # Retrieve a session
            session = await store.get("token123")

            # Delete a session (logout)
            await store.delete("token123")
    """

    def __init__(
        self,
        client: Redis,
        key_prefix: str = "session",
        default_ttl: int = 3600,  # 1 hour
    ) -> None:
        """Initialize the Redis session store.

        Args:
            client: The Redis async client.
            key_prefix: Prefix for all session keys in Redis.
            default_ttl: Default session TTL in seconds.
        """
        self._client = client
        self._key_prefix = key_prefix
        self._default_ttl = default_ttl

    def _make_key(self, token: str) -> str:
        """Create a Redis key for the given token.

        Args:
            token: The session token.

        Returns:
            A fully qualified Redis key.
        """
        return f"{self._key_prefix}:{token}"

    async def get(self, token: str) -> dict[str, Any] | None:
        """Retrieve session data for a token.

        Args:
            token: The session token.

        Returns:
            Session data as a dictionary, or None if not found.
        """
        key = self._make_key(token)
        data = await self._client.hgetall(key)

        if not data:
            return None

        # Update last accessed time
        await self._client.hset(key, "last_accessed", str(time.time()))

        return data

    async def set(
        self,
        token: str,
        data: dict[str, Any],
        ttl: int | None = None,
    ) -> None:
        """Store session data for a token.

        Args:
            token: The session token.
            data: Session data to store.
            ttl: Optional TTL in seconds (uses default if not provided).
        """
        key = self._make_key(token)
        ttl = ttl or self._default_ttl

        # Add timestamps
        data["created_at"] = data.get("created_at", str(time.time()))
        data["last_accessed"] = str(time.time())

        # Store as hash and set expiration
        await self._client.hset(key, mapping=data)
        await self._client.expire(key, ttl)

    async def delete(self, token: str) -> bool:
        """Delete a session.

        Args:
            token: The session token to delete.

        Returns:
            True if the session was deleted, False if it didn't exist.
        """
        key = self._make_key(token)
        result = await self._client.delete(key)
        return result > 0

    async def exists(self, token: str) -> bool:
        """Check if a session exists.

        Args:
            token: The session token to check.

        Returns:
            True if the session exists.
        """
        key = self._make_key(token)
        return await self._client.exists(key) > 0

    async def refresh(self, token: str, ttl: int | None = None) -> bool:
        """Refresh the TTL for a session.

        Args:
            token: The session token.
            ttl: New TTL in seconds (uses default if not provided).

        Returns:
            True if the session was refreshed, False if it didn't exist.
        """
        key = self._make_key(token)
        ttl = ttl or self._default_ttl

        if await self._client.exists(key):
            await self._client.expire(key, ttl)
            await self._client.hset(key, "last_accessed", str(time.time()))
            return True

        return False

    async def get_all_user_sessions(self, user_id: str) -> list[str]:
        """Get all session tokens for a user.

        Note: This requires scanning keys, which can be slow with many sessions.
        Consider using a separate index for user sessions in production.

        Args:
            user_id: The user ID to find sessions for.

        Returns:
            List of session tokens for the user.
        """
        pattern = f"{self._key_prefix}:*"
        tokens: list[str] = []

        async for key in self._client.scan_iter(match=pattern, count=100):
            session_user_id = await self._client.hget(key, "user_id")
            if session_user_id == user_id:
                # Extract token from key
                token = key.replace(f"{self._key_prefix}:", "")
                tokens.append(token)

        return tokens

    async def delete_all_user_sessions(self, user_id: str) -> int:
        """Delete all sessions for a user (logout from all devices).

        Args:
            user_id: The user ID to delete sessions for.

        Returns:
            Number of sessions deleted.
        """
        tokens = await self.get_all_user_sessions(user_id)
        if tokens:
            keys = [self._make_key(token) for token in tokens]
            return await self._client.delete(*keys)
        return 0

    async def close(self) -> None:
        """Close the Redis connection."""
        await self._client.close()


# ==============================================================================
# Redis Cache
# ==============================================================================


class RedisCache:
    """Redis implementation for general-purpose caching.

    This provides a simple Redis-backed cache for storing arbitrary data
    with optional TTL. Useful for caching expensive database queries,
    API responses, or computed values.

    Attributes:
        client: The Redis async client.
        key_prefix: Prefix for all cache keys in Redis.
        default_ttl: Default cache TTL in seconds (5 minutes).

    Example:
        Basic usage::

            client = await get_redis_client("redis://localhost:6379/0")
            cache = RedisCache(client)

            # Cache a value
            await cache.set("user:1:profile", {"name": "John", "email": "john@example.com"})

            # Retrieve cached value
            profile = await cache.get("user:1:profile")

            # Delete cached value
            await cache.delete("user:1:profile")

        With TTL::

            # Cache for 10 minutes
            await cache.set("expensive_query", result, ttl=600)
    """

    def __init__(
        self,
        client: Redis,
        key_prefix: str = "cache",
        default_ttl: int = 300,  # 5 minutes
    ) -> None:
        """Initialize the Redis cache.

        Args:
            client: The Redis async client.
            key_prefix: Prefix for all cache keys in Redis.
            default_ttl: Default cache TTL in seconds.
        """
        self._client = client
        self._key_prefix = key_prefix
        self._default_ttl = default_ttl

    def _make_key(self, key: str) -> str:
        """Create a Redis key for the given cache key.

        Args:
            key: The cache key.

        Returns:
            A fully qualified Redis key.
        """
        return f"{self._key_prefix}:{key}"

    async def get(self, key: str) -> Any | None:
        """Retrieve a cached value.

        Args:
            key: The cache key.

        Returns:
            The cached value, or None if not found.
        """
        import json

        redis_key = self._make_key(key)
        data = await self._client.get(redis_key)

        if data is None:
            return None

        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return data  # Return as-is if not JSON

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:
        """Store a value in the cache.

        Args:
            key: The cache key.
            value: The value to cache (must be JSON serializable).
            ttl: Optional TTL in seconds (uses default if not provided).
        """
        import json

        redis_key = self._make_key(key)
        ttl = ttl or self._default_ttl

        # Serialize to JSON
        if isinstance(value, (dict, list)):
            data = json.dumps(value)
        else:
            data = str(value)

        await self._client.setex(redis_key, ttl, data)

    async def delete(self, key: str) -> bool:
        """Delete a cached value.

        Args:
            key: The cache key to delete.

        Returns:
            True if the key was deleted, False if it didn't exist.
        """
        redis_key = self._make_key(key)
        result = await self._client.delete(redis_key)
        return result > 0

    async def exists(self, key: str) -> bool:
        """Check if a key exists in the cache.

        Args:
            key: The cache key to check.

        Returns:
            True if the key exists.
        """
        redis_key = self._make_key(key)
        return await self._client.exists(redis_key) > 0

    async def clear_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern.

        Args:
            pattern: Glob-style pattern to match (e.g., "user:*").

        Returns:
            Number of keys deleted.
        """
        full_pattern = f"{self._key_prefix}:{pattern}"
        keys: list[str] = []

        async for key in self._client.scan_iter(match=full_pattern, count=100):
            keys.append(key)

        if keys:
            return await self._client.delete(*keys)

        return 0

    async def get_or_set(
        self,
        key: str,
        factory: Any,
        ttl: int | None = None,
    ) -> Any:
        """Get a cached value or compute and cache it.

        This is useful for caching expensive computations. If the key exists,
        its value is returned. Otherwise, the factory is called to compute
        the value, which is then cached and returned.

        Args:
            key: The cache key.
            factory: A callable that returns the value to cache.
                    Can be sync or async.
            ttl: Optional TTL in seconds.

        Returns:
            The cached or computed value.

        Example:
            Cache a database query::

                async def get_user_stats(user_id: str) -> dict:
                    # Expensive query
                    return await db.execute(...)


                stats = await cache.get_or_set(
                    f"user:{user_id}:stats",
                    lambda: get_user_stats(user_id),
                    ttl=300,
                )
        """
        import asyncio

        value = await self.get(key)
        if value is not None:
            return value

        # Compute the value
        if asyncio.iscoroutinefunction(factory):
            value = await factory()
        elif callable(factory):
            result = factory()
            if asyncio.iscoroutine(result):
                value = await result
            else:
                value = result
        else:
            value = factory

        await self.set(key, value, ttl)
        return value

    async def close(self) -> None:
        """Close the Redis connection."""
        await self._client.close()


# ==============================================================================
# Factory Functions with Fallback
# ==============================================================================


async def create_redis_rate_limit_store(
    url: str | None = None,
) -> RedisRateLimitStore | None:
    """Create a Redis rate limit store with automatic fallback.

    If Redis is not available, returns None. The caller should fall back to
    InMemoryRateLimitStore in this case.

    Args:
        url: Redis connection URL. Uses REDIS_URL env var if not provided.

    Returns:
        A RedisRateLimitStore if Redis is available, None otherwise.

    Example:
        With automatic fallback::

            from litestar_admin.middleware import InMemoryRateLimitStore

            redis_store = await create_redis_rate_limit_store()
            rate_limit_store = redis_store or InMemoryRateLimitStore()
    """
    client = await get_redis_client(url)
    if client:
        return RedisRateLimitStore(client)
    return None


async def create_redis_session_store(
    url: str | None = None,
    default_ttl: int = 3600,
) -> RedisSessionStore | None:
    """Create a Redis session store with automatic fallback.

    If Redis is not available, returns None. The caller should fall back to
    an in-memory session store in this case.

    Args:
        url: Redis connection URL. Uses REDIS_URL env var if not provided.
        default_ttl: Default session TTL in seconds.

    Returns:
        A RedisSessionStore if Redis is available, None otherwise.
    """
    client = await get_redis_client(url)
    if client:
        return RedisSessionStore(client, default_ttl=default_ttl)
    return None


async def create_redis_cache(
    url: str | None = None,
    default_ttl: int = 300,
) -> RedisCache | None:
    """Create a Redis cache with automatic fallback.

    If Redis is not available, returns None. The caller should implement
    caching without Redis or skip caching entirely.

    Args:
        url: Redis connection URL. Uses REDIS_URL env var if not provided.
        default_ttl: Default cache TTL in seconds.

    Returns:
        A RedisCache if Redis is available, None otherwise.
    """
    client = await get_redis_client(url)
    if client:
        return RedisCache(client, default_ttl=default_ttl)
    return None
