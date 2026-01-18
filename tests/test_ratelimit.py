"""Tests for rate limiting middleware."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from litestar import Litestar, get
from litestar.status_codes import HTTP_200_OK, HTTP_429_TOO_MANY_REQUESTS
from litestar.testing import TestClient

from litestar_admin.middleware import (
    InMemoryRateLimitStore,
    RateLimitConfig,
    RateLimitMiddleware,
    RateLimitStore,
    create_rate_limit_middleware,
    get_client_ip,
    get_rate_limit_key,
)

if TYPE_CHECKING:
    pass


# ==============================================================================
# Test Fixtures
# ==============================================================================


@pytest.fixture
def rate_limit_config() -> RateLimitConfig:
    """Return a basic rate limit configuration."""
    return RateLimitConfig(
        requests_per_minute=10,
        requests_per_hour=100,
        burst_size=5,
    )


@pytest.fixture
def rate_limit_store() -> InMemoryRateLimitStore:
    """Return a fresh in-memory rate limit store."""
    return InMemoryRateLimitStore()


@pytest.fixture
def mock_connection() -> MagicMock:
    """Return a mock ASGI connection."""
    conn = MagicMock()
    conn.client = MagicMock()
    conn.client.host = "192.168.1.100"
    conn.headers = {
        "user-agent": "Test Browser/1.0",
    }
    return conn


@pytest.fixture
def mock_connection_with_proxy() -> MagicMock:
    """Return a mock ASGI connection with proxy headers."""
    conn = MagicMock()
    conn.client = MagicMock()
    conn.client.host = "127.0.0.1"
    conn.headers = {
        "x-forwarded-for": "203.0.113.195, 70.41.3.18",
        "user-agent": "Test Browser/1.0",
    }
    return conn


# ==============================================================================
# RateLimitConfig Tests
# ==============================================================================


class TestRateLimitConfig:
    """Tests for the RateLimitConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = RateLimitConfig()

        assert config.requests_per_minute == 60
        assert config.requests_per_hour == 1000
        assert config.burst_size == 10
        assert config.key_func is None
        assert config.exclude_paths == []
        assert config.include_paths is None
        assert config.enabled is True
        assert config.headers_enabled is True

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = RateLimitConfig(
            requests_per_minute=100,
            requests_per_hour=2000,
            burst_size=20,
            exclude_paths=["/health", "/status"],
            enabled=False,
        )

        assert config.requests_per_minute == 100
        assert config.requests_per_hour == 2000
        assert config.burst_size == 20
        assert config.exclude_paths == ["/health", "/status"]
        assert config.enabled is False

    def test_validation_requests_per_minute(self) -> None:
        """Test validation of requests_per_minute."""
        with pytest.raises(ValueError, match="requests_per_minute must be at least 1"):
            RateLimitConfig(requests_per_minute=0)

        with pytest.raises(ValueError, match="requests_per_minute must be at least 1"):
            RateLimitConfig(requests_per_minute=-1)

    def test_validation_requests_per_hour(self) -> None:
        """Test validation of requests_per_hour."""
        with pytest.raises(ValueError, match="requests_per_hour must be at least 1"):
            RateLimitConfig(requests_per_hour=0)

    def test_validation_burst_size(self) -> None:
        """Test validation of burst_size."""
        with pytest.raises(ValueError, match="burst_size must be at least 1"):
            RateLimitConfig(burst_size=0)

    def test_validation_hour_less_than_minute(self) -> None:
        """Test validation when hour limit is less than minute limit."""
        with pytest.raises(ValueError, match="requests_per_hour must be greater than or equal"):
            RateLimitConfig(requests_per_minute=100, requests_per_hour=50)

    def test_custom_key_func(self) -> None:
        """Test configuration with custom key function."""

        def custom_key(conn):
            return f"user:{getattr(conn, 'user_id', 'anon')}"

        config = RateLimitConfig(key_func=custom_key)
        assert config.key_func is not None

    def test_include_paths(self) -> None:
        """Test configuration with include_paths."""
        config = RateLimitConfig(include_paths=["/api/", "/admin/"])

        assert config.include_paths == ["/api/", "/admin/"]


# ==============================================================================
# InMemoryRateLimitStore Tests
# ==============================================================================


