"""
Personal AI OS - Shared Library Service

Publish, browse, install, and rate rules from a shared community library.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rule import Rule
from app.models.shared_rule import SharedRule
from app.core.logging import get_logger

logger = get_logger("services.shared_library")


class SharedLibraryService:
    """Service for the multi-user shared rule library."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def publish_rule(
        self,
        user_id: UUID,
        rule_id: UUID,
        title: str,
        description: str = None,
        visibility: str = "public",
    ) -> Dict[str, Any]:
        """
        Publish a user's rule to the shared library.

        Creates an immutable snapshot of the rule content.
        """
        # Fetch the source rule
        result = await self.db.execute(
            select(Rule).where(and_(Rule.id == rule_id, Rule.user_id == user_id))
        )
        rule = result.scalar_one_or_none()
        if not rule:
            return {"error": "Rule not found or not owned by user"}

        # Check if already published
        existing = await self.db.execute(
            select(SharedRule).where(
                and_(
                    SharedRule.author_user_id == user_id,
                    SharedRule.source_rule_id == rule_id,
                )
            )
        )
        if existing.scalar_one_or_none():
            return {"error": "Rule is already published"}

        shared = SharedRule(
            id=uuid4(),
            author_user_id=user_id,
            source_rule_id=rule_id,
            title=title,
            description=description,
            content=rule.content,
            category=rule.category,
            visibility=visibility,
        )
        self.db.add(shared)

        logger.info(
            "Rule published to shared library",
            extra={"extra_data": {
                "user_id": str(user_id),
                "rule_id": str(rule_id),
                "shared_rule_id": str(shared.id),
            }},
        )

        return {"shared_rule": shared.to_dict()}

    async def browse_library(
        self,
        query: str = None,
        category: str = None,
        sort_by: str = "popular",
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Browse and search the shared rule library."""
        stmt = select(SharedRule).where(SharedRule.visibility == "public")

        if query:
            stmt = stmt.where(
                or_(
                    SharedRule.title.ilike(f"%{query}%"),
                    SharedRule.content.ilike(f"%{query}%"),
                    SharedRule.description.ilike(f"%{query}%"),
                )
            )

        if category:
            stmt = stmt.where(SharedRule.category == category)

        # Sorting
        if sort_by == "popular":
            stmt = stmt.order_by(desc(SharedRule.install_count))
        elif sort_by == "rating":
            stmt = stmt.order_by(desc(SharedRule.rating_sum / func.nullif(SharedRule.rating_count, 0)))
        elif sort_by == "newest":
            stmt = stmt.order_by(desc(SharedRule.created_at))
        else:
            stmt = stmt.order_by(desc(SharedRule.install_count))

        # Count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Paginate
        stmt = stmt.limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        items = [r.to_dict() for r in result.scalars().all()]

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "sort_by": sort_by,
            "rules": items,
        }

    async def get_popular(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top shared rules by install count."""
        result = await self.db.execute(
            select(SharedRule)
            .where(SharedRule.visibility == "public")
            .order_by(desc(SharedRule.install_count))
            .limit(limit)
        )
        return [r.to_dict() for r in result.scalars().all()]

    async def install_rule(
        self, user_id: UUID, shared_rule_id: UUID
    ) -> Dict[str, Any]:
        """
        Install a shared rule into the user's personal ruleset.

        Creates a copy with attribution to the original.
        """
        result = await self.db.execute(
            select(SharedRule).where(SharedRule.id == shared_rule_id)
        )
        shared = result.scalar_one_or_none()
        if not shared:
            return {"error": "Shared rule not found"}

        # Create user's copy
        new_rule = Rule(
            id=uuid4(),
            user_id=user_id,
            content=shared.content,
            original_correction=f"Installed from shared library: {shared.title}",
            category=shared.category,
            confidence=0.5,
            status="active",
        )
        self.db.add(new_rule)

        # Increment install count
        shared.install_count = (shared.install_count or 0) + 1

        logger.info(
            "Shared rule installed",
            extra={"extra_data": {
                "user_id": str(user_id),
                "shared_rule_id": str(shared_rule_id),
                "new_rule_id": str(new_rule.id),
            }},
        )

        return {
            "installed_rule_id": str(new_rule.id),
            "source_shared_rule": shared.to_dict(),
        }

    async def rate_rule(
        self, user_id: UUID, shared_rule_id: UUID, rating: int
    ) -> Dict[str, Any]:
        """Rate a shared rule (1-5 stars)."""
        if rating < 1 or rating > 5:
            return {"error": "Rating must be between 1 and 5"}

        result = await self.db.execute(
            select(SharedRule).where(SharedRule.id == shared_rule_id)
        )
        shared = result.scalar_one_or_none()
        if not shared:
            return {"error": "Shared rule not found"}

        shared.rating_sum = (shared.rating_sum or 0) + rating
        shared.rating_count = (shared.rating_count or 0) + 1

        logger.info(
            "Shared rule rated",
            extra={"extra_data": {
                "user_id": str(user_id),
                "shared_rule_id": str(shared_rule_id),
                "rating": rating,
                "new_avg": shared.avg_rating,
            }},
        )

        return {
            "shared_rule_id": str(shared_rule_id),
            "new_avg_rating": shared.avg_rating,
            "total_ratings": shared.rating_count,
        }

    async def unpublish(self, user_id: UUID, shared_rule_id: UUID) -> Dict[str, Any]:
        """Remove a shared rule (author only)."""
        result = await self.db.execute(
            select(SharedRule).where(
                and_(
                    SharedRule.id == shared_rule_id,
                    SharedRule.author_user_id == user_id,
                )
            )
        )
        shared = result.scalar_one_or_none()
        if not shared:
            return {"error": "Shared rule not found or not authored by user"}

        await self.db.delete(shared)

        logger.info(
            "Shared rule unpublished",
            extra={"extra_data": {
                "user_id": str(user_id),
                "shared_rule_id": str(shared_rule_id),
            }},
        )

        return {"deleted": True, "shared_rule_id": str(shared_rule_id)}
