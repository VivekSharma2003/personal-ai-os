"""
Personal AI OS - Notification Digest Background Job

Generates daily digest notifications for all users with recent activity.
"""
from app.db.session import async_session_maker
from app.services.notification_service import NotificationService
from app.core.logging import get_logger
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta

logger = get_logger("jobs.notification_digest")


async def generate_daily_digests():
    """
    Generate daily digest notifications for all users with
    recent audit log activity in the last 24 hours.
    """
    from app.models.audit_log import AuditLog

    since = datetime.utcnow() - timedelta(days=1)

    async with async_session_maker() as db:
        try:
            # Find all users with recent activity
            result = await db.execute(
                select(AuditLog.user_id)
                .where(AuditLog.created_at >= since)
                .group_by(AuditLog.user_id)
            )
            active_user_ids = [row[0] for row in result.fetchall()]

            if not active_user_ids:
                logger.info("No active users for digest generation")
                return

            generated = 0
            for user_id in active_user_ids:
                try:
                    service = NotificationService(db)
                    await service.generate_digest(user_id)
                    generated += 1
                except Exception as e:
                    logger.error(
                        f"Failed to generate digest for user {user_id}: {e}",
                        extra={"extra_data": {"user_id": str(user_id)}},
                    )

            await db.commit()

            logger.info(
                "Daily digests generated",
                extra={"extra_data": {
                    "users_processed": len(active_user_ids),
                    "digests_generated": generated,
                }},
            )

        except Exception as e:
            logger.error(f"Digest job failed: {e}")
            await db.rollback()
