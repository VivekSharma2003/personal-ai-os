"""
Personal AI OS - Background Job Tracker

In-memory tracking of background job executions with a ring buffer
for recent history, plus a decorator to wrap job functions.
"""
import asyncio
import time
import functools
from collections import deque, defaultdict
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from app.core.logging import get_logger

logger = get_logger("core.job_tracker")


class JobRun:
    """Record of a single job execution."""

    __slots__ = ("job_id", "started_at", "finished_at", "status", "duration_ms", "detail")

    def __init__(
        self,
        job_id: str,
        started_at: str,
        finished_at: str,
        status: str,
        duration_ms: float,
        detail: Optional[str] = None,
    ):
        self.job_id = job_id
        self.started_at = started_at
        self.finished_at = finished_at
        self.status = status
        self.duration_ms = duration_ms
        self.detail = detail

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "status": self.status,
            "duration_ms": round(self.duration_ms, 2),
            "detail": self.detail,
        }


class JobTracker:
    """
    Singleton that tracks background job executions.

    Stores the last `max_runs` executions per job in a ring buffer.
    Thread-safe via asyncio (single-threaded event loop).
    """

    _instance: Optional["JobTracker"] = None
    _runs: Dict[str, deque]
    _stats: Dict[str, Dict[str, Any]]

    MAX_RUNS = 100  # per job

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._runs = defaultdict(lambda: deque(maxlen=cls.MAX_RUNS))
            cls._instance._stats = defaultdict(
                lambda: {
                    "total_runs": 0,
                    "success_count": 0,
                    "failure_count": 0,
                    "total_duration_ms": 0.0,
                    "last_run_at": None,
                    "last_status": None,
                }
            )
        return cls._instance

    def record_run(
        self,
        job_id: str,
        status: str,
        duration_ms: float,
        detail: Optional[str] = None,
    ):
        """Record a completed job run."""
        now = datetime.utcnow().isoformat()
        run = JobRun(
            job_id=job_id,
            started_at=now,
            finished_at=now,
            status=status,
            duration_ms=duration_ms,
            detail=detail,
        )

        self._runs[job_id].append(run)

        # Update aggregate stats
        stats = self._stats[job_id]
        stats["total_runs"] += 1
        stats["total_duration_ms"] += duration_ms
        stats["last_run_at"] = now
        stats["last_status"] = status
        if status == "success":
            stats["success_count"] += 1
        else:
            stats["failure_count"] += 1

    def get_runs(self, job_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent runs for a job, most recent first."""
        runs = list(self._runs.get(job_id, []))
        runs.reverse()
        return [r.to_dict() for r in runs[:limit]]

    def get_stats(self, job_id: str) -> Dict[str, Any]:
        """Get aggregate stats for a job."""
        stats = dict(self._stats[job_id])
        total = stats["total_runs"]
        if total > 0:
            stats["avg_duration_ms"] = round(stats["total_duration_ms"] / total, 2)
            stats["success_rate"] = round(stats["success_count"] / total * 100, 1)
        else:
            stats["avg_duration_ms"] = 0
            stats["success_rate"] = 0
        return stats

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get aggregate stats for all tracked jobs."""
        return {job_id: self.get_stats(job_id) for job_id in self._stats}

    def clear(self):
        """Clear all tracking data. Useful for testing."""
        self._runs.clear()
        self._stats.clear()


# Module-level singleton accessor
_tracker: Optional[JobTracker] = None


def get_job_tracker() -> JobTracker:
    """Get the global JobTracker singleton."""
    global _tracker
    if _tracker is None:
        _tracker = JobTracker()
    return _tracker


def tracked_job(func: Callable) -> Callable:
    """
    Decorator that wraps an async job function with timing and error capture.

    Usage:
        @tracked_job
        async def my_background_job():
            ...
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        tracker = get_job_tracker()
        job_id = func.__name__
        start = time.time()

        try:
            result = await func(*args, **kwargs)
            duration_ms = (time.time() - start) * 1000
            tracker.record_run(job_id, "success", duration_ms)
            logger.info(
                f"Job '{job_id}' completed in {duration_ms:.1f}ms",
                extra={"extra_data": {"job_id": job_id, "duration_ms": round(duration_ms, 2)}},
            )
            return result
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            tracker.record_run(job_id, "failure", duration_ms, detail=str(e))
            logger.error(
                f"Job '{job_id}' failed after {duration_ms:.1f}ms: {e}",
                exc_info=True,
                extra={"extra_data": {"job_id": job_id}},
            )
            # Don't re-raise — APScheduler will log it anyway
            return None

    return wrapper
