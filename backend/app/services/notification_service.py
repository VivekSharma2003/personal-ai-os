"""
Personal AI OS - Notification Service

Creates, lists, and manages notifications for rule lifecycle events.
Generates LLM-powered daily digests of rule activity.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4

from sqlalchemy import select, func, and_, update, delete, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.audit_log import AuditLog
from app.core.logging import get_logger

logger = get_logger("services.notification")


class NotificationService:
    """Service for user notifications and activity digests."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_notification(
        self,
        user_id: UUID,
        type: str,
        title: str,
        body: str = None,
        extra_data: dict = None,
    ) -> Dict[str, Any]:
        """
        Create a new notification for a user.

        Also publishes a 'notification.created' event on the EventBus.
        """
        notification = Notification(
            id=uuid4(),
            user_id=user_id,
            type=type,
            title=title,
            body=body,
            extra_data=extra_data or {},
        )
        self.db.add(notification)

        # Publish event
        try:
            from app.core.events import get_event_bus
            event_bus = get_event_bus()
            await event_bus.publish("notification.created", {
                "user_id": str(user_id),
                "notification_id": str(notification.id),
                "type": type,
                "title": title,
            })
        except Exception:
            pass  # Non-critical

        logger.info(
            "Notification created",
            extra={"extra_data": {
                "user_id": str(user_id),
                "type": type,
                "notification_id": str(notification.id),
            }},
        )

        return notification.to_dict()

    async def list_notifications(
        self,
        user_id: UUID,
        unread_only: bool = False,
        type_filter: str = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """List notifications for a user with pagination and filters."""
        conditions = [Notification.user_id == user_id, Notification.is_archived == False]

        if unread_only:
            conditions.append(Notification.is_read == False)
        if type_filter:
            conditions.append(Notification.type == type_filter)

        # Count
        count_q = await self.db.execute(
            select(func.count()).select_from(Notification).where(and_(*conditions))
        )
        total = count_q.scalar() or 0

        # Fetch
        result = await self.db.execute(
            select(Notification)
            .where(and_(*conditions))
            .order_by(desc(Notification.created_at))
            .limit(limit)
            .offset(offset)
        )
        items = [n.to_dict() for n in result.scalars().all()]

        return {"total": total, "limit": limit, "offset": offset, "notifications": items}

    async def get_unread_count(self, user_id: UUID) -> Dict[str, Any]:
        """Get unread notification count for badge display."""
        result = await self.db.execute(
            select(func.count()).select_from(Notification).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False,
                    Notification.is_archived == False,
                )
            )
        )
        count = result.scalar() or 0

        # Also get per-type breakdown
        type_q = await self.db.execute(
            select(Notification.type, func.count())
            .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False,
                    Notification.is_archived == False,
                )
            )
            .group_by(Notification.type)
        )
        by_type = {row[0]: row[1] for row in type_q.fetchall()}

        return {"unread_count": count, "by_type": by_type}

    async def mark_read(self, notification_id: UUID) -> Dict[str, Any]:
        """Mark a single notification as read."""
        result = await self.db.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        notification = result.scalar_one_or_none()
        if not notification:
            return {"error": "Notification not found"}

        notification.is_read = True
        notification.read_at = datetime.utcnow()

        return {"marked_read": True, "notification_id": str(notification_id)}

    async def mark_all_read(self, user_id: UUID) -> Dict[str, Any]:
        """Mark all unread notifications as read for a user."""
        now = datetime.utcnow()
        result = await self.db.execute(
            update(Notification)
            .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False,
                )
            )
            .values(is_read=True, read_at=now)
        )
        count = result.rowcount

        return {"marked_read": count}

    async def delete_notification(self, notification_id: UUID, user_id: UUID) -> Dict[str, Any]:
        """Delete (archive) a notification."""
        result = await self.db.execute(
            select(Notification).where(
                and_(
                    Notification.id == notification_id,
                    Notification.user_id == user_id,
                )
            )
        )
        notification = result.scalar_one_or_none()
        if not notification:
            return {"error": "Notification not found"}

        notification.is_archived = True

        return {"deleted": True, "notification_id": str(notification_id)}

    async def generate_digest(self, user_id: UUID) -> Dict[str, Any]:
        """
        Generate an LLM-powered daily digest summarizing recent rule activity.

        Pulls the last 24 hours of audit log events and summarizes them.
        """
        since = datetime.utcnow() - timedelta(days=1)

        # Fetch recent audit events
        result = await self.db.execute(
            select(AuditLog)
            .where(
                and_(
                    AuditLog.user_id == user_id,
                    AuditLog.created_at >= since,
                )
            )
            .order_by(desc(AuditLog.created_at))
            .limit(100)
        )
        events = list(result.scalars().all())

        if not events:
            return {
                "digest": "No rule activity in the last 24 hours. Your preferences are stable!",
                "event_count": 0,
                "period": "24h",
            }

        # Summarize event types
        event_summary = {}
        for event in events:
            event_summary[event.event_type] = event_summary.get(event.event_type, 0) + 1

        summary_lines = [f"- {count} × {etype}" for etype, count in event_summary.items()]
        summary_text = "\n".join(summary_lines)

        # Use LLM to generate natural language digest
        from app.core.llm import call_llm

        try:
            digest_text = await call_llm(
                messages=[{
                    "role": "user",
                    "content": (
                        "You are a personal AI assistant summarizing rule activity. "
                        "Given the following audit events from the last 24 hours, write a brief, "
                        "friendly digest (2-4 sentences) summarizing what happened with the user's "
                        "AI preferences. Be concise and conversational.\n\n"
                        f"Events:\n{summary_text}\n\n"
                        f"Total events: {len(events)}"
                    ),
                }],
                temperature=0.5,
                max_tokens=200,
            )
        except Exception:
            digest_text = (
                f"In the last 24 hours, there were {len(events)} rule events: "
                + ", ".join(f"{count} {etype}" for etype, count in event_summary.items())
                + "."
            )

        # Store digest as a notification
        await self.create_notification(
            user_id=user_id,
            type="digest",
            title="Daily Rule Activity Digest",
            body=digest_text.strip(),
            extra_data={"event_counts": event_summary, "total_events": len(events)},
        )

        logger.info(
            "Digest generated",
            extra={"extra_data": {
                "user_id": str(user_id),
                "event_count": len(events),
            }},
        )

        return {
            "digest": digest_text.strip(),
            "event_count": len(events),
            "event_breakdown": event_summary,
            "period": "24h",
        }