class TestInMemoryRateLimitStore:
    """Tests for the InMemoryRateLimitStore implementation."""

    @pytest.mark.asyncio
    async def test_get_count_empty(self, rate_limit_store: InMemoryRateLimitStore) -> None:
        """Test getting count for non-existent key."""
        count = await rate_limit_store.get_count("test-key", "minute")
        assert count == 0

    @pytest.mark.asyncio
    async def test_increment(self, rate_limit_store: InMemoryRateLimitStore) -> None:
        """Test incrementing counter."""
        count1 = await rate_limit_store.increment("test-key", "minute")
        assert count1 == 1

        count2 = await rate_limit_store.increment("test-key", "minute")
        assert count2 == 2

        count3 = await rate_limit_store.increment("test-key", "minute")
        assert count3 == 3

    @pytest.mark.asyncio
    async def test_increment_different_windows(self, rate_limit_store: InMemoryRateLimitStore) -> None:
        """Test incrementing counters in different windows."""
        await rate_limit_store.increment("test-key", "minute")
        await rate_limit_store.increment("test-key", "minute")
        await rate_limit_store.increment("test-key", "hour")

        minute_count = await rate_limit_store.get_count("test-key", "minute")
        hour_count = await rate_limit_store.get_count("test-key", "hour")

        assert minute_count == 2
        assert hour_count == 1

    @pytest.mark.asyncio
    async def test_increment_different_keys(self, rate_limit_store: InMemoryRateLimitStore) -> None:
        """Test incrementing counters for different keys."""
        await rate_limit_store.increment("key1", "minute")
        await rate_limit_store.increment("key1", "minute")
        await rate_limit_store.increment("key2", "minute")

        count1 = await rate_limit_store.get_count("key1", "minute")
        count2 = await rate_limit_store.get_count("key2", "minute")

        assert count1 == 2
        assert count2 == 1

    @pytest.mark.asyncio
    async def test_reset(self, rate_limit_store: InMemoryRateLimitStore) -> None:
        """Test resetting counters for a key."""
        await rate_limit_store.increment("test-key", "minute")
        await rate_limit_store.increment("test-key", "hour")

        await rate_limit_store.reset("test-key")

        minute_count = await rate_limit_store.get_count("test-key", "minute")
        hour_count = await rate_limit_store.get_count("test-key", "hour")

        assert minute_count == 0
        assert hour_count == 0

    @pytest.mark.asyncio
    async def test_get_remaining(self, rate_limit_store: InMemoryRateLimitStore) -> None:
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
    async def test_get_remaining_at_limit(self, rate_limit_store: InMemoryRateLimitStore) -> None:
        """Test getting remaining when at limit."""
        limit = 3

        await rate_limit_store.increment("test-key", "minute")
        await rate_limit_store.increment("test-key", "minute")
        await rate_limit_store.increment("test-key", "minute")

        remaining = await rate_limit_store.get_remaining("test-key", "minute", limit)
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_get_remaining_over_limit(self, rate_limit_store: InMemoryRateLimitStore) -> None:
        """Test that remaining never goes negative."""
        limit = 2

        await rate_limit_store.increment("test-key", "minute")
        await rate_limit_store.increment("test-key", "minute")
        await rate_limit_store.increment("test-key", "minute")

        remaining = await rate_limit_store.get_remaining("test-key", "minute", limit)
        assert remaining == 0  # Not -1

    @pytest.mark.asyncio
    async def test_get_reset_time(self, rate_limit_store: InMemoryRateLimitStore) -> None:
        """Test getting reset time."""
        await rate_limit_store.increment("test-key", "minute")

        reset_time = await rate_limit_store.get_reset_time("test-key", "minute")

        # Reset time should be in the future (within 60 seconds)
        current_time = int(time.time())
        assert reset_time > current_time
        assert reset_time <= current_time + 60

    @pytest.mark.asyncio
    async def test_get_reset_time_new_key(self, rate_limit_store: InMemoryRateLimitStore) -> None:
        """Test getting reset time for a new key."""
        reset_time = await rate_limit_store.get_reset_time("new-key", "minute")

        # Should be approximately now + 60 seconds
        current_time = int(time.time())
        assert reset_time >= current_time + 59
        assert reset_time <= current_time + 61

    @pytest.mark.asyncio
    async def test_window_expiry(self) -> None:
        """Test that windows expire correctly."""
        # Create store with very short window for testing
        store = InMemoryRateLimitStore(minute_window=1)

        await store.increment("test-key", "minute")
        count1 = await store.get_count("test-key", "minute")
        assert count1 == 1

        # Wait for window to expire
        await asyncio.sleep(1.1)

        count2 = await store.get_count("test-key", "minute")
        assert count2 == 0

    @pytest.mark.asyncio
    async def test_increment_resets_expired_window(self) -> None:
        """Test that increment resets an expired window."""
        store = InMemoryRateLimitStore(minute_window=1)

        await store.increment("test-key", "minute")
        await store.increment("test-key", "minute")

        # Wait for window to expire
        await asyncio.sleep(1.1)

        # Increment should start fresh
        count = await store.increment("test-key", "minute")
        assert count == 1

    def test_clear(self, rate_limit_store: InMemoryRateLimitStore) -> None:
        """Test clearing all data."""
        # Add some data synchronously by directly manipulating internal state
        rate_limit_store._data["key1"] = {}
        rate_limit_store._data["key2"] = {}

        rate_limit_store.clear()

        assert len(rate_limit_store.keys) == 0

    def test_keys_property(self, rate_limit_store: InMemoryRateLimitStore) -> None:
        """Test the keys property."""
        rate_limit_store._data["key1"] = {}
        rate_limit_store._data["key2"] = {}

        keys = rate_limit_store.keys

        assert "key1" in keys
        assert "key2" in keys

    @pytest.mark.asyncio
    async def test_implements_protocol(self) -> None:
        """Verify InMemoryRateLimitStore implements RateLimitStore protocol."""
        store = InMemoryRateLimitStore()
        assert isinstance(store, RateLimitStore)


