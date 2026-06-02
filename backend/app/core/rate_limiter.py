"""
Personal AI OS - Rate Limiting & API Throttling

Redis-backed sliding window rate limiter implemented as FastAPI middleware.
Uses sorted sets with timestamps for precise per-user rate limiting.
"""
import time
from typing import Optional
from uuid import uuid4

# pyrefly: ignore [missing-import]
from fastapi import Request, Response
# pyrefly: ignore [missing-import]
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
# pyrefly: ignore [missing-import]
from starlette.responses import JSONResponse

from app.config import get_settings


# Paths that should use the stricter LLM rate limit tier
LLM_TIER_PATHS = {
    "/api/chat",
    "/api/chat/stream",
    "/api/summarize",
}


class RateLimiter:
    """
    Sliding window rate limiter backed by Redis sorted sets.

    Each user's requests are tracked in a Redis sorted set keyed by
    `ratelimit:{user_id}:{tier}`. Entries are scored by timestamp
    and expired entries are trimmed on each check.
    """

    PREFIX = "ratelimit:"

    def __init__(self, redis_client):
        self.redis = redis_client
        self.settings = get_settings()

    async def is_allowed(
        self,
        identifier: str,
        tier: str = "default",
    ) -> tuple[bool, dict]:
        """
        Check if a request is allowed under the rate limit.

        Args:
            identifier: Unique identifier (user_id or IP).
            tier: Rate limit tier ("default" or "llm").

        Returns:
            Tuple of (allowed: bool, info: dict with limit/remaining/reset).
        """
        if tier == "llm":
            max_requests = self.settings.rate_limit_llm
        else:
            max_requests = self.settings.rate_limit_default

        now = time.time()
        window_start = now - 60.0  # 1-minute sliding window
        key = f"{self.PREFIX}{identifier}:{tier}"

        pipe = self.redis.pipeline()
        # Remove expired entries
        pipe.zremrangebyscore(key, 0, window_start)
        # Count remaining entries in window
        pipe.zcard(key)
        # Add current request
        pipe.zadd(key, {f"{now}:{uuid4().hex[:8]}": now})
        # Set expiry on the key itself (auto-cleanup)
        pipe.expire(key, 120)

        results = await pipe.execute()
        current_count = results[1]  # zcard result before adding

        remaining = max(0, max_requests - current_count - 1)
        reset_at = int(now + 60)

        info = {
            "limit": max_requests,
            "remaining": remaining,
            "reset": reset_at,
            "tier": tier,
        }

        if current_count >= max_requests:
            # Over limit — remove the entry we just added
            info["remaining"] = 0
            info["retry_after"] = int(60 - (now - window_start))
            return False, info

        return True, info


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that applies per-user rate limiting.

    Identifies users by the `X-User-ID` header, falling back to
    client IP. Adds `X-RateLimit-*` headers to all responses.
    """

    # Paths exempt from rate limiting
    EXEMPT_PATHS = {"/api/health", "/api/rate-limit/status", "/docs", "/openapi.json"}

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip exempt paths
        path = request.url.path
        if path in self.EXEMPT_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        # Get Redis client (may not be available in tests)
        try:
            from app.db.redis import get_redis
            redis_client = get_redis()
        except (RuntimeError, Exception):
            # Redis not available — let requests through
            return await call_next(request)

        # Identify the user
        identifier = request.headers.get("X-User-ID", "")
        if not identifier:
            identifier = request.client.host if request.client else "unknown"

        # Determine rate limit tier
        tier = "llm" if path in LLM_TIER_PATHS else "default"

        limiter = RateLimiter(redis_client)
        allowed, info = await limiter.is_allowed(identifier, tier)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "detail": f"Too many requests. Limit: {info['limit']}/min ({info['tier']} tier)",
                    "retry_after": info.get("retry_after", 60),
                },
                headers={
                    "Retry-After": str(info.get("retry_after", 60)),
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(info["reset"]),
                    "X-RateLimit-Tier": info["tier"],
                },
            )

        # Allowed — proceed and attach rate limit headers
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(info["reset"])
        response.headers["X-RateLimit-Tier"] = info["tier"]

        return response
