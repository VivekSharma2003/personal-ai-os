"""
Personal AI OS - Rule Effectiveness Background Job

Batch-recomputes effectiveness scores for all users daily.
"""
from app.db.session import async_session_maker
from app.services.effectiveness_service import EffectivenessService
from app.models.user import User
from sqlalchemy import select
from app.core.logging import get_logger

logger = get_logger("jobs.effectiveness")


async def compute_effectiveness_scores():
    """
    Iterate over all users and recompute rule effectiveness scores.

    Runs daily at 4 AM via the scheduler.
    """
    async with async_session_maker() as session:
        try:
            result = await session.execute(select(User))
            users = result.scalars().all()

            total_rules = 0
            for user in users:
                service = EffectivenessService(session)
                count = await service.batch_compute(user.id)
                total_rules += count

            logger.info(
                "Effectiveness batch compute complete",
                extra={"extra_data": {
                    "users_processed": len(users),
                    "rules_processed": total_rules,
                }},
            )
        except Exception as e:
            logger.error(
                f"Effectiveness batch compute failed: {e}",
                exc_info=True,
            )
