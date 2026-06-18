"""
Personal AI OS - Background Job Dashboard API Routes
"""
from fastapi import APIRouter, HTTPException
from app.api.schemas.jobs import (
    JobInfoResponse,
    JobListResponse,
    JobHistoryResponse,
    JobRunResponse,
    JobStatsResponse,
)
from app.core.job_tracker import get_job_tracker
from app.jobs.scheduler import get_scheduler


router = APIRouter()


def _get_scheduler_or_404():
    """Get the APScheduler instance, raising 503 if not running."""
    scheduler = get_scheduler()
    if scheduler is None:
        raise HTTPException(status_code=503, detail="Scheduler not initialized")
    return scheduler


@router.get(
    "/jobs",
    response_model=JobListResponse,
    summary="List all background jobs",
)
async def list_jobs():
    """
    List all registered background jobs with their schedule, next run time,
    and aggregate execution stats.
    """
    scheduler = _get_scheduler_or_404()
    tracker = get_job_tracker()

    jobs = []
    for job in scheduler.get_jobs():
        stats_data = tracker.get_stats(job.id)
        stats = JobStatsResponse(**stats_data)

        trigger_str = str(job.trigger) if job.trigger else "unknown"
        next_run = (
            job.next_run_time.isoformat()
            if job.next_run_time
            else None
        )

        jobs.append(
            JobInfoResponse(
                id=job.id,
                name=job.name or job.id,
                trigger=trigger_str,
                next_run_time=next_run,
                is_paused=job.next_run_time is None,
                stats=stats,
            )
        )

    return JobListResponse(jobs=jobs, total=len(jobs))


@router.get(
    "/jobs/{job_id}/history",
    response_model=JobHistoryResponse,
    summary="Get run history for a job",
)
async def get_job_history(job_id: str, limit: int = 20):
    """
    Get the recent execution history for a specific background job,
    including timing and error details.
    """
    tracker = get_job_tracker()
    runs = tracker.get_runs(job_id, limit=limit)
    stats_data = tracker.get_stats(job_id)

    return JobHistoryResponse(
        job_id=job_id,
        runs=[JobRunResponse(**r) for r in runs],
        stats=JobStatsResponse(**stats_data),
    )


@router.post(
    "/jobs/{job_id}/trigger",
    summary="Manually trigger a background job",
)
async def trigger_job(job_id: str):
    """
    Manually trigger a background job to run immediately.

    The job runs asynchronously — this endpoint returns immediately.
    """
    scheduler = _get_scheduler_or_404()

    job = scheduler.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    # Get the wrapped function and run it
    try:
        job.modify(next_run_time=None)
        scheduler.modify_job(job_id, next_run_time=None)
        # Force immediate run by adding a one-shot trigger
        from datetime import datetime
        scheduler.modify_job(job_id, next_run_time=datetime.now(job.next_run_time.tzinfo) if job.next_run_time else datetime.utcnow())
    except Exception:
        # Fallback: just call the function directly
        import asyncio
        func = job.func
        if callable(func):
            asyncio.create_task(func())

    return {"status": "triggered", "job_id": job_id}


@router.patch(
    "/jobs/{job_id}/pause",
    summary="Pause or resume a background job",
)
async def toggle_job_pause(job_id: str):
    """
    Toggle a job between paused and running states.

    When paused, the job will not execute on its schedule.
    """
    scheduler = _get_scheduler_or_404()

    job = scheduler.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    if job.next_run_time is None:
        # Currently paused — resume
        scheduler.resume_job(job_id)
        return {"status": "resumed", "job_id": job_id}
    else:
        # Currently running — pause
        scheduler.pause_job(job_id)
        return {"status": "paused", "job_id": job_id}
