"""
Personal AI OS - Data Retention Cleanup Background Job

Runs daily to purge expired records per user retention policies.
"""
from app.db.session import async_session_maker
from app.services.retention_service import RetentionService
from app.models.user import User
from sqlalchemy import select
from app.core.logging import get_logger

logger = get_logger("jobs.retention")


async def run_retention_cleanup():
    """
    Iterate over all users and apply their retention policies.

    Runs daily at 2 AM via the scheduler.
    """
    async with async_session_maker() as session:
        try:
            result = await session.execute(select(User))
            users = result.scalars().all()

            total_deleted = {}
            for user in users:
                service = RetentionService(session)
                deleted = await service.execute_cleanup(user.id)
                for resource_type, count in deleted.items():
                    total_deleted[resource_type] = (
                        total_deleted.get(resource_type, 0) + count
                    )

            await session.commit()

            logger.info(
                "Retention cleanup complete",
                extra={"extra_data": {
                    "users_processed": len(users),
                    "deleted": total_deleted,
                }},
            )
        except Exception as e:
            await session.rollback()
            logger.error(
                f"Retention cleanup failed: {e}",
                exc_info=True,
            )
