"""
Personal AI OS - Conflict Service

Orchestrates conflict detection, storage, and resolution.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rule import Rule, RuleStatus
from app.models.rule_conflict import RuleConflict, ConflictStatus, ConflictResolution
from app.core.conflict_detector import detect_pairwise_conflict, scan_all_conflicts
from app.core.events import emit_event


class ConflictService:
    """Service for detecting, managing, and resolving rule conflicts."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def detect_conflicts_for_rule(
        self,
        rule: Rule,
        user_id: UUID
    ) -> List[RuleConflict]:
        """
        Check a single rule against all other active rules for conflicts.

        Called when a rule is created or updated.

        Args:
            rule: The rule to check
            user_id: UUID of the user

        Returns:
            List of newly created RuleConflict objects
        """
        # Get all active rules for this user
        result = await self.db.execute(
            select(Rule)
            .where(Rule.user_id == user_id)
            .where(Rule.status == RuleStatus.ACTIVE.value)
            .where(Rule.id != rule.id)
        )
        other_rules = list(result.scalars().all())

        if not other_rules:
            return []

        new_conflicts = []
        for other_rule in other_rules:
            # Check if conflict already exists
            existing = await self._get_existing_conflict(rule.id, other_rule.id)
            if existing:
                continue

            # Detect conflict via LLM
            analysis = await detect_pairwise_conflict(rule.content, other_rule.content)

            if analysis["conflicts"]:
                conflict = RuleConflict(
                    user_id=user_id,
                    rule_a_id=rule.id,
                    rule_b_id=other_rule.id,
                    explanation=analysis["explanation"],
                    severity=analysis["severity"],
                    suggested_resolution=analysis["suggested_resolution"],
                    status=ConflictStatus.ACTIVE.value,
                )
                self.db.add(conflict)
                await self.db.flush()
                new_conflicts.append(conflict)

                # Emit event
                await emit_event("rule.conflict_detected", {
                    "conflict_id": str(conflict.id),
                    "rule_a_id": str(rule.id),
                    "rule_b_id": str(other_rule.id),
                    "severity": analysis["severity"],
                })

        return new_conflicts

    async def scan_all_user_conflicts(self, user_id: UUID) -> List[RuleConflict]:
        """
        Full scan of all active rules for conflicts.

        Used by the background job and manual trigger.

        Args:
            user_id: UUID of the user

        Returns:
            List of newly created RuleConflict objects
        """
        # Get all active rules
        result = await self.db.execute(
            select(Rule)
            .where(Rule.user_id == user_id)
            .where(Rule.status == RuleStatus.ACTIVE.value)
        )
        rules = list(result.scalars().all())
        rules_data = [r.to_dict() for r in rules]

        # Scan for conflicts
        detected = await scan_all_conflicts(rules_data)

        new_conflicts = []
        for conflict_data in detected:
            rule_a_id = UUID(conflict_data["rule_a_id"])
            rule_b_id = UUID(conflict_data["rule_b_id"])

            # Check if already exists
            existing = await self._get_existing_conflict(rule_a_id, rule_b_id)
            if existing:
                continue

            conflict = RuleConflict(
                user_id=user_id,
                rule_a_id=rule_a_id,
                rule_b_id=rule_b_id,
                explanation=conflict_data["explanation"],
                severity=conflict_data["severity"],
                suggested_resolution=conflict_data["suggested_resolution"],
                status=ConflictStatus.ACTIVE.value,
            )
            self.db.add(conflict)
            await self.db.flush()
            new_conflicts.append(conflict)

        return new_conflicts

    async def get_conflicts(
        self,
        user_id: UUID,
        status: Optional[str] = None
    ) -> List[RuleConflict]:
        """
        Get all conflicts for a user.

        Args:
            user_id: UUID of the user
            status: Optional filter by status

        Returns:
            List of RuleConflict objects
        """
        query = (
            select(RuleConflict)
            .where(RuleConflict.user_id == user_id)
        )

        if status:
            query = query.where(RuleConflict.status == status)

        query = query.order_by(RuleConflict.severity.desc(), RuleConflict.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def resolve_conflict(
        self,
        conflict_id: UUID,
        resolution: str,
        details: Optional[dict] = None
    ) -> Optional[RuleConflict]:
        """
        Resolve a conflict by applying the chosen resolution strategy.

        Args:
            conflict_id: UUID of the conflict
            resolution: Resolution strategy (keep_both, keep_newer, keep_older, merge, disable_one)
            details: Additional resolution details (e.g., merged rule text, which rule to disable)

        Returns:
            Updated RuleConflict object
        """
        result = await self.db.execute(
            select(RuleConflict).where(RuleConflict.id == conflict_id)
        )
        conflict = result.scalar_one_or_none()

        if not conflict:
            return None

        details = details or {}

        # Apply resolution
        if resolution == ConflictResolution.KEEP_BOTH.value:
            # Just mark as resolved, no action needed
            pass

        elif resolution == ConflictResolution.KEEP_NEWER.value:
            # Disable the older rule
            rule_a = await self.db.get(Rule, conflict.rule_a_id)
            rule_b = await self.db.get(Rule, conflict.rule_b_id)
            if rule_a and rule_b:
                older = rule_a if rule_a.created_at <= rule_b.created_at else rule_b
                older.status = RuleStatus.DISABLED.value

        elif resolution == ConflictResolution.KEEP_OLDER.value:
            # Disable the newer rule
            rule_a = await self.db.get(Rule, conflict.rule_a_id)
            rule_b = await self.db.get(Rule, conflict.rule_b_id)
            if rule_a and rule_b:
                newer = rule_b if rule_b.created_at >= rule_a.created_at else rule_a
                newer.status = RuleStatus.DISABLED.value

        elif resolution == ConflictResolution.MERGE.value:
            # Merge into rule_a, disable rule_b
            merged_content = details.get("merged_content")
            if merged_content:
                rule_a = await self.db.get(Rule, conflict.rule_a_id)
                rule_b = await self.db.get(Rule, conflict.rule_b_id)
                if rule_a and rule_b:
                    rule_a.content = merged_content
                    rule_a.updated_at = datetime.utcnow()
                    rule_b.status = RuleStatus.DISABLED.value

        elif resolution == ConflictResolution.DISABLE_ONE.value:
            # Disable the specified rule
            rule_to_disable = details.get("disable_rule_id")
            if rule_to_disable:
                rule = await self.db.get(Rule, UUID(rule_to_disable))
                if rule:
                    rule.status = RuleStatus.DISABLED.value

        # Update conflict status
        conflict.status = ConflictStatus.RESOLVED.value
        conflict.resolved_at = datetime.utcnow()
        conflict.resolution_applied = resolution
        conflict.resolution_details = details

        return conflict

    async def dismiss_conflict(self, conflict_id: UUID) -> Optional[RuleConflict]:
        """Dismiss a conflict (user acknowledges but takes no action)."""
        result = await self.db.execute(
            select(RuleConflict).where(RuleConflict.id == conflict_id)
        )
        conflict = result.scalar_one_or_none()

        if conflict:
            conflict.status = ConflictStatus.DISMISSED.value
            conflict.resolved_at = datetime.utcnow()

        return conflict

    async def _get_existing_conflict(
        self,
        rule_a_id: UUID,
        rule_b_id: UUID
    ) -> Optional[RuleConflict]:
        """Check if a conflict already exists between two rules (in either direction)."""
        result = await self.db.execute(
            select(RuleConflict)
            .where(
                or_(
                    and_(
                        RuleConflict.rule_a_id == rule_a_id,
                        RuleConflict.rule_b_id == rule_b_id
                    ),
                    and_(
                        RuleConflict.rule_a_id == rule_b_id,
                        RuleConflict.rule_b_id == rule_a_id
                    )
                )
            )
            .where(RuleConflict.status == ConflictStatus.ACTIVE.value)
        )
        return result.scalar_one_or_none()
