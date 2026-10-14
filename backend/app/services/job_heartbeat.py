"""
Personal AI OS - Job Heartbeat Watchdog Service

Long-running jobs call `beat()` periodically.  The watchdog queries Redis
for all registered jobs and flags any whose last heartbeat exceeds the
configured staleness threshold — indicating a hung or crashed job.

Pattern used by a background job
---------------------------------
    watchdog = JobHeartbeat("embedding_indexer", job_id="run-42")
    await watchdog.start()          # registers the job
    try:
        for batch in batches:
            await process(batch)
            await watchdog.beat()   # keeps it alive
    finally:
        await watchdog.finish()     # removes it from active registry
"""
import json
import logging
import time
from typing import List, Dict, Any, Optional

from app.db.redis import get_redis

logger = logging.getLogger(__name__)

_KEY_PREFIX = "heartbeat"
_REGISTRY_KEY = "heartbeat:registry"   # sorted set: score = last_beat timestamp
_DEFAULT_TTL = 300                      # 5 minutes max silence before stale
_DEFAULT_INTERVAL = 30                  # expected beat interval (informational)


class JobHeartbeat:
    """Per-job helper. Call from inside the job process."""

    def __init__(self, job_name: str, job_id: str, ttl: int = _DEFAULT_TTL):
        self.job_name = job_name
        self.job_id = job_id
        self.ttl = ttl
        self._meta_key = f"{_KEY_PREFIX}:{job_name}:{job_id}"

    @property
    def _registry_member(self) -> str:
        return f"{self.job_name}:{self.job_id}"

    async def start(self, metadata: Optional[Dict] = None) -> None:
        """Register the job as active."""
        redis = get_redis()
        now = time.time()
        meta = {"job_name": self.job_name, "job_id": self.job_id,
                "started_at": now, "last_beat": now, **(metadata or {})}
        await redis.set(self._meta_key, json.dumps(meta), ex=self.ttl)
        await redis.zadd(_REGISTRY_KEY, {self._registry_member: now})
        logger.info(f"Heartbeat START job={self._registry_member}")

    async def beat(self) -> None:
        """Refresh the heartbeat (call this inside the job loop)."""
        redis = get_redis()
        now = time.time()
        raw = await redis.get(self._meta_key)
        if raw:
            meta = json.loads(raw)
            meta["last_beat"] = now
            await redis.set(self._meta_key, json.dumps(meta), ex=self.ttl)
        await redis.zadd(_REGISTRY_KEY, {self._registry_member: now})
        logger.debug(f"Heartbeat BEAT  job={self._registry_member}")

    async def finish(self) -> None:
        """Deregister the job on clean completion."""
        redis = get_redis()
        await redis.delete(self._meta_key)
        await redis.zrem(_REGISTRY_KEY, self._registry_member)
        logger.info(f"Heartbeat DONE  job={self._registry_member}")


class HeartbeatWatchdog:
    """Query-side: inspect all registered jobs and detect stale ones."""

    async def list_active(self) -> List[Dict[str, Any]]:
        """Return all jobs currently in the registry with their metadata."""
        redis = get_redis()
        members = await redis.zrange(_REGISTRY_KEY, 0, -1, withscores=True)
        jobs = []
        for member, score in members:
            meta_key = f"{_KEY_PREFIX}:{member}"
            raw = await redis.get(meta_key)
            if raw:
                jobs.append(json.loads(raw))
            else:
                # Key expired but still in sorted set — clean up
                await redis.zrem(_REGISTRY_KEY, member)
        return jobs

    async def stale_jobs(self, staleness_threshold: int = _DEFAULT_TTL) -> List[Dict[str, Any]]:
        """Return jobs whose last beat is older than *staleness_threshold* seconds."""
        now = time.time()
        cutoff = now - staleness_threshold
        redis = get_redis()
        # Sorted set score = last_beat timestamp; members with score < cutoff are stale
        stale_members = await redis.zrangebyscore(_REGISTRY_KEY, 0, cutoff, withscores=True)
        stale = []
        for member, score in stale_members:
            stale.append({
                "member": member,
                "last_beat": score,
                "seconds_since_beat": round(now - score, 1),
            })
        return stale

    async def evict_stale(self, staleness_threshold: int = _DEFAULT_TTL) -> int:
        """Remove stale jobs from the registry. Returns count removed."""
        redis = get_redis()
        cutoff = time.time() - staleness_threshold
        removed = await redis.zremrangebyscore(_REGISTRY_KEY, 0, cutoff)
        return removed or 0
