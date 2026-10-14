"""
Personal AI OS - Job Heartbeat Routes

GET    /api/heartbeat/jobs             — list all active jobs
GET    /api/heartbeat/stale            — list stale (possibly hung) jobs
POST   /api/heartbeat/{name}/{id}/start  — register a job
POST   /api/heartbeat/{name}/{id}/beat   — refresh heartbeat
POST   /api/heartbeat/{name}/{id}/finish — deregister on completion
DELETE /api/heartbeat/stale            — evict stale job entries
"""
from fastapi import APIRouter, Query

from app.services.job_heartbeat import JobHeartbeat, HeartbeatWatchdog

router = APIRouter(prefix="/api/heartbeat", tags=["Job Heartbeat"])


@router.get("/jobs")
async def list_active_jobs():
    """Return all jobs currently registered with a live heartbeat."""
    watchdog = HeartbeatWatchdog()
    return await watchdog.list_active()


@router.get("/stale")
async def list_stale_jobs(threshold: int = Query(default=300, ge=10)):
    """Return jobs whose heartbeat has not been refreshed within *threshold* seconds."""
    watchdog = HeartbeatWatchdog()
    return await watchdog.stale_jobs(staleness_threshold=threshold)


@router.post("/{name}/{job_id}/start")
async def start_job(name: str, job_id: str):
    """Register a job as active and start tracking its heartbeat."""
    hb = JobHeartbeat(name, job_id)
    await hb.start()
    return {"status": "started", "job": f"{name}:{job_id}"}


@router.post("/{name}/{job_id}/beat")
async def beat_job(name: str, job_id: str):
    """Refresh the heartbeat for an active job."""
    hb = JobHeartbeat(name, job_id)
    await hb.beat()
    return {"status": "beat", "job": f"{name}:{job_id}"}


@router.post("/{name}/{job_id}/finish")
async def finish_job(name: str, job_id: str):
    """Deregister a job on clean completion."""
    hb = JobHeartbeat(name, job_id)
    await hb.finish()
    return {"status": "finished", "job": f"{name}:{job_id}"}


@router.delete("/stale")
async def evict_stale(threshold: int = Query(default=300, ge=10)):
    """Remove stale jobs from the registry."""
    watchdog = HeartbeatWatchdog()
    count = await watchdog.evict_stale(staleness_threshold=threshold)
    return {"evicted": count}
