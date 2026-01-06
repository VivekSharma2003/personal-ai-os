"""
Personal AI OS - Background Job Scheduler

Uses APScheduler for periodic job execution.
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.jobs.decay_processor import process_decay
from app.jobs.rule_extractor import process_pending_extractions


# Global scheduler instance
scheduler: AsyncIOScheduler = None


async def start_scheduler():
    """Initialize and start the background job scheduler."""
    global scheduler
    
    scheduler = AsyncIOScheduler()
    
    # Decay processor - runs daily at 3 AM
    scheduler.add_job(
        process_decay,
        trigger=CronTrigger(hour=3, minute=0),
        id="decay_processor",
        name="Rule Confidence Decay Processor",
        replace_existing=True
    )
    
    # Rule extractor - runs every 30 minutes
    scheduler.add_job(
        process_pending_extractions,
        trigger=IntervalTrigger(minutes=30),
        id="rule_extractor",
        name="Pending Rule Extractor",
        replace_existing=True
    )
    
    scheduler.start()
    print("[Scheduler] Background jobs started")


async def stop_scheduler():
    """Stop the background job scheduler."""
    global scheduler
    
    if scheduler:
        scheduler.shutdown(wait=False)
        print("[Scheduler] Background jobs stopped")


def get_scheduler() -> AsyncIOScheduler:
    """Get the scheduler instance."""
    return scheduler
