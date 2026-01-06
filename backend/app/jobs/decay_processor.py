"""
Personal AI OS - Decay Processor Background Job

Runs periodically to decay rule confidence and archive unused rules.
"""
import asyncio
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker
from app.models.rule import Rule, RuleStatus
from app.models.audit_log import AuditLog, AuditEventType
from app.core.algorithms import calculate_confidence, should_archive_rule
from app.db.redis import RuleCache


async def process_decay():
    """
    Process confidence decay for all active rules.
    
    This job should run daily to:
    1. Recalculate confidence for all active rules
    2. Archive rules that fall below the threshold
    3. Log all changes for transparency
    """
    print(f"[DecayProcessor] Starting decay processing at {datetime.utcnow()}")
    
    async with async_session_maker() as db:
        try:
            # Get all active rules
            result = await db.execute(
                select(Rule).where(Rule.status == RuleStatus.ACTIVE.value)
            )
            rules = result.scalars().all()
            
            processed = 0
            archived = 0
            users_affected = set()
            
            for rule in rules:
                old_confidence = rule.confidence
                
                # Recalculate confidence
                new_confidence = calculate_confidence(
                    base_confidence=0.5,
                    times_reinforced=rule.times_reinforced,
                    last_applied_at=rule.last_applied_at
                )
                
                # Check if confidence changed significantly
                if abs(new_confidence - old_confidence) > 0.01:
                    rule.confidence = new_confidence
                    rule.updated_at = datetime.utcnow()
                    users_affected.add(rule.user_id)
                    
                    # Log decay event
                    await _log_decay_event(
                        db, rule.user_id, rule.id, 
                        old_confidence, new_confidence
                    )
                    processed += 1
                
                # Check if should be archived
                if should_archive_rule(new_confidence):
                    rule.status = RuleStatus.ARCHIVED.value
                    
                    # Log archive event
                    await _log_archive_event(db, rule.user_id, rule.id)
                    archived += 1
            
            await db.commit()
            
            # Invalidate caches for affected users
            for user_id in users_affected:
                await RuleCache.invalidate_user_rules(str(user_id))
            
            print(f"[DecayProcessor] Completed: {processed} rules decayed, {archived} archived")
            
        except Exception as e:
            print(f"[DecayProcessor] Error: {e}")
            await db.rollback()
            raise


async def _log_decay_event(
    db: AsyncSession,
    user_id,
    rule_id,
    old_confidence: float,
    new_confidence: float
):
    """Log a decay event to the audit log."""
    log = AuditLog(
        user_id=user_id,
        rule_id=rule_id,
        event_type=AuditEventType.RULE_DECAYED.value,
        event_data={
            "old_confidence": round(old_confidence, 2),
            "new_confidence": round(new_confidence, 2),
            "change": round(new_confidence - old_confidence, 2)
        }
    )
    db.add(log)


async def _log_archive_event(db: AsyncSession, user_id, rule_id):
    """Log an archive event to the audit log."""
    log = AuditLog(
        user_id=user_id,
        rule_id=rule_id,
        event_type=AuditEventType.RULE_ARCHIVED.value,
        event_data={"reason": "confidence_decay"}
    )
    db.add(log)
