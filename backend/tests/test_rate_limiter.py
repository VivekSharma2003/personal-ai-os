"""
Tests for Rate Limiting & API Throttling (Feature 1).
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from app.core.rate_limiter import RateLimiter, RateLimitMiddleware, LLM_TIER_PATHS


class FakeRedis:
    """Minimal async Redis mock for rate limit testing."""

    def __init__(self):
        self._data = {}

    def pipeline(self):
        return FakePipeline(self._data)


class FakePipeline:
    def __init__(self, data):
        self._data = data
        self._commands = []

    def zremrangebyscore(self, key, low, high):
        self._commands.append(("zremrangebyscore", key, low, high))

    def zcard(self, key):
        self._commands.append(("zcard", key))

    def zadd(self, key, mapping):
        self._commands.append(("zadd", key, mapping))

    def expire(self, key, ttl):
        self._commands.append(("expire", key, ttl))

    async def execute(self):
        # zremrangebyscore returns removed count, zcard returns 0, zadd returns 1, expire returns True
        return [0, 0, 1, True]


@pytest.mark.asyncio
async def test_rate_limiter_allows_first_request():
    """First request should always be allowed."""
    redis = FakeRedis()
    limiter = RateLimiter(redis)
    allowed, info = await limiter.is_allowed("user123", "default")

    assert allowed is True
    assert info["tier"] == "default"
    assert info["limit"] == 60
    assert info["remaining"] >= 0


@pytest.mark.asyncio
async def test_rate_limiter_blocks_when_over_limit():
    """Requests should be blocked when over the limit."""

    class OverLimitPipeline(FakePipeline):
        async def execute(self):
            return [0, 100, 1, True]  # zcard returns 100 (over any limit)

    class OverLimitRedis(FakeRedis):
        def pipeline(self):
            return OverLimitPipeline(self._data)

    redis = OverLimitRedis()
    limiter = RateLimiter(redis)
    allowed, info = await limiter.is_allowed("user123", "default")

    assert allowed is False
    assert info["remaining"] == 0
    assert "retry_after" in info


@pytest.mark.asyncio
async def test_rate_limiter_llm_tier_has_lower_limit():
    """LLM tier should have a lower rate limit."""
    redis = FakeRedis()
    limiter = RateLimiter(redis)
    _, info = await limiter.is_allowed("user123", "llm")

    assert info["tier"] == "llm"
    assert info["limit"] == 10


def test_llm_tier_paths_defined():
    """LLM-intensive paths should be configured."""
    assert "/api/chat" in LLM_TIER_PATHS
    assert "/api/chat/stream" in LLM_TIER_PATHS


@pytest.mark.asyncio
async def test_rate_limit_status_endpoint(client):
    """Rate limit status endpoint should return tier info."""
    response = await client.get(
        "/api/rate-limit/status",
        headers={"X-User-ID": "test_user"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "tiers" in data or "status" in data
