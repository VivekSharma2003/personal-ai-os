"""
Personal AI OS - Adaptive Rule Compression Job
"""
import logging
from sqlalchemy import select

from app.core.job_tracker import tracked_job
from app.db.session import async_session_maker
from app.models.user import User
from app.services.rule_compressor import RuleCompressorService

logger = logging.getLogger(__name__)

@tracked_job
async def run_rule_compression():
    """
    Periodically scans for users with bloated rule categories and compresses them.
    """
    async with async_session_maker() as db:
        users_res = await db.execute(select(User.id))
        users = users_res.scalars().all()
        
        service = RuleCompressorService(db)
        
        for user_id in users:
            try:
                # For MVP, we'll try to compress the common categories
                for category in ["general", "style", "coding"]:
                    result = await service.compress_category(user_id, category)
                    if result.get("status") == "success":
                        logger.info(f"Compressed {result.get('compressed_count')} rules in category '{category}' for user {user_id}")
            except Exception as e:
                logger.error(f"Error running compression for user {user_id}: {e}")
