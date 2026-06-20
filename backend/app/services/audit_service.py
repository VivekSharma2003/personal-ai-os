"""
Personal AI OS - Audit Service

Provides paginated, filterable access to the audit log with
aggregate stats and CSV export.
"""
import csv
import io
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


class AuditService:
    """Service for querying and exporting audit logs."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_logs(
        self,
        user_id: UUID,
        event_type: Optional[str] = None,
        rule_id: Optional[UUID] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[List[AuditLog], int]:
        """
        Get paginated audit logs with optional filters.

        Args:
            user_id: UUID of the user.
            event_type: Filter by event type (e.g., "rule_created").
            rule_id: Filter by specific rule.
            from_date: Start of date range.
            to_date: End of date range.
            page: Page number (1-indexed).
            page_size: Items per page.

        Returns:
            Tuple of (logs, total_count).
        """
        conditions = [AuditLog.user_id == user_id]

        if event_type:
            conditions.append(AuditLog.event_type == event_type)
        if rule_id:
            conditions.append(AuditLog.rule_id == rule_id)
        if from_date:
            conditions.append(AuditLog.created_at >= from_date)
        if to_date:
            conditions.append(AuditLog.created_at <= to_date)

        where_clause = and_(*conditions)

        # Get total count
        count_query = select(func.count(AuditLog.id)).where(where_clause)
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results
        offset = (page - 1) * page_size
        query = (
            select(AuditLog)
            .where(where_clause)
            .order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )

        result = await self.db.execute(query)
        logs = list(result.scalars().all())

        return logs, total

    async def get_log(self, log_id: UUID) -> Optional[AuditLog]:
        """Get a single audit log entry by ID."""
        result = await self.db.execute(
            select(AuditLog).where(AuditLog.id == log_id)
        )
        return result.scalar_one_or_none()

    async def get_stats(
        self,
        user_id: UUID,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get aggregated audit statistics for a user.

        Returns event type counts and recent activity summary.
        """
        conditions = [AuditLog.user_id == user_id]
        if from_date:
            conditions.append(AuditLog.created_at >= from_date)
        if to_date:
            conditions.append(AuditLog.created_at <= to_date)

        where_clause = and_(*conditions)

        # Count by event type
        type_query = (
            select(AuditLog.event_type, func.count(AuditLog.id).label("count"))
            .where(where_clause)
            .group_by(AuditLog.event_type)
            .order_by(func.count(AuditLog.id).desc())
        )

        type_result = await self.db.execute(type_query)
        event_counts = {row.event_type: row.count for row in type_result}

        # Total count
        total_query = select(func.count(AuditLog.id)).where(where_clause)
        total_result = await self.db.execute(total_query)
        total = total_result.scalar() or 0

        # Most recent event
        recent_query = (
            select(AuditLog)
            .where(where_clause)
            .order_by(AuditLog.created_at.desc())
            .limit(1)
        )
        recent_result = await self.db.execute(recent_query)
        most_recent = recent_result.scalar_one_or_none()

        return {
            "total_events": total,
            "event_counts": event_counts,
            "most_recent": most_recent.to_dict() if most_recent else None,
        }

    async def export_csv(
        self,
        user_id: UUID,
        event_type: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> str:
        """
        Export audit logs as a CSV string.

        Returns the CSV content as a string for streaming response.
        """
        conditions = [AuditLog.user_id == user_id]
        if event_type:
            conditions.append(AuditLog.event_type == event_type)
        if from_date:
            conditions.append(AuditLog.created_at >= from_date)
        if to_date:
            conditions.append(AuditLog.created_at <= to_date)

        query = (
            select(AuditLog)
            .where(and_(*conditions))
            .order_by(AuditLog.created_at.desc())
            .limit(10000)  # Safety cap
        )

        result = await self.db.execute(query)
        logs = result.scalars().all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "rule_id", "event_type", "event_data", "created_at"])

        for log in logs:
            writer.writerow([
                str(log.id),
                str(log.rule_id) if log.rule_id else "",
                log.event_type,
                str(log.event_data) if log.event_data else "",
                log.created_at.isoformat() if log.created_at else "",
            ])

        return output.getvalue()
