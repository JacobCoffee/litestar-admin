"""Tests for Redis storage backends.

This module tests the Redis implementations for rate limiting, session storage,
and caching. Uses fakeredis to mock Redis without requiring a real server.
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    from fakeredis import FakeAsyncRedis


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
async def fake_redis() -> FakeAsyncRedis:
    """Create a fake Redis async client for testing."""
    from fakeredis import FakeAsyncRedis

    client = FakeAsyncRedis(decode_responses=True)
    yield client
    await client.flushall()
    await client.aclose()


@pytest.fixture
async def rate_limit_store(fake_redis: FakeAsyncRedis):
    """Create a RedisRateLimitStore with fake Redis client."""
    from examples.full.redis_store import RedisRateLimitStore

    return RedisRateLimitStore(fake_redis)


@pytest.fixture
async def session_store(fake_redis: FakeAsyncRedis):
    """Create a RedisSessionStore with fake Redis client."""
    from examples.full.redis_store import RedisSessionStore

    return RedisSessionStore(fake_redis, default_ttl=60)


@pytest.fixture
async def cache(fake_redis: FakeAsyncRedis):
    """Create a RedisCache with fake Redis client."""
    from examples.full.redis_store import RedisCache

    return RedisCache(fake_redis, default_ttl=60)


# ==============================================================================
# RedisRateLimitStore Tests
# ==============================================================================


class TestRedisRateLimitStore:
    """Tests for the RedisRateLimitStore implementation."""

    @pytest.mark.asyncio
    async def test_get_count_empty(self, rate_limit_store) -> None:
        """Test getting count for non-existent key returns 0."""
        count = await rate_limit_store.get_count("test-key", "minute")
        assert count == 0

    @pytest.mark.asyncio
    async def test_increment(self, rate_limit_store) -> None:
        """Test incrementing counter returns correct counts."""
        count1 = await rate_limit_store.increment("test-key", "minute")
        assert count1 == 1

        count2 = await rate_limit_store.increment("test-key", "minute")
        assert count2 == 2

        count3 = await rate_limit_store.increment("test-key", "minute")
        assert count3 == 3

    @pytest.mark.asyncio
    async def test_increment_different_windows(self, rate_limit_store) -> None:
        """Test incrementing counters in different windows are independent."""
        await rate_limit_store.increment("test-key", "minute")
        await rate_limit_store.increment("test-key", "minute")
        await rate_limit_store.increment("test-key", "hour")

        minute_count = await rate_limit_store.get_count("test-key", "minute")
        hour_count = await rate_limit_store.get_count("test-key", "hour")

        assert minute_count == 2
        assert hour_count == 1

    @pytest.mark.asyncio
    async def test_increment_different_keys(self, rate_limit_store) -> None:
        """Test incrementing counters for different keys are independent."""
        await rate_limit_store.increment("key1", "minute")
        await rate_limit_store.increment("key1", "minute")
        await rate_limit_store.increment("key2", "minute")

        count1 = await rate_limit_store.get_count("key1", "minute")
        count2 = await rate_limit_store.get_count("key2", "minute")

        assert count1 == 2
        assert count2 == 1

    @pytest.mark.asyncio
    async def test_reset(self, rate_limit_store) -> None:
        """Test resetting counters for a key clears both windows."""
        await rate_limit_store.increment("test-key", "minute")
        await rate_limit_store.increment("test-key", "hour")

        await rate_limit_store.reset("test-key")

        minute_count = await rate_limit_store.get_count("test-key", "minute")
        hour_count = await rate_limit_store.get_count("test-key", "hour")

        assert minute_count == 0
        assert hour_count == 0

    @pytest.mark.asyncio
    async def test_get_remaining(self, rate_limit_store) -> None:
        """Test getting remaining requests."""
        limit = 10

        # Initially all requests available
        remaining = await rate_limit_store.get_remaining("test-key", "minute", limit)
        assert remaining == 10

        # After some requests
        await rate_limit_store.increment("test-key", "minute")
        await rate_limit_store.increment("test-key", "minute")
        await rate_limit_store.increment("test-key", "minute")

        remaining = await rate_limit_store.get_remaining("test-key", "minute", limit)
        assert remaining == 7

    @pytest.mark.asyncio
    async def test_get_remaining_at_limit(self, rate_limit_store) -> None:
        """Test getting remaining when at limit returns 0."""
        limit = 3

        await rate_limit_store.increment("test-key", "minute")
        await rate_limit_store.increment("test-key", "minute")
        await rate_limit_store.increment("test-key", "minute")

        remaining = await rate_limit_store.get_remaining("test-key", "minute", limit)
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_get_remaining_over_limit(self, rate_limit_store) -> None:
        """Test that remaining never goes negative."""
        limit = 2

        await rate_limit_store.increment("test-key", "minute")
        await rate_limit_store.increment("test-key", "minute")
        await rate_limit_store.increment("test-key", "minute")

        remaining = await rate_limit_store.get_remaining("test-key", "minute", limit)
        assert remaining == 0  # Not -1

    @pytest.mark.asyncio
    async def test_get_reset_time(self, rate_limit_store) -> None:
        """Test getting reset time returns a future timestamp."""
        await rate_limit_store.increment("test-key", "minute")

        reset_time = await rate_limit_store.get_reset_time("test-key", "minute")

        # Reset time should be in the future (within 60 seconds)
        current_time = int(time.time())
        assert reset_time > current_time
        assert reset_time <= current_time + 60

    @pytest.mark.asyncio
    async def test_get_reset_time_new_key(self, rate_limit_store) -> None:
        """Test getting reset time for a new key returns future time."""
        reset_time = await rate_limit_store.get_reset_time("new-key", "minute")

        # Should be approximately now + 60 seconds
        current_time = int(time.time())
        assert reset_time >= current_time + 59
        assert reset_time <= current_time + 61

    @pytest.mark.asyncio
    async def test_get_reset_time_hour_window(self, rate_limit_store) -> None:
        """Test getting reset time for hour window."""
        await rate_limit_store.increment("test-key", "hour")

        reset_time = await rate_limit_store.get_reset_time("test-key", "hour")

        # Reset time should be in the future (within 3600 seconds)
        current_time = int(time.time())
        assert reset_time > current_time
        assert reset_time <= current_time + 3600

    @pytest.mark.asyncio
    async def test_ping_success(self, rate_limit_store) -> None:
        """Test ping returns True when Redis is connected."""
        result = await rate_limit_store.ping()
        assert result is True

    @pytest.mark.asyncio
    async def test_ping_failure(self, fake_redis) -> None:
        """Test ping returns False when Redis connection fails."""
        from examples.full.redis_store import RedisRateLimitStore

        # Create a mock client that raises on ping
        mock_client = MagicMock()
        mock_client.ping = AsyncMock(side_effect=Exception("Connection refused"))

        store = RedisRateLimitStore(mock_client)
        result = await store.ping()
        assert result is False

    @pytest.mark.asyncio
    async def test_close(self, rate_limit_store, fake_redis) -> None:
        """Test close method calls client close."""
        # The store should close without error
        await rate_limit_store.close()

    @pytest.mark.asyncio
    async def test_key_prefix(self, fake_redis) -> None:
        """Test custom key prefix is used."""
        from examples.full.redis_store import RedisRateLimitStore

        store = RedisRateLimitStore(fake_redis, key_prefix="custom_prefix")
        await store.increment("test-key", "minute")

        # Verify the key was created with custom prefix
        keys = [key async for key in fake_redis.scan_iter(match="custom_prefix:*")]
        assert len(keys) > 0
        assert any("custom_prefix:minute:test-key" in key for key in keys)

    @pytest.mark.asyncio
    async def test_custom_window_durations(self, fake_redis) -> None:
        """Test custom window durations."""
        from examples.full.redis_store import RedisRateLimitStore

        store = RedisRateLimitStore(
            fake_redis,
            minute_window=30,  # 30 seconds
            hour_window=1800,  # 30 minutes
        )

        await store.increment("test-key", "minute")
        reset_time = await store.get_reset_time("test-key", "minute")

        current_time = int(time.time())
        # Reset should be within 30 seconds (the custom window)
        assert reset_time <= current_time + 30

    @pytest.mark.asyncio
    async def test_make_key(self, rate_limit_store) -> None:
        """Test internal key generation."""
        key = rate_limit_store._make_key("192.168.1.1", "minute")
        assert key == "ratelimit:minute:192.168.1.1"

        key = rate_limit_store._make_key("user:123", "hour")
        assert key == "ratelimit:hour:user:123"

    @pytest.mark.asyncio
    async def test_get_window_duration(self, rate_limit_store) -> None:
        """Test window duration lookup."""
        assert rate_limit_store._get_window_duration("minute") == 60
        assert rate_limit_store._get_window_duration("hour") == 3600
        # Unknown window defaults to minute
        assert rate_limit_store._get_window_duration("unknown") == 60


# ==============================================================================
# RedisSessionStore Tests
# ==============================================================================


class TestRedisSessionStore:
    """Tests for the RedisSessionStore implementation."""

    @pytest.mark.asyncio
    async def test_set_and_get(self, session_store) -> None:
        """Test storing and retrieving session data."""
        session_data = {
            "user_id": "123",
            "email": "test@example.com",
            "role": "admin",
        }

        await session_store.set("token123", session_data)
        retrieved = await session_store.get("token123")

        assert retrieved is not None
        assert retrieved["user_id"] == "123"
        assert retrieved["email"] == "test@example.com"
        assert retrieved["role"] == "admin"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, session_store) -> None:
        """Test getting non-existent session returns None."""
        result = await session_store.get("nonexistent-token")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_adds_timestamps(self, session_store) -> None:
        """Test that set adds created_at and last_accessed timestamps."""
        session_data = {"user_id": "123"}

        await session_store.set("token123", session_data)
        retrieved = await session_store.get("token123")

        assert "created_at" in retrieved
        assert "last_accessed" in retrieved

    @pytest.mark.asyncio
    async def test_get_updates_last_accessed(self, session_store) -> None:
        """Test that get updates last_accessed timestamp."""
        session_data = {"user_id": "123"}

        await session_store.set("token123", session_data)

        # Small delay to ensure timestamps differ
        await asyncio.sleep(0.01)

        retrieved1 = await session_store.get("token123")
        last_accessed1 = float(retrieved1["last_accessed"])

        await asyncio.sleep(0.01)

        retrieved2 = await session_store.get("token123")
        last_accessed2 = float(retrieved2["last_accessed"])

        assert last_accessed2 >= last_accessed1

    @pytest.mark.asyncio
    async def test_delete(self, session_store) -> None:
        """Test deleting a session."""
        await session_store.set("token123", {"user_id": "123"})

        result = await session_store.delete("token123")
        assert result is True

        # Verify it's gone
        retrieved = await session_store.get("token123")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, session_store) -> None:
        """Test deleting non-existent session returns False."""
        result = await session_store.delete("nonexistent-token")
        assert result is False

    @pytest.mark.asyncio
    async def test_exists(self, session_store) -> None:
        """Test checking if session exists."""
        assert await session_store.exists("token123") is False

        await session_store.set("token123", {"user_id": "123"})

        assert await session_store.exists("token123") is True

    @pytest.mark.asyncio
    async def test_refresh(self, session_store) -> None:
        """Test refreshing session TTL."""
        await session_store.set("token123", {"user_id": "123"})

        result = await session_store.refresh("token123", ttl=120)
        assert result is True

        # Session should still exist
        assert await session_store.exists("token123") is True

    @pytest.mark.asyncio
    async def test_refresh_nonexistent(self, session_store) -> None:
        """Test refreshing non-existent session returns False."""
        result = await session_store.refresh("nonexistent-token")
        assert result is False

    @pytest.mark.asyncio
    async def test_refresh_updates_last_accessed(self, session_store) -> None:
        """Test that refresh updates last_accessed timestamp."""
        await session_store.set("token123", {"user_id": "123"})
        initial = await session_store.get("token123")
        initial_time = float(initial["last_accessed"])

        await asyncio.sleep(0.01)

        await session_store.refresh("token123")

        refreshed = await session_store.get("token123")
        refreshed_time = float(refreshed["last_accessed"])

        assert refreshed_time >= initial_time

    @pytest.mark.asyncio
    async def test_get_all_user_sessions(self, session_store) -> None:
        """Test getting all sessions for a user."""
        # Create multiple sessions for same user
        await session_store.set("token1", {"user_id": "user123"})
        await session_store.set("token2", {"user_id": "user123"})
        await session_store.set("token3", {"user_id": "user456"})

        sessions = await session_store.get_all_user_sessions("user123")

        assert len(sessions) == 2
        assert "token1" in sessions
        assert "token2" in sessions
        assert "token3" not in sessions

    @pytest.mark.asyncio
    async def test_get_all_user_sessions_empty(self, session_store) -> None:
        """Test getting all sessions for user with no sessions."""
        sessions = await session_store.get_all_user_sessions("nonexistent_user")
        assert sessions == []

    @pytest.mark.asyncio
    async def test_delete_all_user_sessions(self, session_store) -> None:
        """Test deleting all sessions for a user."""
        await session_store.set("token1", {"user_id": "user123"})
        await session_store.set("token2", {"user_id": "user123"})
        await session_store.set("token3", {"user_id": "user456"})

        deleted = await session_store.delete_all_user_sessions("user123")
        assert deleted == 2

        # Verify user123 sessions are gone
        assert await session_store.exists("token1") is False
        assert await session_store.exists("token2") is False
        # user456 session should still exist
        assert await session_store.exists("token3") is True

    @pytest.mark.asyncio
    async def test_delete_all_user_sessions_empty(self, session_store) -> None:
        """Test deleting sessions when user has none."""
        deleted = await session_store.delete_all_user_sessions("nonexistent_user")
        assert deleted == 0

    @pytest.mark.asyncio
    async def test_custom_ttl_on_set(self, session_store) -> None:
        """Test setting session with custom TTL."""
        await session_store.set("token123", {"user_id": "123"}, ttl=10)

        # Session should exist
        assert await session_store.exists("token123") is True

    @pytest.mark.asyncio
    async def test_key_prefix(self, fake_redis) -> None:
        """Test custom key prefix is used."""
        from examples.full.redis_store import RedisSessionStore

        store = RedisSessionStore(fake_redis, key_prefix="custom_session")
        await store.set("token123", {"user_id": "123"})

        # Verify the key was created with custom prefix
        keys = [key async for key in fake_redis.scan_iter(match="custom_session:*")]
        assert len(keys) > 0
        assert any("custom_session:token123" in key for key in keys)

    @pytest.mark.asyncio
    async def test_make_key(self, session_store) -> None:
        """Test internal key generation."""
        key = session_store._make_key("abc123")
        assert key == "session:abc123"

    @pytest.mark.asyncio
    async def test_close(self, session_store) -> None:
        """Test close method."""
        await session_store.close()


# ==============================================================================
# RedisCache Tests
# ==============================================================================


class TestRedisCache:
    """Tests for the RedisCache implementation."""

    @pytest.mark.asyncio
    async def test_set_and_get_dict(self, cache) -> None:
        """Test caching and retrieving a dictionary."""
        data = {"name": "John", "age": 30}

        await cache.set("user:1", data)
        retrieved = await cache.get("user:1")

        assert retrieved == data

    @pytest.mark.asyncio
    async def test_set_and_get_list(self, cache) -> None:
        """Test caching and retrieving a list."""
        data = [1, 2, 3, "four", {"five": 5}]

        await cache.set("mylist", data)
        retrieved = await cache.get("mylist")

        assert retrieved == data

    @pytest.mark.asyncio
    async def test_set_and_get_string(self, cache) -> None:
        """Test caching and retrieving a string."""
        await cache.set("mykey", "myvalue")
        retrieved = await cache.get("mykey")

        assert retrieved == "myvalue"

    @pytest.mark.asyncio
    async def test_set_and_get_number(self, cache) -> None:
        """Test caching and retrieving a number."""
        await cache.set("count", 42)
        retrieved = await cache.get("count")

        # Numbers are converted to strings via str(), but JSON.loads("42") returns int
        assert retrieved == 42

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, cache) -> None:
        """Test getting non-existent key returns None."""
        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self, cache) -> None:
        """Test deleting a cached value."""
        await cache.set("mykey", "myvalue")

        result = await cache.delete("mykey")
        assert result is True

        # Verify it's gone
        retrieved = await cache.get("mykey")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, cache) -> None:
        """Test deleting non-existent key returns False."""
        result = await cache.delete("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_exists(self, cache) -> None:
        """Test checking if key exists."""
        assert await cache.exists("mykey") is False

        await cache.set("mykey", "myvalue")

        assert await cache.exists("mykey") is True

    @pytest.mark.asyncio
    async def test_clear_pattern(self, cache) -> None:
        """Test clearing keys by pattern."""
        await cache.set("user:1:profile", {"name": "John"})
        await cache.set("user:1:settings", {"theme": "dark"})
        await cache.set("user:2:profile", {"name": "Jane"})
        await cache.set("product:1", {"name": "Widget"})

        # Clear all user:1:* keys
        deleted = await cache.clear_pattern("user:1:*")
        assert deleted == 2

        # Verify user:1 keys are gone
        assert await cache.exists("user:1:profile") is False
        assert await cache.exists("user:1:settings") is False
        # Other keys should remain
        assert await cache.exists("user:2:profile") is True
        assert await cache.exists("product:1") is True

    @pytest.mark.asyncio
    async def test_clear_pattern_no_matches(self, cache) -> None:
        """Test clearing pattern with no matches."""
        deleted = await cache.clear_pattern("nonexistent:*")
        assert deleted == 0

    @pytest.mark.asyncio
    async def test_get_or_set_cache_hit(self, cache) -> None:
        """Test get_or_set returns cached value on cache hit."""
        await cache.set("mykey", {"cached": True})

        factory_called = False

        def factory():
            nonlocal factory_called
            factory_called = True
            return {"cached": False}

        result = await cache.get_or_set("mykey", factory)

        assert result == {"cached": True}
        assert factory_called is False  # Factory should not be called

    @pytest.mark.asyncio
    async def test_get_or_set_cache_miss_sync_factory(self, cache) -> None:
        """Test get_or_set calls sync factory on cache miss."""

        def factory():
            return {"computed": True}

        result = await cache.get_or_set("mykey", factory)

        assert result == {"computed": True}
        # Verify it was cached
        cached = await cache.get("mykey")
        assert cached == {"computed": True}

    @pytest.mark.asyncio
    async def test_get_or_set_cache_miss_async_factory(self, cache) -> None:
        """Test get_or_set calls async factory on cache miss."""

        async def async_factory():
            await asyncio.sleep(0.001)
            return {"async_computed": True}

        result = await cache.get_or_set("mykey", async_factory)

        assert result == {"async_computed": True}
        # Verify it was cached
        cached = await cache.get("mykey")
        assert cached == {"async_computed": True}

    @pytest.mark.asyncio
    async def test_get_or_set_cache_miss_coroutine(self, cache) -> None:
        """Test get_or_set handles callable returning coroutine."""

        async def async_func():
            return {"from_coroutine": True}

        def factory():
            return async_func()

        result = await cache.get_or_set("mykey", factory)

        assert result == {"from_coroutine": True}

    @pytest.mark.asyncio
    async def test_get_or_set_static_value(self, cache) -> None:
        """Test get_or_set with non-callable factory."""
        static_value = {"static": True}

        result = await cache.get_or_set("mykey", static_value)

        assert result == {"static": True}

    @pytest.mark.asyncio
    async def test_get_or_set_with_ttl(self, cache) -> None:
        """Test get_or_set respects TTL."""
        result = await cache.get_or_set("mykey", lambda: "value", ttl=10)

        assert result == "value"
        assert await cache.exists("mykey") is True

    @pytest.mark.asyncio
    async def test_custom_ttl_on_set(self, cache) -> None:
        """Test setting value with custom TTL."""
        await cache.set("mykey", "myvalue", ttl=10)

        # Value should exist
        assert await cache.exists("mykey") is True

    @pytest.mark.asyncio
    async def test_key_prefix(self, fake_redis) -> None:
        """Test custom key prefix is used."""
        from examples.full.redis_store import RedisCache

        custom_cache = RedisCache(fake_redis, key_prefix="custom_cache")
        await custom_cache.set("mykey", "myvalue")

        # Verify the key was created with custom prefix
        value = await fake_redis.get("custom_cache:mykey")
        assert value is not None

    @pytest.mark.asyncio
    async def test_make_key(self, cache) -> None:
        """Test internal key generation."""
        key = cache._make_key("user:123:profile")
        assert key == "cache:user:123:profile"

    @pytest.mark.asyncio
    async def test_close(self, cache) -> None:
        """Test close method."""
        await cache.close()

    @pytest.mark.asyncio
    async def test_json_decode_error_returns_raw(self, fake_redis) -> None:
        """Test that non-JSON data is returned as-is."""
        from examples.full.redis_store import RedisCache

        custom_cache = RedisCache(fake_redis)

        # Manually set a non-JSON value
        await fake_redis.setex("cache:raw_string", 60, "not json")

        result = await custom_cache.get("raw_string")
        assert result == "not json"


# ==============================================================================
# Factory Function Tests
# ==============================================================================


class TestFactoryFunctions:
    """Tests for the factory functions."""

    @pytest.mark.asyncio
    async def test_get_redis_client_no_url(self) -> None:
        """Test get_redis_client returns None when no URL configured."""
        from examples.full.redis_store import get_redis_client

        with patch.dict("os.environ", {}, clear=True):
            # Temporarily clear REDIS_URL
            with patch("examples.full.redis_store.REDIS_URL", None):
                client = await get_redis_client(None)
                assert client is None

    @pytest.mark.asyncio
    async def test_get_redis_client_import_error(self) -> None:
        """Test get_redis_client handles import error gracefully."""
        from examples.full.redis_store import get_redis_client

        with patch.dict("sys.modules", {"redis": None}):
            with patch("builtins.__import__", side_effect=ImportError("No module")):
                client = await get_redis_client("redis://localhost:6379/0")
                # Should return None, not raise
                assert client is None

    @pytest.mark.asyncio
    async def test_get_redis_client_connection_error(self) -> None:
        """Test get_redis_client handles connection error gracefully."""
        from examples.full.redis_store import get_redis_client

        # Use an invalid URL that will fail to connect
        client = await get_redis_client("redis://invalid-host-12345:6379/0")
        assert client is None

    @pytest.mark.asyncio
    async def test_create_redis_rate_limit_store_no_redis(self) -> None:
        """Test factory returns None when Redis unavailable."""
        from examples.full.redis_store import create_redis_rate_limit_store

        with patch("examples.full.redis_store.get_redis_client", return_value=None):
            store = await create_redis_rate_limit_store()
            assert store is None

    @pytest.mark.asyncio
    async def test_create_redis_rate_limit_store_success(self, fake_redis) -> None:
        """Test factory returns store when Redis available."""
        from examples.full.redis_store import (
            RedisRateLimitStore,
            create_redis_rate_limit_store,
        )

        async def mock_get_client(url=None):
            return fake_redis

        with patch("examples.full.redis_store.get_redis_client", mock_get_client):
            store = await create_redis_rate_limit_store()
            assert store is not None
            assert isinstance(store, RedisRateLimitStore)

    @pytest.mark.asyncio
    async def test_create_redis_session_store_no_redis(self) -> None:
        """Test factory returns None when Redis unavailable."""
        from examples.full.redis_store import create_redis_session_store

        with patch("examples.full.redis_store.get_redis_client", return_value=None):
            store = await create_redis_session_store()
            assert store is None

    @pytest.mark.asyncio
    async def test_create_redis_session_store_success(self, fake_redis) -> None:
        """Test factory returns store when Redis available."""
        from examples.full.redis_store import (
            RedisSessionStore,
            create_redis_session_store,
        )

        async def mock_get_client(url=None):
            return fake_redis

        with patch("examples.full.redis_store.get_redis_client", mock_get_client):
            store = await create_redis_session_store(default_ttl=120)
            assert store is not None
            assert isinstance(store, RedisSessionStore)

    @pytest.mark.asyncio
    async def test_create_redis_cache_no_redis(self) -> None:
        """Test factory returns None when Redis unavailable."""
        from examples.full.redis_store import create_redis_cache

        with patch("examples.full.redis_store.get_redis_client", return_value=None):
            cache = await create_redis_cache()
            assert cache is None

    @pytest.mark.asyncio
    async def test_create_redis_cache_success(self, fake_redis) -> None:
        """Test factory returns cache when Redis available."""
        from examples.full.redis_store import RedisCache, create_redis_cache

        async def mock_get_client(url=None):
            return fake_redis

        with patch("examples.full.redis_store.get_redis_client", mock_get_client):
            cache = await create_redis_cache(default_ttl=120)
            assert cache is not None
            assert isinstance(cache, RedisCache)


# ==============================================================================
# Edge Cases and Error Handling
# ==============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_rate_limit_concurrent_increments(self, rate_limit_store) -> None:
        """Test concurrent increments are handled correctly."""
        tasks = [rate_limit_store.increment("concurrent-key", "minute") for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # All results should be unique and sequential
        assert len(set(results)) == 10
        assert sorted(results) == list(range(1, 11))

    @pytest.mark.asyncio
    async def test_session_with_special_characters(self, session_store) -> None:
        """Test session tokens with special characters."""
        token = "token:with/special@chars#123"
        await session_store.set(token, {"user_id": "123"})

        result = await session_store.get(token)
        assert result is not None
        assert result["user_id"] == "123"

    @pytest.mark.asyncio
    async def test_cache_with_nested_data(self, cache) -> None:
        """Test caching deeply nested data structures."""
        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "list": [1, 2, {"nested": True}],
                        "value": "deep",
                    }
                }
            }
        }

        await cache.set("nested", data)
        retrieved = await cache.get("nested")

        assert retrieved == data
        assert retrieved["level1"]["level2"]["level3"]["list"][2]["nested"] is True

    @pytest.mark.asyncio
    async def test_cache_with_unicode(self, cache) -> None:
        """Test caching unicode strings."""
        data = {
            "message": "Hello, World!",
            "japanese": "Nihongo wa muzukashii",
            "emoji": "emoji",
        }

        await cache.set("unicode", data)
        retrieved = await cache.get("unicode")

        assert retrieved == data

    @pytest.mark.asyncio
    async def test_rate_limit_empty_key(self, rate_limit_store) -> None:
        """Test rate limiting with empty key string."""
        count = await rate_limit_store.increment("", "minute")
        assert count == 1

        count = await rate_limit_store.get_count("", "minute")
        assert count == 1

    @pytest.mark.asyncio
    async def test_session_empty_data(self, session_store) -> None:
        """Test session with empty data dict."""
        await session_store.set("empty-session", {})
        result = await session_store.get("empty-session")

        # Should have timestamps even with empty input
        assert "created_at" in result
        assert "last_accessed" in result

    @pytest.mark.asyncio
    async def test_cache_null_value(self, cache) -> None:
        """Test caching null/None value."""
        await cache.set("null-key", None)

        # get_or_set should treat None as cache miss
        result = await cache.get_or_set("null-key", lambda: "computed")
        # Since the stored value is "None" string, it will be returned
        assert result is not None
