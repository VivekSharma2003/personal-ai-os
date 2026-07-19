"""
Personal AI OS - Decay Policy Model

Supports context-aware dynamic decay curves and policy overrides
per tag or rule category.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class DecayPolicy(Base):
    """
    Decay policy representing specific rules for preference decay.
    Policies can target specific tags, categories, or serve as general user policies.
    """

    __tablename__ = "decay_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tag_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="CASCADE"),
        nullable=True,
    )

    category = Column(String(50), nullable=True)  # optional override per category (style, tone, etc)

    base_decay_rate = Column(Float, nullable=False, default=0.05)
    grace_period_days = Column(Integer, nullable=False, default=7)
    topic_sensitivity = Column(Float, nullable=False, default=1.0)  # sensitivity multiplier (0.0 to 1.0+)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")
    tag = relationship("Tag")

    def __repr__(self):
        return f"<DecayPolicy {self.id}: user={self.user_id} tag={self.tag_id} rate={self.base_decay_rate}>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "tag_id": str(self.tag_id) if self.tag_id else None,
            "category": self.category,
            "base_decay_rate": self.base_decay_rate,
            "grace_period_days": self.grace_period_days,
            "topic_sensitivity": self.topic_sensitivity,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
