"""
Personal AI OS - Rule Version Model

Tracks every change to a rule over time for undo, diffing, and evolution tracking.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class RuleVersion(Base):
    """
    Snapshot of a rule's state at a point in time.

    Created before any mutation to a rule, capturing the full state
    so users can view history, compute diffs, and rollback changes.
    """

    __tablename__ = "rule_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(UUID(as_uuid=True), ForeignKey("rules.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)

    # Snapshot of rule state
    content = Column(Text, nullable=False)
    category = Column(String(50), nullable=False)
    confidence = Column(Float, nullable=False)
    status = Column(String(20), nullable=False)

    # Change metadata
    changed_by = Column(String(20), default="user")  # "user" | "system" | "decay" | "import"
    change_reason = Column(Text)  # Human-readable description of why the change was made

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    rule = relationship("Rule")

    def __repr__(self):
        return f"<RuleVersion {self.rule_id} v{self.version_number}>"

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "rule_id": str(self.rule_id),
            "version_number": self.version_number,
            "content": self.content,
            "category": self.category,
            "confidence": round(self.confidence, 2),
            "status": self.status,
            "changed_by": self.changed_by,
            "change_reason": self.change_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
