"""
Personal AI OS - Decay Policy Service

Manages dynamic, context-aware confidence decay policies and processes rule decay.
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from sqlalchemy import select, and_, delete, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.decay_policy import DecayPolicy
from app.models.rule import Rule, RuleStatus
from app.models.interaction import Interaction
from app.models.audit_log import AuditLog
from app.db.redis import RuleCache
from app.core.logging import get_logger
from app.config import get_settings

logger = get_logger("services.decay_policy")


class DecayPolicyService:
    """Service for managing decay policies and processing dynamic rule decay."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_or_update_policy(
        self,
        user_id: UUID,
        tag_id: Optional[UUID] = None,
        category: Optional[str] = None,
        base_decay_rate: float = 0.05,
        grace_period_days: int = 7,
        topic_sensitivity: float = 1.0,
    ) -> DecayPolicy:
        """Create or update a decay policy override for a specific tag or category."""
        # Check if policy already exists
        stmt = select(DecayPolicy).where(
            and_(
                DecayPolicy.user_id == user_id,
                DecayPolicy.tag_id == tag_id,
                DecayPolicy.category == category,
            )
        )
        result = await self.db.execute(stmt)
        policy = result.scalar_one_or_none()

        if policy:
            policy.base_decay_rate = base_decay_rate
            policy.grace_period_days = grace_period_days
            policy.topic_sensitivity = topic_sensitivity
        else:
            policy = DecayPolicy(
                id=uuid4(),
                user_id=user_id,
                tag_id=tag_id,
                category=category,
                base_decay_rate=base_decay_rate,
                grace_period_days=grace_period_days,
                topic_sensitivity=topic_sensitivity,
            )
            self.db.add(policy)

        await self.db.flush()
        logger.info(f"Decay policy created/updated: {policy.id}")
        return policy

    async def list_policies(self, user_id: UUID) -> List[DecayPolicy]:
        """List all decay policies for a user."""
        stmt = select(DecayPolicy).where(DecayPolicy.user_id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_policy(self, policy_id: UUID, user_id: UUID) -> Dict[str, Any]:
        """Delete a decay policy."""
        stmt = delete(DecayPolicy).where(
            and_(DecayPolicy.id == policy_id, DecayPolicy.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return {"deleted": True, "count": result.rowcount}

    async def process_dynamic_decay(self, user_id: UUID, dry_run: bool = False) -> Dict[str, Any]:
        """
        Process context-aware decay for all active rules of a user.
        
        1. Fetch all active rules.
        2. Identify recently active categories/tags based on interactions.
        3. Match each rule with its decay policy.
        4. Apply decay.
        """
        # Fetch active rules for the user
        result = await self.db.execute(
            select(Rule).where(
                and_(Rule.user_id == user_id, Rule.status == RuleStatus.ACTIVE.value)
            )
        )
        rules = result.scalars().all()

        if not rules:
            return {"processed": 0, "archived": 0, "changes": []}

        # Fetch decay policies
        policies = await self.list_policies(user_id)
        # Create map for fast lookup
        policy_by_tag: Dict[UUID, DecayPolicy] = {}
        policy_by_cat: Dict[str, DecayPolicy] = {}
        general_policy = None

        for p in policies:
            if p.tag_id:
                policy_by_tag[p.tag_id] = p
            elif p.category:
                policy_by_cat[p.category] = p
            else:
                general_policy = p

        # Fetch recent interactions in the last 14 days to compute category activity
        cutoff_date = datetime.utcnow() - timedelta(days=14)
        interactions_stmt = select(Interaction).where(
            and_(Interaction.user_id == user_id, Interaction.created_at >= cutoff_date)
        )
        int_result = await self.db.execute(interactions_stmt)
        recent_interactions = int_result.scalars().all()

        # Identify which rule IDs and categories/tags were active
        recently_applied_rules = set()
        active_categories = set()
        for inter in recent_interactions:
            if inter.rules_applied:
                for rid in inter.rules_applied:
                    recently_applied_rules.add(rid)

        # Also populate active categories from applied rules
        for rule in rules:
            if rule.id in recently_applied_rules:
                active_categories.add(rule.category)

        changes = []
        archived_count = 0
        decayed_count = 0

        for rule in rules:
            # 1. Match policy
            matched_policy = None
            # Check tags (using rule's tags)
            rule_tag_ids = [t.id for t in rule.tags] if hasattr(rule, "tags") else []
            for tid in rule_tag_ids:
                if tid in policy_by_tag:
                    matched_policy = policy_by_tag[tid]
                    break

            if not matched_policy and rule.category in policy_by_cat:
                matched_policy = policy_by_cat[rule.category]

            if not matched_policy:
                matched_policy = general_policy

            # Configuration defaults if no policy matched
            base_rate = matched_policy.base_decay_rate if matched_policy else 0.05
            grace_days = matched_policy.grace_period_days if matched_policy else 7
            sensitivity = matched_policy.topic_sensitivity if matched_policy else 1.0

            # Calculate days since last use
            days_since_use = 0
            if rule.last_applied_at:
                days_since_use = (datetime.utcnow() - rule.last_applied_at).days

            # Skip decay if within grace period
            if days_since_use <= grace_days:
                continue

            # Context-Aware Modifier:
            # If the category was completely INACTIVE in recent interactions,
            # we scale down decay rate because the user didn't have a chance to use it.
            decay_modifier = 1.0
            if rule.category not in active_categories:
                # Suspend/reduce decay since category was inactive
                decay_modifier = max(0.0, 1.0 - sensitivity)

            # Apply decay penalty
            weeks_unused = max(0, (days_since_use - grace_days) // 7)
            if weeks_unused == 0:
                continue

            decay_penalty = weeks_unused * base_rate * decay_modifier
            new_confidence = max(0.1, min(0.95, rule.confidence - decay_penalty))

            if new_confidence < rule.confidence:
                old_conf = rule.confidence
                change_info = {
                    "rule_id": str(rule.id),
                    "content": rule.content,
                    "old_confidence": round(old_conf, 3),
                    "new_confidence": round(new_confidence, 3),
                    "archived": False,
                }

                if not dry_run:
                    rule.confidence = new_confidence
                    rule.updated_at = datetime.utcnow()

                    # Check archival
                    settings = get_settings()
                    if new_confidence < settings.archive_threshold:
                        rule.status = RuleStatus.ARCHIVED.value
                        change_info["archived"] = True
                        archived_count += 1
                        # Log audit
                        await self._log_event(user_id, rule.id, "archived", {"reason": "dynamic_decay"})
                    else:
                        decayed_count += 1
                        await self._log_event(
                            user_id,
                            rule.id,
                            "decayed",
                            {
                                "old_confidence": round(old_conf, 3),
                                "new_confidence": round(new_confidence, 3),
                            },
                        )

                changes.append(change_info)

        if not dry_run and changes:
            await self.db.flush()
            await RuleCache.invalidate_user_rules(str(user_id))

        return {
            "processed": len(changes),
            "decayed": decayed_count,
            "archived": archived_count,
            "changes": changes,
        }

    async def _log_event(self, user_id: UUID, rule_id: UUID, event_type: str, data: dict):
        log = AuditLog(
            user_id=user_id,
            rule_id=rule_id,
            event_type=event_type,
            event_data=data,
        )
        self.db.add(log)
