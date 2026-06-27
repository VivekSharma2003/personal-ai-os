"""
Personal AI OS - Profile Service

Manages prompt profiles for context-aware rule filtering and LLM parameter overrides.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prompt_profile import PromptProfile
from app.core.logging import get_logger

logger = get_logger("services.profile")


class ProfileService:
    """Service for managing prompt profiles."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_profile(
        self,
        user_id: UUID,
        name: str,
        description: str = "",
        rule_filter_tags: Optional[List[str]] = None,
        rule_filter_categories: Optional[List[str]] = None,
        system_preamble: str = "",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        is_default: bool = False,
    ) -> PromptProfile:
        """Create a new prompt profile."""
        # If this is set as default, unset any existing default
        if is_default:
            await self._clear_default(user_id)

        profile = PromptProfile(
            user_id=user_id,
            name=name,
            description=description,
            rule_filter_tags=rule_filter_tags or [],
            rule_filter_categories=rule_filter_categories or [],
            system_preamble=system_preamble,
            temperature=temperature,
            max_tokens=max_tokens,
            is_default=is_default,
        )
        self.db.add(profile)
        await self.db.flush()

        logger.info(f"Created profile '{name}'", extra={"extra_data": {
            "profile_id": str(profile.id),
            "user_id": str(user_id),
        }})

        return profile

    async def update_profile(
        self,
        profile_id: UUID,
        **kwargs,
    ) -> PromptProfile:
        """Update profile fields."""
        profile = await self.db.get(PromptProfile, profile_id)
        if not profile:
            raise ValueError("Profile not found")

        if kwargs.get("is_default"):
            await self._clear_default(profile.user_id)

        for key, value in kwargs.items():
            if hasattr(profile, key) and value is not None:
                setattr(profile, key, value)

        profile.updated_at = datetime.utcnow()
        await self.db.flush()
        return profile

    async def delete_profile(self, profile_id: UUID) -> bool:
        """Delete a profile."""
        profile = await self.db.get(PromptProfile, profile_id)
        if not profile:
            return False
        await self.db.delete(profile)
        await self.db.flush()
        return True

    async def get_profile(self, profile_id: UUID) -> Optional[PromptProfile]:
        """Get a single profile."""
        return await self.db.get(PromptProfile, profile_id)

    async def list_profiles(self, user_id: UUID) -> List[Dict[str, Any]]:
        """List all profiles for a user."""
        q = select(PromptProfile).where(
            PromptProfile.user_id == user_id
        ).order_by(PromptProfile.is_default.desc(), PromptProfile.name)
        result = await self.db.execute(q)
        return [p.to_dict() for p in result.scalars().all()]

    async def clone_profile(
        self,
        profile_id: UUID,
        new_name: str,
    ) -> PromptProfile:
        """Clone a profile with a new name."""
        source = await self.db.get(PromptProfile, profile_id)
        if not source:
            raise ValueError("Source profile not found")

        clone = PromptProfile(
            user_id=source.user_id,
            name=new_name,
            description=f"Cloned from '{source.name}'",
            rule_filter_tags=list(source.rule_filter_tags or []),
            rule_filter_categories=list(source.rule_filter_categories or []),
            system_preamble=source.system_preamble,
            temperature=source.temperature,
            max_tokens=source.max_tokens,
            is_default=False,
        )
        self.db.add(clone)
        await self.db.flush()
        return clone

    async def apply_profile(
        self,
        profile_id: UUID,
        rules: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Apply a profile to a list of rules.

        Filters rules by tag/category and returns overrides.

        Returns:
            Dict with filtered_rules, system_preamble, temperature, max_tokens.
        """
        profile = await self.db.get(PromptProfile, profile_id)
        if not profile:
            raise ValueError("Profile not found")

        filtered_rules = list(rules)

        # Filter by categories
        if profile.rule_filter_categories:
            categories_set = set(profile.rule_filter_categories)
            filtered_rules = [
                r for r in filtered_rules
                if r.get("category", "") in categories_set
            ]

        # Filter by tag IDs (rules must have at least one matching tag)
        if profile.rule_filter_tags:
            tag_set = set(profile.rule_filter_tags)
            filtered_rules = [
                r for r in filtered_rules
                if tag_set.intersection(set(r.get("tag_ids", [])))
            ] if any(r.get("tag_ids") for r in filtered_rules) else filtered_rules

        return {
            "filtered_rules": filtered_rules,
            "system_preamble": profile.system_preamble or "",
            "temperature": profile.temperature,
            "max_tokens": profile.max_tokens,
        }

    async def _clear_default(self, user_id: UUID):
        """Unset default flag on all profiles for a user."""
        q = select(PromptProfile).where(
            and_(
                PromptProfile.user_id == user_id,
                PromptProfile.is_default == True,
            )
        )
        result = await self.db.execute(q)
        for p in result.scalars().all():
            p.is_default = False
        await self.db.flush()