# ==============================================================================
# Helper Function Tests
# ==============================================================================


class TestGetClientIp:
    """Tests for the get_client_ip helper function."""

    def test_direct_connection(self, mock_connection: MagicMock) -> None:
        """Test getting IP from direct connection."""
        ip = get_client_ip(mock_connection)
        assert ip == "192.168.1.100"

    def test_x_forwarded_for_single(self) -> None:
        """Test getting IP from X-Forwarded-For with single IP."""
        conn = MagicMock()
        conn.headers = {"x-forwarded-for": "203.0.113.195"}
        conn.client = None

        ip = get_client_ip(conn)
        assert ip == "203.0.113.195"

    def test_x_forwarded_for_multiple(self, mock_connection_with_proxy: MagicMock) -> None:
        """Test getting IP from X-Forwarded-For with multiple IPs."""
        ip = get_client_ip(mock_connection_with_proxy)
        # Should return the first IP (original client)
        assert ip == "203.0.113.195"

    def test_x_real_ip(self) -> None:
        """Test getting IP from X-Real-IP header."""
        conn = MagicMock()
        conn.headers = {"x-real-ip": "10.0.0.5"}
        conn.client = None

        ip = get_client_ip(conn)
        assert ip == "10.0.0.5"

    def test_x_forwarded_for_takes_precedence(self) -> None:
        """Test that X-Forwarded-For takes precedence over X-Real-IP."""
        conn = MagicMock()
        conn.headers = {
            "x-forwarded-for": "203.0.113.195",
            "x-real-ip": "10.0.0.5",
        }
        conn.client = MagicMock()
        conn.client.host = "127.0.0.1"

        ip = get_client_ip(conn)
        assert ip == "203.0.113.195"

    def test_no_ip_available(self) -> None:
        """Test when no IP is available."""
        conn = MagicMock()
        conn.headers = {}
        conn.client = None

        ip = get_client_ip(conn)
        assert ip == "unknown"

    def test_whitespace_handling(self) -> None:
        """Test that whitespace is stripped from IPs."""
        conn = MagicMock()
        conn.headers = {"x-forwarded-for": "  203.0.113.195  ,  70.41.3.18  "}
        conn.client = None

        ip = get_client_ip(conn)
        assert ip == "203.0.113.195"


