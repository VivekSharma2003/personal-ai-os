"""
Personal AI OS - Data Retention Service

Manages data retention policies and executes cleanup of expired records.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID
from sqlalchemy import select, delete, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.retention import RetentionPolicy
from app.models.interaction import Interaction
from app.models.audit_log import AuditLog
from app.models.conversation import Conversation
from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger("services.retention")

# Map resource types to their models and date columns
RESOURCE_MAP = {
    "interactions": (Interaction, Interaction.created_at),
    "audit_logs": (AuditLog, AuditLog.created_at),
    "conversations": (Conversation, Conversation.created_at),
}


class RetentionService:
    """
    Manages data retention policies and executes cleanup.

    Each resource type (interactions, audit_logs, conversations) can have
    a user-specific retention period. Falls back to system defaults from config.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._settings = get_settings()

    # ------------------------------------------------------------------
    # Policy CRUD
    # ------------------------------------------------------------------

    async def get_policies(self, user_id: UUID) -> List[Dict[str, Any]]:
        """
        Get all retention policies for a user.

        Includes system defaults for any unconfigured resource types.
        """
        result = await self.db.execute(
            select(RetentionPolicy).where(RetentionPolicy.user_id == user_id)
        )
        user_policies = {p.resource_type: p for p in result.scalars().all()}

        defaults = self._get_defaults()
        policies = []

        for resource_type, default_days in defaults.items():
            if resource_type in user_policies:
                policy = user_policies[resource_type]
                policies.append({
                    **policy.to_dict(),
                    "is_custom": True,
                })
            else:
                policies.append({
                    "id": None,
                    "user_id": str(user_id),
                    "resource_type": resource_type,
                    "retention_days": default_days,
                    "is_custom": False,
                    "created_at": None,
                    "updated_at": None,
                })

        return policies

    async def set_policy(
        self, user_id: UUID, resource_type: str, retention_days: int
    ) -> RetentionPolicy:
        """Create or update a retention policy for a resource type."""
        if resource_type not in RESOURCE_MAP:
            raise ValueError(
                f"Invalid resource_type: {resource_type}. "
                f"Valid types: {list(RESOURCE_MAP.keys())}"
            )

        result = await self.db.execute(
            select(RetentionPolicy).where(
                RetentionPolicy.user_id == user_id,
                RetentionPolicy.resource_type == resource_type,
            )
        )
        policy = result.scalar_one_or_none()

        if policy:
            policy.retention_days = retention_days
            policy.updated_at = datetime.utcnow()
        else:
            policy = RetentionPolicy(
                user_id=user_id,
                resource_type=resource_type,
                retention_days=retention_days,
            )
            self.db.add(policy)

        await self.db.flush()

        logger.info(
            f"Retention policy set: {resource_type} = {retention_days}d",
            extra={"extra_data": {"user_id": str(user_id)}},
        )

        return policy

    # ------------------------------------------------------------------
    # Cleanup execution
    # ------------------------------------------------------------------

    async def execute_cleanup(self, user_id: UUID) -> Dict[str, int]:
        """
        Delete records older than the retention period for each resource type.

        Returns dict of {resource_type: deleted_count}.
        """
        policies = await self._get_effective_policies(user_id)
        results = {}

        for resource_type, retention_days in policies.items():
            if retention_days == 0:
                results[resource_type] = 0  # 0 = keep forever
                continue

            cutoff = datetime.utcnow() - timedelta(days=retention_days)
            model, date_col = RESOURCE_MAP[resource_type]

            # Build delete query with user filter
            if hasattr(model, "user_id"):
                stmt = delete(model).where(
                    and_(model.user_id == user_id, date_col < cutoff)
                )
            else:
                stmt = delete(model).where(date_col < cutoff)

            result = await self.db.execute(stmt)
            deleted = result.rowcount
            results[resource_type] = deleted

            if deleted > 0:
                logger.info(
                    f"Retention cleanup: deleted {deleted} {resource_type} "
                    f"older than {retention_days}d",
                    extra={"extra_data": {"user_id": str(user_id)}},
                )

        return results

    async def preview_cleanup(self, user_id: UUID) -> Dict[str, int]:
        """
        Dry-run: show how many records WOULD be deleted for each resource type.
        """
        policies = await self._get_effective_policies(user_id)
        results = {}

        for resource_type, retention_days in policies.items():
            if retention_days == 0:
                results[resource_type] = 0
                continue

            cutoff = datetime.utcnow() - timedelta(days=retention_days)
            model, date_col = RESOURCE_MAP[resource_type]

            if hasattr(model, "user_id"):
                stmt = select(func.count()).select_from(model).where(
                    and_(model.user_id == user_id, date_col < cutoff)
                )
            else:
                stmt = select(func.count()).select_from(model).where(date_col < cutoff)

            result = await self.db.execute(stmt)
            count = result.scalar() or 0
            results[resource_type] = count

        return results

    # ------------------------------------------------------------------
    # Storage stats
    # ------------------------------------------------------------------

    async def get_storage_stats(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get record counts per resource type for a user.
        """
        stats = {}

        for resource_type, (model, date_col) in RESOURCE_MAP.items():
            if hasattr(model, "user_id"):
                result = await self.db.execute(
                    select(
                        func.count().label("total"),
                        func.min(date_col).label("oldest"),
                        func.max(date_col).label("newest"),
                    ).where(model.user_id == user_id)
                )
            else:
                result = await self.db.execute(
                    select(
                        func.count().label("total"),
                        func.min(date_col).label("oldest"),
                        func.max(date_col).label("newest"),
                    )
                )

            row = result.one()
            stats[resource_type] = {
                "total_records": row.total or 0,
                "oldest_record": row.oldest.isoformat() if row.oldest else None,
                "newest_record": row.newest.isoformat() if row.newest else None,
            }

        return stats

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _get_effective_policies(
        self, user_id: UUID
    ) -> Dict[str, int]:
        """Get effective retention days per resource type (user override or default)."""
        result = await self.db.execute(
            select(RetentionPolicy).where(RetentionPolicy.user_id == user_id)
        )
        user_policies = {p.resource_type: p.retention_days for p in result.scalars().all()}

        defaults = self._get_defaults()
        return {
            rt: user_policies.get(rt, default_days)
            for rt, default_days in defaults.items()
        }

    def _get_defaults(self) -> Dict[str, int]:
        """Get system default retention days from config."""
        return {
            "interactions": self._settings.retention_interactions_days,
            "audit_logs": self._settings.retention_audit_days,
            "conversations": self._settings.retention_conversations_days,
        }
