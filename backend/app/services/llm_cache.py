"""
Personal AI OS - LLM Response Cache Service

Redis-backed cache keyed on SHA-256(provider:model:prompt).
Avoids duplicate LLM calls for identical prompts within the TTL window.
"""
import hashlib
import json
import logging
from typing import Optional

from app.db.redis import get_redis

logger = logging.getLogger(__name__)

_DEFAULT_TTL = 3600  # 1 hour


class LLMCacheService:
    """
    Try/store cache pattern:

        cached = await cache.get(provider, model, prompt)
        if cached:
            return cached
        result = await llm.call(prompt)
        await cache.store(provider, model, prompt, result)
        return result
    """

    def _build_key(self, provider: str, model: str, prompt: str) -> str:
        fingerprint = hashlib.sha256(
            f"{provider}:{model}:{prompt}".encode()
        ).hexdigest()
        return f"llm_cache:{fingerprint}"

    async def get(self, provider: str, model: str, prompt: str) -> Optional[str]:
        """Return cached response, or None on miss."""
        redis = get_redis()
        key = self._build_key(provider, model, prompt)
        raw = await redis.get(key)
        if raw is None:
            logger.debug(f"Cache MISS  key={key[:16]}...")
            return None
        logger.debug(f"Cache HIT   key={key[:16]}...")
        return json.loads(raw)["response"]

    async def store(
        self,
        provider: str,
        model: str,
        prompt: str,
        response: str,
        ttl: int = _DEFAULT_TTL,
    ) -> None:
        """Persist a response for *ttl* seconds."""
        redis = get_redis()
        key = self._build_key(provider, model, prompt)
        payload = json.dumps({"response": response})
        await redis.set(key, payload, ex=ttl)
        logger.debug(f"Cache STORE key={key[:16]}... ttl={ttl}s")

    async def invalidate(self, provider: str, model: str, prompt: str) -> bool:
        """Delete a specific cached entry. Returns True if it existed."""
        redis = get_redis()
        key = self._build_key(provider, model, prompt)
        deleted = await redis.delete(key)
        return bool(deleted)

    async def flush_all(self) -> int:
        """
        Flush every llm_cache:* key (e.g. after a model rollout).
        Returns the count of deleted keys.
        """
        redis = get_redis()
        keys = await redis.keys("llm_cache:*")
        if not keys:
            return 0
        return await redis.delete(*keys)

    async def stats(self) -> dict:
        """Return the current number of cached entries."""
        redis = get_redis()
        keys = await redis.keys("llm_cache:*")
        return {"cached_entries": len(keys)}
