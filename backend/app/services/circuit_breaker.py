"""
Personal AI OS - Circuit Breaker Service

Tracks consecutive failures per provider/endpoint in Redis and automatically
opens (blocks) the circuit when failures exceed a threshold, giving the
downstream service time to recover.

States
------
CLOSED  — normal operation, requests flow through
OPEN    — circuit tripped; calls are rejected immediately
HALF_OPEN — probe window; one request is allowed through to test recovery

Usage in a route/service
------------------------
    cb = CircuitBreaker("openai", "gpt-4o")
    if await cb.is_open():
        raise HTTPException(503, "Circuit open – provider temporarily unavailable")
    try:
        result = await call_provider(...)
        await cb.record_success()
    except ProviderError:
        await cb.record_failure()
        raise
"""
import json
import logging
import time
from typing import Literal

from app.db.redis import get_redis

logger = logging.getLogger(__name__)

State = Literal["CLOSED", "OPEN", "HALF_OPEN"]

_FAILURE_THRESHOLD = 5      # failures before opening
_RECOVERY_TIMEOUT = 60      # seconds before attempting HALF_OPEN
_HALF_OPEN_SUCCESS = 2      # successes needed to close again
_KEY_PREFIX = "cb"


class CircuitBreaker:
    def __init__(
        self,
        service: str,
        resource: str = "default",
        failure_threshold: int = _FAILURE_THRESHOLD,
        recovery_timeout: int = _RECOVERY_TIMEOUT,
        half_open_success_threshold: int = _HALF_OPEN_SUCCESS,
    ):
        self.service = service
        self.resource = resource
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_success_threshold = half_open_success_threshold
        self._state_key = f"{_KEY_PREFIX}:{service}:{resource}:state"
        self._failures_key = f"{_KEY_PREFIX}:{service}:{resource}:failures"
        self._opened_at_key = f"{_KEY_PREFIX}:{service}:{resource}:opened_at"
        self._half_successes_key = f"{_KEY_PREFIX}:{service}:{resource}:half_successes"

    async def _get_state(self) -> State:
        redis = get_redis()
        raw = await redis.get(self._state_key)
        return raw if raw in ("CLOSED", "OPEN", "HALF_OPEN") else "CLOSED"

    async def _set_state(self, state: State, ttl: int = 3600) -> None:
        redis = get_redis()
        await redis.set(self._state_key, state, ex=ttl)

    async def get_status(self) -> dict:
        redis = get_redis()
        state = await self._get_state()
        failures = int(await redis.get(self._failures_key) or 0)
        opened_at = await redis.get(self._opened_at_key)
        return {
            "service": self.service,
            "resource": self.resource,
            "state": state,
            "failures": failures,
            "opened_at": float(opened_at) if opened_at else None,
        }

    async def is_open(self) -> bool:
        """Returns True if the circuit is open (calls should be rejected)."""
        redis = get_redis()
        state = await self._get_state()

        if state == "CLOSED":
            return False

        if state == "OPEN":
            opened_at = float(await redis.get(self._opened_at_key) or 0)
            if time.time() - opened_at >= self.recovery_timeout:
                # Transition to HALF_OPEN for probe
                await self._set_state("HALF_OPEN")
                await redis.set(self._half_successes_key, 0, ex=3600)
                return False   # allow one probe request
            return True

        # HALF_OPEN — allow probe
        return False

    async def record_success(self) -> None:
        redis = get_redis()
        state = await self._get_state()
        if state == "HALF_OPEN":
            successes = await redis.incr(self._half_successes_key)
            if successes >= self.half_open_success_threshold:
                await self._reset()
                logger.info(f"Circuit CLOSED for {self.service}/{self.resource}")
        elif state == "CLOSED":
            # Reset failure counter on success
            await redis.set(self._failures_key, 0, ex=3600)

    async def record_failure(self) -> None:
        redis = get_redis()
        failures = await redis.incr(self._failures_key)
        await redis.expire(self._failures_key, 3600)

        if failures >= self.failure_threshold:
            await self._set_state("OPEN")
            await redis.set(self._opened_at_key, time.time(), ex=3600)
            logger.warning(f"Circuit OPENED for {self.service}/{self.resource} after {failures} failures")

    async def _reset(self) -> None:
        redis = get_redis()
        await self._set_state("CLOSED")
        await redis.set(self._failures_key, 0, ex=3600)
        await redis.delete(self._opened_at_key)
        await redis.delete(self._half_successes_key)

    async def force_open(self) -> None:
        """Manually trip the circuit (e.g. during maintenance)."""
        redis = get_redis()
        await self._set_state("OPEN")
        await redis.set(self._opened_at_key, time.time(), ex=3600)

    async def force_close(self) -> None:
        """Manually reset the circuit."""
        await self._reset()
