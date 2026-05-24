"""
Personal AI OS - Conflict Scanner Background Job

Periodically scans all active rules for conflicts across all users.
"""
from datetime import datetime
from sqlalchemy import select, func

from app.db.session import async_session_maker
from app.models.user import User
from app.models.rule import Rule, RuleStatus
from app.services.conflicts import ConflictService


async def scan_conflicts():
    """
    Background job: Scan all users' active rules for conflicts.

    Runs every 6 hours by default. Only scans users who have
    2+ active rules (minimum needed for a conflict).
    """
    print(f"[ConflictScanner] Starting conflict scan at {datetime.utcnow()}")

    async with async_session_maker() as db:
        try:
            # Find users with 2+ active rules
            result = await db.execute(
                select(Rule.user_id)
                .where(Rule.status == RuleStatus.ACTIVE.value)
                .group_by(Rule.user_id)
                .having(func.count(Rule.id) >= 2)
            )
            user_ids = [row[0] for row in result.all()]

            if not user_ids:
                print("[ConflictScanner] No users with 2+ active rules")
                return

            total_conflicts = 0
            for user_id in user_ids:
                conflict_service = ConflictService(db)
                new_conflicts = await conflict_service.scan_all_user_conflicts(user_id)
                total_conflicts += len(new_conflicts)

            await db.commit()
            print(
                f"[ConflictScanner] Completed: scanned {len(user_ids)} users, "
                f"found {total_conflicts} new conflicts"
            )

        except Exception as e:
            print(f"[ConflictScanner] Error: {e}")
            await db.rollback()
            raise
