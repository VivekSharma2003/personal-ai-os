"""
Personal AI OS - Background Job Scheduler

Uses APScheduler for periodic job execution.
All jobs are wrapped with the @tracked_job decorator for observability.
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.job_tracker import tracked_job
from app.core.logging import get_logger
from app.config import get_settings

logger = get_logger("jobs.scheduler")

# --- Wrap existing jobs with tracking ---

from app.jobs.decay_processor import process_decay
from app.jobs.rule_extractor import process_pending_extractions
from app.jobs.conflict_scanner import scan_conflicts
from app.jobs.webhook_dispatcher import retry_failed_webhooks
from app.jobs.effectiveness_job import compute_effectiveness_scores
from app.jobs.retention_job import run_retention_cleanup
from app.jobs.lifecycle_job import run_lifecycle_scan
from app.jobs.notification_job import generate_daily_digests


@tracked_job
async def _tracked_decay():
    await process_decay()


@tracked_job
async def _tracked_extractions():
    await process_pending_extractions()


@tracked_job
async def _tracked_conflicts():
    await scan_conflicts()


@tracked_job
async def _tracked_webhooks():
    await retry_failed_webhooks()


@tracked_job
async def _tracked_effectiveness():
    await compute_effectiveness_scores()


@tracked_job
async def _tracked_retention():
    await run_retention_cleanup()


@tracked_job
async def _tracked_lifecycle():
    await run_lifecycle_scan()


@tracked_job
async def _tracked_digests():
    await generate_daily_digests()


# Global scheduler instance
scheduler: AsyncIOScheduler = None


async def start_scheduler():
    """Initialize and start the background job scheduler."""
    global scheduler
    settings = get_settings()

    scheduler = AsyncIOScheduler()

    # Decay processor - runs daily at 3 AM
    scheduler.add_job(
        _tracked_decay,
        trigger=CronTrigger(hour=3, minute=0),
        id="decay_processor",
        name="Rule Confidence Decay Processor",
        replace_existing=True
    )

    # Rule extractor - runs every 30 minutes
    scheduler.add_job(
        _tracked_extractions,
        trigger=IntervalTrigger(minutes=30),
        id="rule_extractor",
        name="Pending Rule Extractor",
        replace_existing=True
    )

    # Conflict scanner - runs every N hours (default 6)
    scheduler.add_job(
        _tracked_conflicts,
        trigger=IntervalTrigger(hours=settings.conflict_scan_interval),
        id="conflict_scanner",
        name="Rule Conflict Scanner",
        replace_existing=True
    )

    # Webhook retry dispatcher - runs every 5 minutes
    scheduler.add_job(
        _tracked_webhooks,
        trigger=IntervalTrigger(minutes=5),
        id="webhook_dispatcher",
        name="Webhook Retry Dispatcher",
        replace_existing=True
    )

    # Effectiveness scorer - runs daily at 4 AM
    scheduler.add_job(
        _tracked_effectiveness,
        trigger=CronTrigger(hour=4, minute=0),
        id="effectiveness_scorer",
        name="Rule Effectiveness Scorer",
        replace_existing=True
    )

    # Retention cleanup - runs daily at 2 AM
    scheduler.add_job(
        _tracked_retention,
        trigger=CronTrigger(hour=2, minute=0),
        id="retention_cleanup",
        name="Data Retention Cleanup",
        replace_existing=True
    )

    # Lifecycle manager - runs daily at 5 AM
    scheduler.add_job(
        _tracked_lifecycle,
        trigger=CronTrigger(hour=5, minute=0),
        id="lifecycle_manager",
        name="Rule Lifecycle Manager",
        replace_existing=True
    )

    # Notification digest - runs daily at configured hour (default 8 AM)
    scheduler.add_job(
        _tracked_digests,
        trigger=CronTrigger(hour=settings.notification_digest_hour, minute=0),
        id="notification_digest",
        name="Notification Digest Generator",
        replace_existing=True
    )

    scheduler.start()
    logger.info("Background jobs started", extra={"extra_data": {
        "job_count": len(scheduler.get_jobs()),
    }})


async def stop_scheduler():
    """Stop the background job scheduler."""
    global scheduler
    
    if scheduler:
        scheduler.shutdown(wait=False)
        logger.info("Background jobs stopped")


def get_scheduler() -> AsyncIOScheduler:
    """Get the scheduler instance."""
    return scheduler
