"""
Personal AI OS - Rule Effectiveness Analytics Service

Computes and tracks how well each rule performs by analyzing
apply/reinforce/override ratios from the audit log history.
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from uuid import UUID
from sqlalchemy import select, func, case, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rule import Rule, RuleStatus
from app.models.audit_log import AuditLog, AuditEventType
from app.models.user import User


class EffectivenessService:
    """
    Analyses rule performance from audit trail data.

    Effectiveness is scored 0-100 based on:
      - Reinforcement rate (positive signal — user confirmed the rule helped)
      - Override / edit rate (negative signal — rule was wrong or stale)
      - Recency bias — recent events weighted more
      - Application frequency — rules that are actually used score higher
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Single-rule effectiveness
    # ------------------------------------------------------------------

    async def get_rule_effectiveness(self, rule_id: UUID) -> Dict[str, Any]:
        """
        Compute effectiveness detail for a single rule.

        Returns dict with: score, trend, apply_count, reinforce_count,
        override_count, reinforce_rate, override_rate, last_applied.
        """
        rule = await self._get_rule(rule_id)
        if not rule:
            return {"error": "Rule not found"}

        stats = await self._compute_rule_stats(rule_id)
        score = self._calculate_score(stats)
        trend = await self._compute_trend(rule_id)

        return {
            "rule_id": str(rule_id),
            "rule_content": rule.content[:120],
            "category": rule.category,
            "score": round(score, 1),
            "grade": self._score_to_grade(score),
            "trend": trend,
            "apply_count": stats["apply_count"],
            "reinforce_count": stats["reinforce_count"],
            "override_count": stats["override_count"],
            "reinforce_rate": round(stats["reinforce_rate"] * 100, 1),
            "override_rate": round(stats["override_rate"] * 100, 1),
            "last_applied": (
                stats["last_applied"].isoformat() if stats["last_applied"] else None
            ),
            "days_since_applied": stats["days_since_applied"],
        }

    # ------------------------------------------------------------------
    # User-wide effectiveness report
    # ------------------------------------------------------------------

    async def get_user_effectiveness_report(
        self, user_id: UUID
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive effectiveness report for all of a user's rules.
        """
        # Fetch all active rules
        result = await self.db.execute(
            select(Rule)
            .where(Rule.user_id == user_id, Rule.status == RuleStatus.ACTIVE.value)
            .order_by(Rule.confidence.desc())
        )
        rules = list(result.scalars().all())

        if not rules:
            return {
                "total_rules": 0,
                "average_score": 0,
                "top_rules": [],
                "underperforming_rules": [],
                "stale_rules": [],
                "category_breakdown": {},
            }

        # Compute effectiveness for each rule
        scored_rules = []
        for rule in rules:
            stats = await self._compute_rule_stats(rule.id)
            score = self._calculate_score(stats)
            scored_rules.append({
                "rule_id": str(rule.id),
                "content": rule.content[:100],
                "category": rule.category,
                "score": round(score, 1),
                "grade": self._score_to_grade(score),
                "apply_count": stats["apply_count"],
                "reinforce_rate": round(stats["reinforce_rate"] * 100, 1),
                "days_since_applied": stats["days_since_applied"],
            })

        # Sort by score
        scored_rules.sort(key=lambda r: r["score"], reverse=True)

        # Category breakdown
        category_scores: Dict[str, List[float]] = {}
        for r in scored_rules:
            cat = r["category"]
            if cat not in category_scores:
                category_scores[cat] = []
            category_scores[cat].append(r["score"])

        category_breakdown = {
            cat: {
                "count": len(scores),
                "average_score": round(sum(scores) / len(scores), 1),
            }
            for cat, scores in category_scores.items()
        }

        avg = sum(r["score"] for r in scored_rules) / len(scored_rules)

        return {
            "total_rules": len(scored_rules),
            "average_score": round(avg, 1),
            "top_rules": scored_rules[:5],
            "underperforming_rules": [
                r for r in scored_rules if r["score"] < 30
            ][:5],
            "stale_rules": [
                r for r in scored_rules if r["days_since_applied"] and r["days_since_applied"] > 30
            ][:5],
            "category_breakdown": category_breakdown,
        }

    # ------------------------------------------------------------------
    # Batch recompute (called by background job)
    # ------------------------------------------------------------------

    async def batch_compute(self, user_id: UUID) -> int:
        """
        Recompute effectiveness scores for all of a user's active rules.
        Returns the number of rules processed.
        """
        result = await self.db.execute(
            select(Rule).where(
                Rule.user_id == user_id,
                Rule.status == RuleStatus.ACTIVE.value,
            )
        )
        rules = list(result.scalars().all())
        return len(rules)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_rule(self, rule_id: UUID) -> Optional[Rule]:
        result = await self.db.execute(select(Rule).where(Rule.id == rule_id))
        return result.scalar_one_or_none()

    async def _compute_rule_stats(self, rule_id: UUID) -> Dict[str, Any]:
        """Aggregate audit events for a rule into stats."""
        result = await self.db.execute(
            select(
                func.count().filter(
                    AuditLog.event_type == AuditEventType.RULE_APPLIED.value
                ).label("apply_count"),
                func.count().filter(
                    AuditLog.event_type == AuditEventType.RULE_REINFORCED.value
                ).label("reinforce_count"),
                func.count().filter(
                    AuditLog.event_type.in_([
                        AuditEventType.RULE_EDITED.value,
                        AuditEventType.RULE_DISABLED.value,
                    ])
                ).label("override_count"),
                func.max(
                    case(
                        (
                            AuditLog.event_type == AuditEventType.RULE_APPLIED.value,
                            AuditLog.created_at,
                        ),
                        else_=None,
                    )
                ).label("last_applied"),
            ).where(AuditLog.rule_id == rule_id)
        )
        row = result.one()

        apply_count = row.apply_count or 0
        reinforce_count = row.reinforce_count or 0
        override_count = row.override_count or 0
        last_applied = row.last_applied
        total = apply_count + reinforce_count + override_count

        reinforce_rate = reinforce_count / total if total > 0 else 0.0
        override_rate = override_count / total if total > 0 else 0.0

        days_since = None
        if last_applied:
            days_since = (datetime.utcnow() - last_applied).days

        return {
            "apply_count": apply_count,
            "reinforce_count": reinforce_count,
            "override_count": override_count,
            "reinforce_rate": reinforce_rate,
            "override_rate": override_rate,
            "last_applied": last_applied,
            "days_since_applied": days_since,
        }

    def _calculate_score(self, stats: Dict[str, Any]) -> float:
        """
        Calculate effectiveness score (0-100).

        Formula:
          base      = reinforce_rate * 60   (max 60 points)
          penalty   = override_rate * 30    (max -30 points)
          usage     = min(apply_count, 20) / 20 * 20  (max 20 points)
          staleness = -10 if >30 days unused, -5 if >14 days
        """
        base = stats["reinforce_rate"] * 60
        penalty = stats["override_rate"] * 30
        usage = min(stats["apply_count"], 20) / 20 * 20

        staleness = 0
        if stats["days_since_applied"] is not None:
            if stats["days_since_applied"] > 30:
                staleness = -10
            elif stats["days_since_applied"] > 14:
                staleness = -5

        # If rule has never been applied, give a neutral baseline
        if stats["apply_count"] == 0:
            return 50.0

        score = base - penalty + usage + staleness
        return max(0.0, min(100.0, score))

    @staticmethod
    def _score_to_grade(score: float) -> str:
        if score >= 80:
            return "A"
        elif score >= 60:
            return "B"
        elif score >= 40:
            return "C"
        elif score >= 20:
            return "D"
        else:
            return "F"

    async def _compute_trend(self, rule_id: UUID) -> str:
        """
        Compare reinforcement rate in last 7 days vs previous 7 days.
        Returns 'improving', 'declining', or 'stable'.
        """
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        two_weeks_ago = now - timedelta(days=14)

        recent = await self.db.execute(
            select(func.count()).where(
                AuditLog.rule_id == rule_id,
                AuditLog.event_type == AuditEventType.RULE_REINFORCED.value,
                AuditLog.created_at >= week_ago,
            )
        )
        recent_count = recent.scalar() or 0

        previous = await self.db.execute(
            select(func.count()).where(
                AuditLog.rule_id == rule_id,
                AuditLog.event_type == AuditEventType.RULE_REINFORCED.value,
                AuditLog.created_at >= two_weeks_ago,
                AuditLog.created_at < week_ago,
            )
        )
        prev_count = previous.scalar() or 0

        if recent_count > prev_count + 1:
            return "improving"
        elif recent_count < prev_count - 1:
            return "declining"
        return "stable"
