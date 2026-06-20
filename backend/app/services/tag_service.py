"""
Personal AI OS - Tag Service

Manages tag CRUD, rule-tag associations, and bulk tagging operations.
"""
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.rule import Rule
from app.models.rule_tag import Tag, rule_tags


class TagService:
    """Service for managing tags and their rule associations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # --- Tag CRUD ---

    async def create_tag(
        self,
        user_id: UUID,
        name: str,
        color: str = "#6366f1",
    ) -> Tag:
        """Create a new tag for a user."""
        tag = Tag(user_id=user_id, name=name, color=color)
        self.db.add(tag)
        await self.db.flush()
        return tag

    async def get_tag(self, tag_id: UUID) -> Optional[Tag]:
        """Get a tag by ID."""
        result = await self.db.execute(
            select(Tag).where(Tag.id == tag_id)
        )
        return result.scalar_one_or_none()

    async def list_tags(self, user_id: UUID) -> List[Tag]:
        """List all tags for a user, with rule counts."""
        result = await self.db.execute(
            select(Tag)
            .where(Tag.user_id == user_id)
            .options(selectinload(Tag.rules))
            .order_by(Tag.name)
        )
        return list(result.scalars().all())

    async def update_tag(
        self,
        tag_id: UUID,
        name: Optional[str] = None,
        color: Optional[str] = None,
    ) -> Optional[Tag]:
        """Update a tag's name or color."""
        tag = await self.get_tag(tag_id)
        if not tag:
            return None
        if name:
            tag.name = name
        if color:
            tag.color = color
        return tag

    async def delete_tag(self, tag_id: UUID) -> bool:
        """Delete a tag (cascade removes associations)."""
        tag = await self.get_tag(tag_id)
        if not tag:
            return False
        await self.db.delete(tag)
        return True

    # --- Rule-Tag Associations ---

    async def tag_rule(self, rule_id: UUID, tag_ids: List[UUID]) -> List[str]:
        """
        Attach one or more tags to a rule.

        Returns list of tag names attached.
        """
        # Get the rule with its tags loaded
        result = await self.db.execute(
            select(Rule)
            .where(Rule.id == rule_id)
            .options(selectinload(Rule.tags))
        )
        rule = result.scalar_one_or_none()
        if not rule:
            return []

        existing_tag_ids = {t.id for t in rule.tags}
        attached = []

        for tag_id in tag_ids:
            if tag_id in existing_tag_ids:
                continue
            tag = await self.get_tag(tag_id)
            if tag:
                rule.tags.append(tag)
                attached.append(tag.name)

        return attached

    async def untag_rule(self, rule_id: UUID, tag_ids: List[UUID]) -> List[str]:
        """
        Remove one or more tags from a rule.

        Returns list of tag names removed.
        """
        result = await self.db.execute(
            select(Rule)
            .where(Rule.id == rule_id)
            .options(selectinload(Rule.tags))
        )
        rule = result.scalar_one_or_none()
        if not rule:
            return []

        removed = []
        tag_ids_set = set(tag_ids)
        remaining_tags = []

        for tag in rule.tags:
            if tag.id in tag_ids_set:
                removed.append(tag.name)
            else:
                remaining_tags.append(tag)

        rule.tags = remaining_tags
        return removed

    async def get_rules_by_tag(self, tag_id: UUID) -> List[Rule]:
        """Get all rules that have a specific tag."""
        result = await self.db.execute(
            select(Tag)
            .where(Tag.id == tag_id)
            .options(selectinload(Tag.rules))
        )
        tag = result.scalar_one_or_none()
        if not tag:
            return []
        return list(tag.rules)

    async def bulk_tag(
        self,
        rule_ids: List[UUID],
        tag_ids: List[UUID],
    ) -> dict:
        """
        Bulk-attach tags to multiple rules at once.

        Returns a summary of how many rules were tagged.
        """
        tagged_count = 0

        for rule_id in rule_ids:
            attached = await self.tag_rule(rule_id, tag_ids)
            if attached:
                tagged_count += 1

        return {
            "rules_tagged": tagged_count,
            "total_rules": len(rule_ids),
            "total_tags": len(tag_ids),
        }
