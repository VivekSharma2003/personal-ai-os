"""
Personal AI OS - Versioning Service

Tracks every change to a rule as an immutable version snapshot.
Supports history viewing, rollback, and textual diffing.
"""
import difflib
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rule import Rule
from app.models.rule_version import RuleVersion


class VersioningService:
    """Service for managing rule version history."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_version(
        self,
        rule: Rule,
        change_reason: str = "",
        changed_by: str = "user"
    ) -> RuleVersion:
        """
        Snapshot the current state of a rule before mutation.

        Should be called BEFORE any update to capture the pre-change state.

        Args:
            rule: The Rule object to snapshot
            change_reason: Human-readable reason for the change
            changed_by: Who made the change ("user", "system", "decay", "import")

        Returns:
            The created RuleVersion object
        """
        # Get the next version number
        next_version = await self._get_next_version_number(rule.id)

        version = RuleVersion(
            rule_id=rule.id,
            version_number=next_version,
            content=rule.content,
            category=rule.category,
            confidence=rule.confidence,
            status=rule.status,
            changed_by=changed_by,
            change_reason=change_reason,
        )

        self.db.add(version)
        await self.db.flush()

        return version

    async def get_history(
        self,
        rule_id: UUID,
        limit: int = 50
    ) -> List[RuleVersion]:
        """
        Get the full version history of a rule.

        Args:
            rule_id: UUID of the rule
            limit: Max number of versions to return

        Returns:
            List of RuleVersion objects, newest first
        """
        result = await self.db.execute(
            select(RuleVersion)
            .where(RuleVersion.rule_id == rule_id)
            .order_by(RuleVersion.version_number.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_version(
        self,
        rule_id: UUID,
        version_number: int
    ) -> Optional[RuleVersion]:
        """Get a specific version of a rule."""
        result = await self.db.execute(
            select(RuleVersion)
            .where(RuleVersion.rule_id == rule_id)
            .where(RuleVersion.version_number == version_number)
        )
        return result.scalar_one_or_none()

    async def rollback(
        self,
        rule_id: UUID,
        target_version: int
    ) -> Optional[Rule]:
        """
        Rollback a rule to a previous version.

        Creates a new version snapshot of the current state before rolling back.

        Args:
            rule_id: UUID of the rule
            target_version: Version number to restore

        Returns:
            The updated Rule object, or None if rule/version not found
        """
        # Get the rule
        rule = await self.db.get(Rule, rule_id)
        if not rule:
            return None

        # Get the target version
        version = await self.get_version(rule_id, target_version)
        if not version:
            return None

        # Snapshot current state before rollback
        await self.create_version(
            rule,
            change_reason=f"Pre-rollback snapshot (rolling back to v{target_version})",
            changed_by="system"
        )

        # Apply the historical state
        rule.content = version.content
        rule.category = version.category
        rule.confidence = version.confidence
        rule.status = version.status
        rule.updated_at = datetime.utcnow()

        # Create a new version for the rollback itself
        await self.create_version(
            rule,
            change_reason=f"Rolled back to v{target_version}",
            changed_by="user"
        )

        return rule

    async def diff(
        self,
        rule_id: UUID,
        version_a: int,
        version_b: int
    ) -> Dict[str, Any]:
        """
        Compute a diff between two versions of a rule.

        Args:
            rule_id: UUID of the rule
            version_a: First version number
            version_b: Second version number

        Returns:
            Dict with unified diff and changed fields
        """
        va = await self.get_version(rule_id, version_a)
        vb = await self.get_version(rule_id, version_b)

        if not va or not vb:
            return {"error": "One or both versions not found"}

        # Content diff (line-by-line)
        content_diff = list(difflib.unified_diff(
            va.content.splitlines(keepends=True),
            vb.content.splitlines(keepends=True),
            fromfile=f"v{version_a}",
            tofile=f"v{version_b}",
            lineterm=""
        ))

        # Field-level changes
        changes = []
        if va.content != vb.content:
            changes.append({
                "field": "content",
                "from": va.content,
                "to": vb.content,
            })
        if va.category != vb.category:
            changes.append({
                "field": "category",
                "from": va.category,
                "to": vb.category,
            })
        if va.confidence != vb.confidence:
            changes.append({
                "field": "confidence",
                "from": round(va.confidence, 2),
                "to": round(vb.confidence, 2),
            })
        if va.status != vb.status:
            changes.append({
                "field": "status",
                "from": va.status,
                "to": vb.status,
            })

        return {
            "rule_id": str(rule_id),
            "version_a": va.to_dict(),
            "version_b": vb.to_dict(),
            "content_diff": content_diff,
            "changes": changes,
            "has_changes": len(changes) > 0,
        }

    async def _get_next_version_number(self, rule_id: UUID) -> int:
        """Get the next version number for a rule."""
        result = await self.db.execute(
            select(func.max(RuleVersion.version_number))
            .where(RuleVersion.rule_id == rule_id)
        )
        max_version = result.scalar()
        return (max_version or 0) + 1
