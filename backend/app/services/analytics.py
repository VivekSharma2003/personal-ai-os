"""
Personal AI OS - Analytics Service

Aggregates usage statistics from the database.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy import select, func, case, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rule import Rule, RuleStatus
from app.models.interaction import Interaction
from app.models.audit_log import AuditLog
from app.models.user import User


class AnalyticsService:
    """Service for computing aggregated analytics."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_analytics(self, user_id: UUID) -> Dict[str, Any]:
        """
        Compute full analytics for a user.

        Args:
            user_id: Internal UUID of the user

        Returns:
            Dict with all analytics fields
        """
        # --- Totals ---
        # Total unique conversations
        conv_result = await self.db.execute(
            select(func.count(func.distinct(Interaction.conversation_id)))
            .where(Interaction.user_id == user_id)
            .where(Interaction.conversation_id.isnot(None))
        )
        total_conversations = conv_result.scalar() or 0

        # Total messages (interactions)
        msg_result = await self.db.execute(
            select(func.count(Interaction.id))
            .where(Interaction.user_id == user_id)
        )
        total_messages = msg_result.scalar() or 0

        # Total rules
        rules_result = await self.db.execute(
            select(func.count(Rule.id))
            .where(Rule.user_id == user_id)
        )
        total_rules = rules_result.scalar() or 0

        # Active rules
        active_result = await self.db.execute(
            select(func.count(Rule.id))
            .where(Rule.user_id == user_id)
            .where(Rule.status == RuleStatus.ACTIVE.value)
        )
        active_rules = active_result.scalar() or 0

        # Total corrections
        corrections_result = await self.db.execute(
            select(func.count(Interaction.id))
            .where(Interaction.user_id == user_id)
            .where(Interaction.was_corrected == True)
        )
        total_corrections = corrections_result.scalar() or 0

        # --- Rates ---
        correction_rate = (total_corrections / total_messages * 100) if total_messages > 0 else 0.0

        # Average rules applied per chat
        # Sum up the lengths of rules_applied arrays
        avg_rules_result = await self.db.execute(
            select(func.avg(func.coalesce(func.array_length(Interaction.rules_applied, 1), 0)))
            .where(Interaction.user_id == user_id)
        )
        avg_rules_per_chat = avg_rules_result.scalar() or 0.0

        # Average confidence of active rules
        avg_conf_result = await self.db.execute(
            select(func.avg(Rule.confidence))
            .where(Rule.user_id == user_id)
            .where(Rule.status == RuleStatus.ACTIVE.value)
        )
        avg_confidence = avg_conf_result.scalar() or 0.0

        # --- Daily Activity (last 30 days) ---
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        daily_messages = await self.db.execute(
            select(
                cast(Interaction.created_at, Date).label("day"),
                func.count(Interaction.id).label("msg_count"),
                func.sum(case((Interaction.was_corrected == True, 1), else_=0)).label("correction_count"),
            )
            .where(Interaction.user_id == user_id)
            .where(Interaction.created_at >= thirty_days_ago)
            .group_by(cast(Interaction.created_at, Date))
            .order_by(cast(Interaction.created_at, Date))
        )
        daily_msg_rows = daily_messages.all()

        daily_rules = await self.db.execute(
            select(
                cast(Rule.created_at, Date).label("day"),
                func.count(Rule.id).label("rule_count"),
            )
            .where(Rule.user_id == user_id)
            .where(Rule.created_at >= thirty_days_ago)
            .group_by(cast(Rule.created_at, Date))
        )
        daily_rule_rows = {str(row.day): row.rule_count for row in daily_rules.all()}

        daily_activity = []
        for row in daily_msg_rows:
            day_str = str(row.day)
            daily_activity.append({
                "date": day_str,
                "messages": row.msg_count,
                "corrections": row.correction_count or 0,
                "rules_created": daily_rule_rows.get(day_str, 0),
            })

        # --- Category Breakdown ---
        cat_result = await self.db.execute(
            select(
                Rule.category,
                func.count(Rule.id).label("count"),
            )
            .where(Rule.user_id == user_id)
            .group_by(Rule.category)
            .order_by(func.count(Rule.id).desc())
        )
        cat_rows = cat_result.all()
        category_breakdown = []
        for row in cat_rows:
            pct = (row.count / total_rules * 100) if total_rules > 0 else 0.0
            category_breakdown.append({
                "category": row.category,
                "count": row.count,
                "percentage": round(pct, 1),
            })

        # --- Most Applied Rule ---
        top_rule_result = await self.db.execute(
            select(Rule.content, Rule.times_applied)
            .where(Rule.user_id == user_id)
            .where(Rule.status == RuleStatus.ACTIVE.value)
            .order_by(Rule.times_applied.desc())
            .limit(1)
        )
        top_rule = top_rule_result.first()
        most_applied_rule = top_rule.content if top_rule else None
        most_applied_count = top_rule.times_applied if top_rule else 0

        return {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "total_rules": total_rules,
            "active_rules": active_rules,
            "total_corrections": total_corrections,
            "correction_rate": round(correction_rate, 1),
            "avg_rules_per_chat": round(float(avg_rules_per_chat), 2),
            "avg_confidence": round(float(avg_confidence), 2),
            "daily_activity": daily_activity,
            "category_breakdown": category_breakdown,
            "most_applied_rule": most_applied_rule,
            "most_applied_count": most_applied_count,
        }
