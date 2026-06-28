"""
Personal AI OS - Rule Lifecycle Service

Automated rule lifecycle management: stale detection, auto-archival,
resurrection of archived rules, and lifecycle analytics.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rule import Rule, RuleStatus
from app.models.audit_log import AuditLog
from app.core.logging import get_logger
from app.config import get_settings

logger = get_logger("services.lifecycle")


class LifecycleService:
    """Service for automated rule lifecycle management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def scan_for_stale_rules(
        self,
        user_id: UUID,
        inactive_days: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find rules that haven't been applied in N days
        with declining confidence (below 0.4).
        """
        settings = get_settings()
        days = inactive_days or settings.lifecycle_stale_days
        cutoff = datetime.utcnow() - timedelta(days=days)

        q = select(Rule).where(
            and_(
                Rule.user_id == user_id,
                Rule.status == RuleStatus.ACTIVE.value,
                Rule.confidence < 0.4,
                # Either never applied, or last applied before cutoff
                (Rule.last_applied_at == None) | (Rule.last_applied_at < cutoff),
            )
        ).order_by(Rule.confidence.asc())

        result = await self.db.execute(q)
        stale_rules = result.scalars().all()

        return [
            {
                **r.to_dict(),
                "days_inactive": (datetime.utcnow() - r.last_applied_at).days if r.last_applied_at else (datetime.utcnow() - r.created_at).days,
                "reason": self._stale_reason(r, cutoff),
            }
            for r in stale_rules
        ]

    async def auto_archive(self, user_id: UUID) -> Dict[str, Any]:
        """
        Archive all stale rules for a user.
        Creates audit log entries and returns archive report.
        """
        settings = get_settings()
        if not settings.lifecycle_auto_archive:
            return {"archived_count": 0, "skipped": True, "reason": "Auto-archive disabled"}

        stale_rules = await self.scan_for_stale_rules(user_id)
        archived = []

        for rule_data in stale_rules:
            rule = await self.db.get(Rule, UUID(rule_data["id"]))
            if rule and rule.status == RuleStatus.ACTIVE.value:
                rule.status = RuleStatus.ARCHIVED.value
                rule.updated_at = datetime.utcnow()

                # Create audit entry
                audit = AuditLog(
                    user_id=user_id,
                    rule_id=rule.id,
                    event_type="rule.auto_archived",
                    event_data={"details": f"Auto-archived: {rule_data['reason']}"},
                )
                self.db.add(audit)
                archived.append(rule_data["id"])

        await self.db.flush()

        if archived:
            logger.info(f"Auto-archived {len(archived)} stale rules", extra={"extra_data": {
                "user_id": str(user_id),
                "archived_count": len(archived),
            }})

        return {
            "archived_count": len(archived),
            "archived_rule_ids": archived,
            "scanned_stale": len(stale_rules),
        }

    async def resurrect_rule(self, rule_id: UUID) -> Dict[str, Any]:
        """
        Move an archived rule back to active with a confidence bump.
        Emits a lifecycle event.
        """
        rule = await self.db.get(Rule, rule_id)
        if not rule:
            raise ValueError("Rule not found")

        if rule.status != RuleStatus.ARCHIVED.value:
            raise ValueError("Only archived rules can be resurrected")

        old_confidence = rule.confidence
        rule.status = RuleStatus.ACTIVE.value
        rule.confidence = min(1.0, rule.confidence + 0.15)  # Confidence bump on resurrection
        rule.updated_at = datetime.utcnow()

        # Audit entry
        audit = AuditLog(
            user_id=rule.user_id,
            rule_id=rule.id,
            event_type="rule.resurrected",
            event_data={"details": f"Resurrected: confidence {old_confidence:.2f} → {rule.confidence:.2f}"},
        )
        self.db.add(audit)
        await self.db.flush()

        logger.info(f"Resurrected rule {rule_id}", extra={"extra_data": {
            "rule_id": str(rule_id),
            "old_confidence": old_confidence,
            "new_confidence": rule.confidence,
        }})

        return rule.to_dict()

    async def get_lifecycle_report(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get lifecycle analytics for the user's rules.
        """
        # Count by status
        status_q = select(
            Rule.status,
            func.count(Rule.id).label("count"),
        ).where(Rule.user_id == user_id).group_by(Rule.status)
        status_result = await self.db.execute(status_q)
        status_counts = {row.status: row.count for row in status_result.all()}

        # Average age of active rules
        age_q = select(
            func.avg(func.extract("epoch", func.now() - Rule.created_at) / 86400).label("avg_age_days"),
        ).where(
            and_(Rule.user_id == user_id, Rule.status == RuleStatus.ACTIVE.value)
        )
        age_result = await self.db.execute(age_q)
        avg_age = age_result.scalar() or 0

        # At-risk rules (active but low confidence and not recently applied)
        settings = get_settings()
        risk_cutoff = datetime.utcnow() - timedelta(days=settings.lifecycle_stale_days // 2)
        at_risk_q = select(func.count(Rule.id)).where(
            and_(
                Rule.user_id == user_id,
                Rule.status == RuleStatus.ACTIVE.value,
                Rule.confidence < 0.5,
                (Rule.last_applied_at == None) | (Rule.last_applied_at < risk_cutoff),
            )
        )
        at_risk_result = await self.db.execute(at_risk_q)
        at_risk_count = at_risk_result.scalar() or 0

        # Recent lifecycle events
        events_q = select(AuditLog).where(
            and_(
                AuditLog.user_id == user_id,
                AuditLog.event_type.in_(["rule.auto_archived", "rule.resurrected"]),
            )
        ).order_by(AuditLog.created_at.desc()).limit(20)
        events_result = await self.db.execute(events_q)
        recent_events = [
            {
                "event_type": e.event_type,
                "rule_id": str(e.rule_id) if e.rule_id else None,
                "details": e.event_data.get("details", "") if isinstance(e.event_data, dict) else "",
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events_result.scalars().all()
        ]

        return {
            "status_counts": {
                "active": status_counts.get(RuleStatus.ACTIVE.value, 0),
                "archived": status_counts.get(RuleStatus.ARCHIVED.value, 0),
                "disabled": status_counts.get(RuleStatus.DISABLED.value, 0),
            },
            "total_rules": sum(status_counts.values()),
            "avg_age_days": round(avg_age, 1),
            "at_risk_count": at_risk_count,
            "recent_lifecycle_events": recent_events,
        }

    async def get_rule_timeline(self, rule_id: UUID) -> List[Dict[str, Any]]:
        """Get chronological lifecycle events for a specific rule."""
        q = select(AuditLog).where(
            AuditLog.rule_id == rule_id
        ).order_by(AuditLog.created_at.asc())
        result = await self.db.execute(q)

        return [
            {
                "event_type": e.event_type,
                "details": e.event_data.get("details", "") if isinstance(e.event_data, dict) else "",
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in result.scalars().all()
        ]

    @staticmethod
    def _stale_reason(rule: Rule, cutoff: datetime) -> str:
        """Generate human-readable reason for staleness."""
        reasons = []
        if rule.confidence < 0.3:
            reasons.append(f"very low confidence ({rule.confidence:.2f})")
        elif rule.confidence < 0.4:
            reasons.append(f"low confidence ({rule.confidence:.2f})")

        if rule.last_applied_at is None:
            reasons.append("never applied")
        elif rule.last_applied_at < cutoff:
            days = (datetime.utcnow() - rule.last_applied_at).days
            reasons.append(f"inactive for {days} days")

        return "; ".join(reasons) if reasons else "stale"
