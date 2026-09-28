"""
Personal AI OS - Idempotency Key Service

Makes POST endpoints retry-safe by storing responses in Redis under an
Idempotency-Key for a configurable TTL.  Callers supply the key; the service
returns the cached response on duplicate requests instead of re-executing them.
"""
import json
import logging
from typing import Optional

from app.db.redis import get_redis

logger = logging.getLogger(__name__)

_TTL = 86_400  # 24 hours


class IdempotencyService:
    """
    Usage in a route:

        idem = IdempotencyService()
        if key := request.headers.get("Idempotency-Key"):
            cached = await idem.get(key)
            if cached:
                return cached          # replay stored response
        ... do work ...
        result = {...}
        if key:
            await idem.store(key, result)
        return result
    """

    def _redis_key(self, idempotency_key: str) -> str:
        return f"idem:{idempotency_key}"

    async def get(self, idempotency_key: str) -> Optional[dict]:
        """Return the stored response for this key, or None if not seen before."""
        redis = get_redis()
        raw = await redis.get(self._redis_key(idempotency_key))
        if raw is None:
            return None
        logger.debug(f"Idempotency HIT key={idempotency_key[:16]}...")
        return json.loads(raw)

    async def store(
        self, idempotency_key: str, response_body: dict, ttl: int = _TTL
    ) -> None:
        """Persist the response body for *ttl* seconds."""
        redis = get_redis()
        await redis.set(
            self._redis_key(idempotency_key),
            json.dumps(response_body),
            ex=ttl,
        )
        logger.debug(f"Idempotency STORE key={idempotency_key[:16]}... ttl={ttl}s")

    async def delete(self, idempotency_key: str) -> bool:
        """Manually expire a key (e.g. after a confirmed failure)."""
        redis = get_redis()
        deleted = await redis.delete(self._redis_key(idempotency_key))
        return bool(deleted)

    async def exists(self, idempotency_key: str) -> bool:
        redis = get_redis()
        return bool(await redis.exists(self._redis_key(idempotency_key)))
