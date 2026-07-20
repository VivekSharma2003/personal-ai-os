"""
Personal AI OS - Shared Rule Model

Enables rules to be published to a community library where other
users can browse, install, and rate them.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class SharedRule(Base):
    """
    A rule published to the shared community library.

    Authors can publish their rules for others to install.
    Tracks install count and average rating.
    """

    __tablename__ = "shared_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    author_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_rule_id = Column(
        UUID(as_uuid=True),
        ForeignKey("rules.id", ondelete="SET NULL"),
    )

    # Content snapshot (immutable copy from the source rule)
    title = Column(String(255), nullable=False)
    description = Column(String(1000))
    content = Column(Text, nullable=False)
    category = Column(String(50), nullable=False)

    # Community metrics
    install_count = Column(Integer, default=0)
    rating_sum = Column(Float, default=0.0)
    rating_count = Column(Integer, default=0)

    # Visibility
    visibility = Column(String(20), default="public")  # public, unlisted

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    author = relationship("User")
    source_rule = relationship("Rule")

    def __repr__(self):
        return f"<SharedRule {self.id}: {self.title}>"

    @property
    def avg_rating(self) -> float:
        if self.rating_count and self.rating_count > 0:
            return round(self.rating_sum / self.rating_count, 1)
        return 0.0

    def to_dict(self):
        return {
            "id": str(self.id),
            "author_user_id": str(self.author_user_id),
            "source_rule_id": str(self.source_rule_id) if self.source_rule_id else None,
            "title": self.title,
            "description": self.description,
            "content": self.content,
            "category": self.category,
            "install_count": self.install_count,
            "avg_rating": self.avg_rating,
            "rating_count": self.rating_count,
            "visibility": self.visibility,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
