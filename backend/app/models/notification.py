"""
Personal AI OS - Notification Model

Queues notifications for rule lifecycle events and supports
periodic digest generation.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.session import Base


class Notification(Base):
    """
    A notification for a user about rule activity.

    Types: rule_created, rule_archived, conflict_detected,
    decay_warning, experiment_concluded, digest, system.
    """

    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Notification content
    type = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    body = Column(Text)
    extra_data = Column(JSONB, default={})

    # State
    is_read = Column(Boolean, default=False, index=True)
    is_archived = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    read_at = Column(DateTime)

    # Relationships
    user = relationship("User")

    def __repr__(self):
        return f"<Notification {self.id}: {self.type} - {self.title}>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "type": self.type,
            "title": self.title,
            "body": self.body,
            "extra_data": self.extra_data or {},
            "is_read": self.is_read,
            "is_archived": self.is_archived,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
        }
