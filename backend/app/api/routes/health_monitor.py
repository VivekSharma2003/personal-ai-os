"""
Personal AI OS - Health Monitor Routes

POST /api/health-monitor/run       — trigger a health check now and store it
GET  /api/health-monitor/latest    — most recent snapshot
GET  /api/health-monitor/history   — last N snapshots
GET  /api/health-monitor/status    — simple overall ok/degraded/critical
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.services.health_monitor import HealthMonitorService

router = APIRouter(prefix="/api/health-monitor", tags=["Health Monitor"])


def _snap_to_dict(snap) -> dict:
    return {
        "id": str(snap.id),
        "checked_at": snap.checked_at.isoformat() if snap.checked_at else None,
        "db_ok": snap.db_ok,
        "redis_ok": snap.redis_ok,
        "db_latency_ms": snap.db_latency_ms,
        "redis_latency_ms": snap.redis_latency_ms,
        "active_rules_count": snap.active_rules_count,
        "healthy": snap.healthy,
        "detail": snap.detail,
    }


@router.post("/run")
async def run_health_check(db: AsyncSession = Depends(get_db)):
    """Immediately run all health probes and persist the snapshot."""
    service = HealthMonitorService(db)
    snap = await service.run_and_store()
    return _snap_to_dict(snap)


@router.get("/latest")
async def latest_snapshot(db: AsyncSession = Depends(get_db)):
    """Return the most recently stored health snapshot."""
    service = HealthMonitorService(db)
    snap = await service.get_latest()
    if snap is None:
        return {"message": "No snapshots yet. POST /run to create one."}
    return _snap_to_dict(snap)


@router.get("/history")
async def snapshot_history(
    limit: int = Query(default=20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Return the last *limit* health snapshots, newest first."""
    service = HealthMonitorService(db)
    snaps = await service.get_recent(limit)
    return [_snap_to_dict(s) for s in snaps]


@router.get("/status")
async def system_status(db: AsyncSession = Depends(get_db)):
    """
    Returns a single human-readable status string:
    - "healthy"   — latest snapshot is fully green
    - "degraded"  — latest snapshot has partial failures
    - "critical"  — 3+ of the last 5 snapshots are unhealthy
    - "unknown"   — no snapshots yet
    """
    service = HealthMonitorService(db)
    latest = await service.get_latest()
    if latest is None:
        return {"status": "unknown"}

    unhealthy_recent = await service.unhealthy_count(last_n=5)

    if unhealthy_recent >= 3:
        status = "critical"
    elif not latest.healthy:
        status = "degraded"
    else:
        status = "healthy"

    return {"status": status, "latest": _snap_to_dict(latest)}
