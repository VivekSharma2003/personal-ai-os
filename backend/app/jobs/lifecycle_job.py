"""
Personal AI OS - Lifecycle Background Job

Runs daily to auto-archive stale rules for all users.
"""
from sqlalchemy import select, distinct

from app.db.session import async_session_maker
from app.models.rule import Rule
from app.services.lifecycle_service import LifecycleService
from app.core.logging import get_logger

logger = get_logger("jobs.lifecycle")


async def run_lifecycle_scan():
    """Scan all users and auto-archive stale rules."""
    async with async_session_maker() as db:
        try:
            # Get all distinct user IDs that have rules
            q = select(distinct(Rule.user_id))
            result = await db.execute(q)
            user_ids = [row[0] for row in result.all()]

            total_archived = 0
            for user_id in user_ids:
                service = LifecycleService(db)
                report = await service.auto_archive(user_id)
                total_archived += report.get("archived_count", 0)

            await db.commit()

            logger.info(f"Lifecycle scan complete", extra={"extra_data": {
                "users_scanned": len(user_ids),
                "total_archived": total_archived,
            }})

        except Exception as e:
            logger.error(f"Lifecycle scan failed: {e}")
            await db.rollback()
            raise
