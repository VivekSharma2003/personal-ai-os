"""
Personal AI OS - Redis Cache Management
"""
import json
from typing import Any, Optional
import redis.asyncio as redis

from app.config import get_settings


settings = get_settings()

# Redis client
redis_client: Optional[redis.Redis] = None


async def init_redis():
    """Initialize Redis connection."""
    global redis_client
    redis_client = redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True
    )


async def close_redis():
    """Close Redis connection."""
    global redis_client
    if redis_client:
        await redis_client.close()


def get_redis() -> redis.Redis:
    """Get Redis client."""
    if not redis_client:
        raise RuntimeError("Redis client not initialized")
    return redis_client


class RuleCache:
    """Cache for hot rules - frequently accessed user preferences."""
    
    PREFIX = "rules:"
    TTL = 3600  # 1 hour
    
    @classmethod
    async def get_user_rules(cls, user_id: str) -> Optional[list]:
        """Get cached rules for a user."""
        client = get_redis()
        data = await client.get(f"{cls.PREFIX}{user_id}")
        if data:
            return json.loads(data)
        return None
    
    @classmethod
    async def set_user_rules(cls, user_id: str, rules: list):
        """Cache rules for a user."""
        client = get_redis()
        await client.setex(
            f"{cls.PREFIX}{user_id}",
            cls.TTL,
            json.dumps(rules)
        )
    
    @classmethod
    async def invalidate_user_rules(cls, user_id: str):
        """Invalidate cached rules for a user."""
        client = get_redis()
        await client.delete(f"{cls.PREFIX}{user_id}")


class ConversationCache:
    """Cache for conversation context."""
    
    PREFIX = "conv:"
    TTL = 7200  # 2 hours
    
    @classmethod
    async def get_context(cls, conversation_id: str) -> Optional[list]:
        """Get cached conversation context."""
        client = get_redis()
        data = await client.get(f"{cls.PREFIX}{conversation_id}")
        if data:
            return json.loads(data)
        return None
    
    @classmethod
    async def set_context(cls, conversation_id: str, messages: list):
        """Cache conversation context."""
        client = get_redis()
        await client.setex(
            f"{cls.PREFIX}{conversation_id}",
            cls.TTL,
            json.dumps(messages)
        )
    
    @classmethod
    async def append_message(cls, conversation_id: str, message: dict):
        """Append a message to conversation context."""
        client = get_redis()
        context = await cls.get_context(conversation_id) or []
        context.append(message)
        # Keep last 20 messages for context
        context = context[-20:]
        await cls.set_context(conversation_id, context)