class TestGetRateLimitKey:
    """Tests for the get_rate_limit_key helper function."""

    def test_default_uses_ip(self, mock_connection: MagicMock) -> None:
        """Test that default key is the client IP."""
        config = RateLimitConfig()
        key = get_rate_limit_key(mock_connection, config)
        assert key == "192.168.1.100"

    def test_custom_key_func(self, mock_connection: MagicMock) -> None:
        """Test using a custom key function."""
        mock_connection.user_id = 42

        def custom_key(conn):
            return f"user:{conn.user_id}"

        config = RateLimitConfig(key_func=custom_key)
        key = get_rate_limit_key(mock_connection, config)
        assert key == "user:42"

    def test_custom_key_func_with_fallback(self) -> None:
        """Test custom key function with fallback."""

        def custom_key(conn):
            if hasattr(conn, "user") and conn.user:
                return f"user:{conn.user.id}"
            return f"ip:{get_client_ip(conn)}"

        # Test with user
        conn_with_user = MagicMock()
        conn_with_user.user = MagicMock()
        conn_with_user.user.id = 42
        conn_with_user.headers = {}

        config = RateLimitConfig(key_func=custom_key)
        key = get_rate_limit_key(conn_with_user, config)
        assert key == "user:42"

        # Test without user
        conn_no_user = MagicMock()
        conn_no_user.user = None
        conn_no_user.headers = {}
        conn_no_user.client = MagicMock()
        conn_no_user.client.host = "10.0.0.1"

        key = get_rate_limit_key(conn_no_user, config)
        assert key == "ip:10.0.0.1"


# ==============================================================================
# RateLimitMiddleware Tests
# ==============================================================================


