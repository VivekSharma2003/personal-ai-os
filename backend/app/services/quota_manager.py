"""
Personal AI OS - Context-Aware Quota Management
"""
import time
import logging
from typing import Dict, Any, Tuple
from uuid import UUID

from app.db.redis import get_redis
from app.config import get_settings

logger = logging.getLogger(__name__)

class QuotaManagerService:
    """
    Manages rate limits and usage quotas using Redis fixed windows.
    Tracks token counts and requests over specific time periods.
    """
    def __init__(self):
        self.settings = get_settings()
        self.redis = get_redis()
        
        # Default limits
        self.default_hourly_tokens = getattr(self.settings, 'hourly_token_limit', 100000)
        self.default_daily_requests = getattr(self.settings, 'daily_request_limit', 1000)

    async def _get_current_counts(self, user_id: UUID) -> Tuple[int, int]:
        """Get current usage without incrementing."""
        if not self.redis:
            return 0, 0
            
        day_str = time.strftime("%Y-%m-%d")
        hour_str = time.strftime("%Y-%m-%d-%H")
        
        user_key_prefix = f"quota:{user_id}"
        req_key = f"{user_key_prefix}:req:{day_str}"
        token_key = f"{user_key_prefix}:tok:{hour_str}"
        
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.get(req_key)
            pipe.get(token_key)
            results = await pipe.execute()
            
        requests = int(results[0] or 0)
        tokens = int(results[1] or 0)
        return requests, tokens

    async def get_quota_status(self, user_id: UUID) -> Dict[str, Any]:
        """Read-only check of current quota status."""
        requests, tokens = await self._get_current_counts(user_id)
        
        req_allowed = requests <= self.default_daily_requests
        tokens_allowed = tokens <= self.default_hourly_tokens
        
        return {
            "requests": {
                "used": requests,
                "limit": self.default_daily_requests,
                "remaining": max(0, self.default_daily_requests - requests)
            },
            "tokens": {
                "used": tokens,
                "limit": self.default_hourly_tokens,
                "remaining": max(0, self.default_hourly_tokens - tokens)
            },
            "allowed": req_allowed and tokens_allowed
        }

    async def check_and_consume_quota(self, user_id: UUID, tokens: int = 0) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if the user has enough quota and consume it if so.
        Increments request count by 1 and tokens count by `tokens`.
        Returns (is_allowed, quota_details).
        """
        if not self.redis:
            logger.warning("Redis not available, bypassing quota check.")
            return True, {"status": "bypassed"}
            
        # First check if they already exceeded
        curr_req, curr_tok = await self._get_current_counts(user_id)
        
        if curr_req >= self.default_daily_requests or (curr_tok + tokens) > self.default_hourly_tokens:
            status = await self.get_quota_status(user_id)
            status["allowed"] = False
            status["reason"] = "Token limit exceeded" if (curr_tok + tokens) > self.default_hourly_tokens else "Request limit exceeded"
            return False, status
            
        day_str = time.strftime("%Y-%m-%d")
        hour_str = time.strftime("%Y-%m-%d-%H")
        
        user_key_prefix = f"quota:{user_id}"
        req_key = f"{user_key_prefix}:req:{day_str}"
        token_key = f"{user_key_prefix}:tok:{hour_str}"
        
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.incr(req_key)
            pipe.expire(req_key, 86400 * 2) # 2 days TTL
            
            if tokens > 0:
                pipe.incrby(token_key, tokens)
                pipe.expire(token_key, 3600 * 2) # 2 hours TTL
                
            results = await pipe.execute()
            
        current_requests = int(results[0])
        current_tokens = int(results[2]) if tokens > 0 else curr_tok
        
        details = {
            "requests": {
                "used": current_requests,
                "limit": self.default_daily_requests,
                "remaining": max(0, self.default_daily_requests - current_requests)
            },
            "tokens": {
                "used": current_tokens,
                "limit": self.default_hourly_tokens,
                "remaining": max(0, self.default_hourly_tokens - current_tokens)
            },
            "allowed": True
        }
        
        return True, details
