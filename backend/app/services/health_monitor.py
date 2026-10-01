"""
Personal AI OS - Health Monitor Service

Runs system health checks, persists snapshots, and queries history/trends.
"""
import logging
import time
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, text, func

from app.db.redis import get_redis
from app.models.health_snapshot import HealthSnapshot

logger = logging.getLogger(__name__)


class HealthMonitorService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------ #
    # Probes                                                               #
    # ------------------------------------------------------------------ #

    async def _probe_db(self) -> tuple[bool, float]:
        """Ping the database and return (ok, latency_ms)."""
        try:
            t0 = time.perf_counter()
            await self.db.execute(text("SELECT 1"))
            ms = (time.perf_counter() - t0) * 1000
            return True, round(ms, 2)
        except Exception as exc:
            logger.error(f"DB health probe failed: {exc}")
            return False, -1.0

    async def _probe_redis(self) -> tuple[bool, float]:
        """Ping Redis and return (ok, latency_ms)."""
        try:
            redis = get_redis()
            t0 = time.perf_counter()
            await redis.ping()
            ms = (time.perf_counter() - t0) * 1000
            return True, round(ms, 2)
        except Exception as exc:
            logger.error(f"Redis health probe failed: {exc}")
            return False, -1.0

    async def _probe_active_rules(self) -> Optional[int]:
        """Count active rules across all users."""
        try:
            from app.models.rule import Rule, RuleStatus
            result = await self.db.execute(
                select(func.count()).where(Rule.status == RuleStatus.ACTIVE.value)
            )
            return result.scalar()
        except Exception:
            return None

    # ------------------------------------------------------------------ #
    # Snapshot                                                             #
    # ------------------------------------------------------------------ #

    async def run_and_store(self) -> HealthSnapshot:
        """Execute all probes, persist a snapshot, and return it."""
        db_ok, db_ms = await self._probe_db()
        redis_ok, redis_ms = await self._probe_redis()
        active_rules = await self._probe_active_rules()

        healthy = db_ok and redis_ok

        snapshot = HealthSnapshot(
            db_ok=db_ok,
            redis_ok=redis_ok,
            db_latency_ms=db_ms,
            redis_latency_ms=redis_ms,
            active_rules_count=active_rules,
            healthy=healthy,
            detail={
                "db_latency_ms": db_ms,
                "redis_latency_ms": redis_ms,
                "active_rules": active_rules,
            },
        )
        self.db.add(snapshot)
        await self.db.commit()
        await self.db.refresh(snapshot)

        if not healthy:
            logger.warning(f"System UNHEALTHY: db={db_ok} redis={redis_ok}")

        return snapshot

    # ------------------------------------------------------------------ #
    # History                                                              #
    # ------------------------------------------------------------------ #

    async def get_recent(self, limit: int = 20) -> List[HealthSnapshot]:
        """Return the most recent *limit* snapshots, newest first."""
        result = await self.db.execute(
            select(HealthSnapshot).order_by(desc(HealthSnapshot.checked_at)).limit(limit)
        )
        return result.scalars().all()

    async def get_latest(self) -> Optional[HealthSnapshot]:
        result = await self.db.execute(
            select(HealthSnapshot).order_by(desc(HealthSnapshot.checked_at)).limit(1)
        )
        return result.scalars().first()

    async def unhealthy_count(self, last_n: int = 10) -> int:
        """Return how many of the last *last_n* snapshots were unhealthy."""
        result = await self.db.execute(
            select(func.count())
            .select_from(
                select(HealthSnapshot.id)
                .where(HealthSnapshot.healthy.is_(False))
                .order_by(desc(HealthSnapshot.checked_at))
                .limit(last_n)
                .subquery()
            )
        )
        return result.scalar() or 0