class TestRateLimitMiddleware:
    """Tests for the RateLimitMiddleware."""

    def test_middleware_allows_requests_under_limit(self) -> None:
        """Test that requests under the limit are allowed."""
        config = RateLimitConfig(requests_per_minute=10, requests_per_hour=100)

        @get("/test")
        async def test_handler() -> dict:
            return {"status": "ok"}

        app = Litestar(
            route_handlers=[test_handler],
            middleware=[create_rate_limit_middleware(config)],
        )

        with TestClient(app) as client:
            for _ in range(5):
                response = client.get("/test")
                assert response.status_code == HTTP_200_OK

    def test_middleware_blocks_at_limit(self) -> None:
        """Test that requests are blocked when limit is reached."""
        config = RateLimitConfig(requests_per_minute=3, requests_per_hour=100)

        @get("/test")
        async def test_handler() -> dict:
            return {"status": "ok"}

        app = Litestar(
            route_handlers=[test_handler],
            middleware=[create_rate_limit_middleware(config)],
        )

        with TestClient(app) as client:
            # First 3 requests should succeed
            for _ in range(3):
                response = client.get("/test")
                assert response.status_code == HTTP_200_OK

            # 4th request should be rate limited
            response = client.get("/test")
            assert response.status_code == HTTP_429_TOO_MANY_REQUESTS

    def test_middleware_adds_rate_limit_headers(self) -> None:
        """Test that rate limit headers are added to responses."""
        config = RateLimitConfig(requests_per_minute=10, requests_per_hour=100)

        @get("/test")
        async def test_handler() -> dict:
            return {"status": "ok"}

        app = Litestar(
            route_handlers=[test_handler],
            middleware=[create_rate_limit_middleware(config)],
        )

        with TestClient(app) as client:
            response = client.get("/test")

            assert "x-ratelimit-limit" in response.headers
            assert "x-ratelimit-remaining" in response.headers
            assert "x-ratelimit-reset" in response.headers

            assert response.headers["x-ratelimit-limit"] == "10"

    def test_middleware_headers_on_429(self) -> None:
        """Test that headers are present on 429 responses."""
        config = RateLimitConfig(requests_per_minute=1, requests_per_hour=100)

        @get("/test")
        async def test_handler() -> dict:
            return {"status": "ok"}

        app = Litestar(
            route_handlers=[test_handler],
            middleware=[create_rate_limit_middleware(config)],
        )

        with TestClient(app) as client:
            client.get("/test")  # First request
            response = client.get("/test")  # Second request - should be blocked

            assert response.status_code == HTTP_429_TOO_MANY_REQUESTS
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
            assert "X-RateLimit-Reset" in response.headers
            assert "Retry-After" in response.headers

    def test_middleware_429_response_body(self) -> None:
        """Test the body of 429 responses."""
        config = RateLimitConfig(requests_per_minute=1, requests_per_hour=100)

        @get("/test")
        async def test_handler() -> dict:
            return {"status": "ok"}

        app = Litestar(
            route_handlers=[test_handler],
            middleware=[create_rate_limit_middleware(config)],
        )

        with TestClient(app) as client:
            client.get("/test")
            response = client.get("/test")

            assert response.status_code == HTTP_429_TOO_MANY_REQUESTS
            data = response.json()
            assert "error" in data
            assert data["error"] == "Too Many Requests"
            assert "retry_after" in data

    def test_middleware_exclude_paths(self) -> None:
        """Test that excluded paths are not rate limited."""
        config = RateLimitConfig(
            requests_per_minute=1,
            requests_per_hour=100,
            exclude_paths=["/health"],
        )

        @get("/test")
        async def test_handler() -> dict:
            return {"status": "ok"}

        @get("/health")
        async def health_handler() -> dict:
            return {"status": "healthy"}

        app = Litestar(
            route_handlers=[test_handler, health_handler],
            middleware=[create_rate_limit_middleware(config)],
        )

        with TestClient(app) as client:
            # First request to /test should work
            response = client.get("/test")
            assert response.status_code == HTTP_200_OK

            # Second request to /test should be blocked
            response = client.get("/test")
            assert response.status_code == HTTP_429_TOO_MANY_REQUESTS

            # Requests to /health should always work
            for _ in range(10):
                response = client.get("/health")
                assert response.status_code == HTTP_200_OK

    def test_middleware_include_paths(self) -> None:
        """Test that only included paths are rate limited."""
        config = RateLimitConfig(
            requests_per_minute=1,
            requests_per_hour=100,
            include_paths=["/api/"],
        )

        @get("/api/test")
        async def api_handler() -> dict:
            return {"status": "ok"}

        @get("/public")
        async def public_handler() -> dict:
            return {"status": "ok"}

        app = Litestar(
            route_handlers=[api_handler, public_handler],
            middleware=[create_rate_limit_middleware(config)],
        )

        with TestClient(app) as client:
            # First request to /api/test should work
            response = client.get("/api/test")
            assert response.status_code == HTTP_200_OK

            # Second request to /api/test should be blocked
            response = client.get("/api/test")
            assert response.status_code == HTTP_429_TOO_MANY_REQUESTS

            # Requests to /public should always work
            for _ in range(10):
                response = client.get("/public")
                assert response.status_code == HTTP_200_OK

    def test_middleware_disabled(self) -> None:
        """Test that disabled middleware allows all requests."""
        config = RateLimitConfig(
            requests_per_minute=1,
            requests_per_hour=100,
            enabled=False,
        )

        @get("/test")
        async def test_handler() -> dict:
            return {"status": "ok"}

        app = Litestar(
            route_handlers=[test_handler],
            middleware=[create_rate_limit_middleware(config)],
        )

        with TestClient(app) as client:
            for _ in range(10):
                response = client.get("/test")
                assert response.status_code == HTTP_200_OK

    def test_middleware_headers_disabled(self) -> None:
        """Test that headers can be disabled."""
        config = RateLimitConfig(
            requests_per_minute=10,
            requests_per_hour=100,
            headers_enabled=False,
        )

        @get("/test")
        async def test_handler() -> dict:
            return {"status": "ok"}

        app = Litestar(
            route_handlers=[test_handler],
            middleware=[create_rate_limit_middleware(config)],
        )

        with TestClient(app) as client:
            response = client.get("/test")
            assert response.status_code == HTTP_200_OK
            # Headers should not be present (or at least not rate limit headers)
            assert "x-ratelimit-limit" not in response.headers

    @pytest.mark.asyncio
    async def test_middleware_per_hour_limit(self) -> None:
        """Test that hour limit is enforced."""
        # Test the hour limit logic directly using the store
        # (Integration test with full middleware would require time mocking)
        store = InMemoryRateLimitStore()

        # Simulate hitting the hour limit
        for _ in range(10):
            await store.increment("test-key", "hour")

        count = await store.get_count("test-key", "hour")
        assert count == 10

        remaining = await store.get_remaining("test-key", "hour", 10)
        assert remaining == 0

        # Verify minute window is separate
        minute_remaining = await store.get_remaining("test-key", "minute", 100)
        assert minute_remaining == 100  # Still full since we only incremented hour


