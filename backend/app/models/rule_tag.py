"""
Personal AI OS - Tag Model

Provides flexible tag-based organization of rules via a many-to-many
association.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


# Many-to-many association table
rule_tags = Table(
    "rule_tags",
    Base.metadata,
    Column(
        "rule_id",
        UUID(as_uuid=True),
        ForeignKey("rules.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        UUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Tag(Base):
    """
    A user-defined label for organizing rules.

    Tags support many-to-many relationships with rules,
    enabling flexible grouping and filtering.
    """

    __tablename__ = "tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name = Column(String(100), nullable=False)
    color = Column(String(7), default="#6366f1")  # Hex color code

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="tags")
    rules = relationship("Rule", secondary=rule_tags, backref="tags")

    def __repr__(self):
        return f"<Tag {self.name}>"

    def to_dict(self, include_rule_count: bool = False):
        """Convert to dictionary for API responses."""
        d = {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "name": self.name,
            "color": self.color,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_rule_count:
            d["rule_count"] = len(self.rules) if self.rules else 0
        return d
