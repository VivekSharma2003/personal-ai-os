"""
Personal AI OS - Conversation Model

Makes conversations first-class entities with support for branching/forking.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class Conversation(Base):
    """
    First-class conversation entity with branching support.

    Previously, conversations were just string IDs on interactions.
    This model adds metadata, titles, forking, and soft-delete capabilities.
    """

    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Metadata
    title = Column(String(500), default="New Conversation")
    description = Column(Text)

    # Forking support — self-referential FK
    parent_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"))
    forked_at_interaction_id = Column(UUID(as_uuid=True), ForeignKey("interactions.id", ondelete="SET NULL"))

    # Status
    is_archived = Column(Boolean, default=False)
    is_pinned = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")
    parent = relationship("Conversation", remote_side=[id], backref="forks")
    forked_at_interaction = relationship("Interaction")

    def __repr__(self):
        return f"<Conversation {self.id}: {self.title}>"

    def to_dict(self, include_fork_count=False):
        """Convert to dictionary for API responses."""
        result = {
            "id": str(self.id),
            "title": self.title,
            "description": self.description,
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "forked_at_interaction_id": str(self.forked_at_interaction_id) if self.forked_at_interaction_id else None,
            "is_archived": self.is_archived,
            "is_pinned": self.is_pinned,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_fork_count:
            result["fork_count"] = len(self.forks) if self.forks else 0
        return result