# ==============================================================================
# Factory Function Tests
# ==============================================================================


class TestCreateRateLimitMiddleware:
    """Tests for the create_rate_limit_middleware factory function."""

    def test_creates_middleware_with_defaults(self) -> None:
        """Test creating middleware with default configuration."""
        middleware_class = create_rate_limit_middleware()

        # Verify it's a proper middleware class
        assert issubclass(middleware_class, RateLimitMiddleware)

    def test_creates_middleware_with_custom_config(self) -> None:
        """Test creating middleware with custom configuration."""
        config = RateLimitConfig(requests_per_minute=100)
        store = InMemoryRateLimitStore()

        middleware_class = create_rate_limit_middleware(config, store)

        @get("/test")
        async def test_handler() -> dict:
            return {"status": "ok"}

        app = Litestar(
            route_handlers=[test_handler],
            middleware=[middleware_class],
        )

        with TestClient(app) as client:
            response = client.get("/test")
            assert response.status_code == HTTP_200_OK


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestRateLimitIntegration:
    """Integration tests for the rate limiting system."""

    def test_different_clients_have_separate_limits(self) -> None:
        """Test that different clients have separate rate limits."""
        config = RateLimitConfig(requests_per_minute=2, requests_per_hour=100)

        @get("/test")
        async def test_handler() -> dict:
            return {"status": "ok"}

        app = Litestar(
            route_handlers=[test_handler],
            middleware=[create_rate_limit_middleware(config)],
        )

        with TestClient(app) as client:
            # Client 1 (default IP)
            client.get("/test")
            client.get("/test")
            response = client.get("/test")
            assert response.status_code == HTTP_429_TOO_MANY_REQUESTS

        # Client 2 (different IP via header)
        with TestClient(app) as client2:
            response = client2.get("/test", headers={"X-Forwarded-For": "10.0.0.1"})
            assert response.status_code == HTTP_200_OK

    def test_remaining_decrements_correctly(self) -> None:
        """Test that remaining count decrements correctly."""
        config = RateLimitConfig(requests_per_minute=5, requests_per_hour=100)

        @get("/test")
        async def test_handler() -> dict:
            return {"status": "ok"}

        app = Litestar(
            route_handlers=[test_handler],
            middleware=[create_rate_limit_middleware(config)],
        )

        with TestClient(app) as client:
            response = client.get("/test")
            assert response.headers["x-ratelimit-remaining"] == "4"

            response = client.get("/test")
            assert response.headers["x-ratelimit-remaining"] == "3"

            response = client.get("/test")
            assert response.headers["x-ratelimit-remaining"] == "2"

    def test_full_workflow(self) -> None:
        """Test complete rate limiting workflow."""
        config = RateLimitConfig(
            requests_per_minute=3,
            requests_per_hour=10,
            exclude_paths=["/health"],
        )
        store = InMemoryRateLimitStore()

        @get("/api/data")
        async def data_handler() -> dict:
            return {"data": "value"}

        @get("/health")
        async def health_handler() -> dict:
            return {"status": "healthy"}

        app = Litestar(
            route_handlers=[data_handler, health_handler],
            middleware=[create_rate_limit_middleware(config, store)],
        )

        with TestClient(app) as client:
            # Health endpoint always works
            response = client.get("/health")
            assert response.status_code == HTTP_200_OK

            # API endpoint works up to limit
            for i in range(3):
                response = client.get("/api/data")
                assert response.status_code == HTTP_200_OK
                assert response.headers["x-ratelimit-remaining"] == str(2 - i)

            # 4th request is blocked
            response = client.get("/api/data")
            assert response.status_code == HTTP_429_TOO_MANY_REQUESTS
            assert "Retry-After" in response.headers

            # Health still works
            response = client.get("/health")
            assert response.status_code == HTTP_200_OK
