"""
Personal AI OS - Rate Limit Status API
"""
from fastapi import APIRouter, Request

from app.core.rate_limiter import RateLimiter, LLM_TIER_PATHS


router = APIRouter()


@router.get("/rate-limit/status")
async def get_rate_limit_status(request: Request):
    """
    Returns the current user's rate limit status across all tiers.

    The user is identified by the `X-User-ID` header or client IP.
    """
    try:
        from app.db.redis import get_redis
        redis_client = get_redis()
    except (RuntimeError, Exception):
        return {
            "status": "unavailable",
            "detail": "Redis not connected — rate limiting disabled",
        }

    identifier = request.headers.get("X-User-ID", "")
    if not identifier:
        identifier = request.client.host if request.client else "unknown"

    limiter = RateLimiter(redis_client)

    _, default_info = await limiter.is_allowed(identifier, "default")
    _, llm_info = await limiter.is_allowed(identifier, "llm")

    return {
        "identifier": identifier,
        "tiers": {
            "default": {
                "limit": default_info["limit"],
                "remaining": default_info["remaining"],
                "reset": default_info["reset"],
            },
            "llm": {
                "limit": llm_info["limit"],
                "remaining": llm_info["remaining"],
                "reset": llm_info["reset"],
            },
        },
        "llm_paths": sorted(LLM_TIER_PATHS),
    }
