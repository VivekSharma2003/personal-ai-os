"""
Personal AI OS - Rule Changelog Service

Records a diff entry every time a rule's content changes and provides
a versioned history with inline unified-diff output.
"""
import difflib
import logging
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.rule_changelog import RuleChangelog

logger = logging.getLogger(__name__)


def _unified_diff(old: Optional[str], new: str) -> str:
    """Return a compact unified-diff string between two text values."""
    a_lines = (old or "").splitlines(keepends=True)
    b_lines = new.splitlines(keepends=True)
    diff = list(difflib.unified_diff(a_lines, b_lines, fromfile="before", tofile="after", lineterm=""))
    return "".join(diff) if diff else "(no change)"


class ChangelogService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record(
        self,
        rule_id: UUID,
        new_content: str,
        old_content: Optional[str] = None,
        changed_by: Optional[str] = None,
        change_reason: Optional[str] = None,
    ) -> RuleChangelog:
        """Append a new changelog entry for a rule edit."""
        # Get next version number for this rule
        result = await self.db.execute(
            select(func.coalesce(func.max(RuleChangelog.version), 0))
            .where(RuleChangelog.rule_id == rule_id)
        )
        next_version = result.scalar() + 1

        entry = RuleChangelog(
            rule_id=rule_id,
            version=next_version,
            old_content=old_content,
            new_content=new_content,
            changed_by=changed_by,
            change_reason=change_reason,
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def get_history(self, rule_id: UUID) -> List[RuleChangelog]:
        """Return all changelog entries for a rule, oldest first."""
        result = await self.db.execute(
            select(RuleChangelog)
            .where(RuleChangelog.rule_id == rule_id)
            .order_by(RuleChangelog.version)
        )
        return result.scalars().all()

    async def get_version(self, rule_id: UUID, version: int) -> Optional[RuleChangelog]:
        """Fetch one specific version of a rule."""
        result = await self.db.execute(
            select(RuleChangelog)
            .where(RuleChangelog.rule_id == rule_id, RuleChangelog.version == version)
        )
        return result.scalars().first()

    async def diff(self, rule_id: UUID, from_version: int, to_version: int) -> dict:
        """Return a unified diff between two versions of a rule."""
        v_from = await self.get_version(rule_id, from_version)
        v_to = await self.get_version(rule_id, to_version)

        if not v_from:
            raise ValueError(f"Version {from_version} not found for rule {rule_id}")
        if not v_to:
            raise ValueError(f"Version {to_version} not found for rule {rule_id}")

        patch = _unified_diff(v_from.new_content, v_to.new_content)
        return {
            "rule_id": str(rule_id),
            "from_version": from_version,
            "to_version": to_version,
            "patch": patch,
        }
