"""
Personal AI OS - User Preferences Service

get_or_create, patch (deep-merge), reset, and section-level reads.
"""
import logging
from typing import Any, Dict, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, UTC

from app.models.user_preferences import UserPreferences

logger = logging.getLogger(__name__)


def _deep_merge(base: dict, patch: dict) -> dict:
    """Recursively merge *patch* into *base* (patch wins on scalar conflicts)."""
    result = dict(base)
    for key, value in patch.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class PreferencesService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create(self, user_id: UUID) -> UserPreferences:
        result = await self.db.execute(
            select(UserPreferences).where(UserPreferences.user_id == user_id)
        )
        prefs = result.scalars().first()
        if prefs is None:
            prefs = UserPreferences(user_id=user_id, llm={}, ui={}, notifications={}, custom={})
            self.db.add(prefs)
            await self.db.flush()
        return prefs

    async def get(self, user_id: UUID) -> Optional[UserPreferences]:
        result = await self.db.execute(
            select(UserPreferences).where(UserPreferences.user_id == user_id)
        )
        return result.scalars().first()

    async def patch(
        self,
        user_id: UUID,
        llm: Optional[Dict] = None,
        ui: Optional[Dict] = None,
        notifications: Optional[Dict] = None,
        custom: Optional[Dict] = None,
    ) -> UserPreferences:
        """Deep-merge the supplied sections into the user's existing preferences."""
        prefs = await self.get_or_create(user_id)

        if llm is not None:
            prefs.llm = _deep_merge(prefs.llm or {}, llm)
        if ui is not None:
            prefs.ui = _deep_merge(prefs.ui or {}, ui)
        if notifications is not None:
            prefs.notifications = _deep_merge(prefs.notifications or {}, notifications)
        if custom is not None:
            prefs.custom = _deep_merge(prefs.custom or {}, custom)

        prefs.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(prefs)
        return prefs

    async def reset_section(self, user_id: UUID, section: str) -> UserPreferences:
        """Reset a single preference section to an empty dict."""
        valid = {"llm", "ui", "notifications", "custom"}
        if section not in valid:
            raise ValueError(f"Invalid section '{section}'. Must be one of {valid}")
        prefs = await self.get_or_create(user_id)
        setattr(prefs, section, {})
        prefs.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(prefs)
        return prefs

    def _to_dict(self, prefs: UserPreferences) -> Dict[str, Any]:
        return {
            "user_id": str(prefs.user_id),
            "llm": prefs.llm or {},
            "ui": prefs.ui or {},
            "notifications": prefs.notifications or {},
            "custom": prefs.custom or {},
            "updated_at": prefs.updated_at.isoformat() if prefs.updated_at else None,
        }
