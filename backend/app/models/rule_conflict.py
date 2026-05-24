"""
Personal AI OS - Rule Conflict Model
"""
import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.session import Base


class ConflictStatus(str, Enum):
    """Status of a detected conflict."""
    ACTIVE = "active"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class ConflictResolution(str, Enum):
    """Resolution strategies for conflicts."""
    KEEP_BOTH = "keep_both"
    KEEP_NEWER = "keep_newer"
    KEEP_OLDER = "keep_older"
    MERGE = "merge"
    DISABLE_ONE = "disable_one"


class RuleConflict(Base):
    """
    Tracks detected conflicts between two rules.

    When two rules contradict each other (e.g., "use formal tone" vs "keep it casual"),
    a conflict record is created for user resolution.
    """

    __tablename__ = "rule_conflicts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # The two conflicting rules
    rule_a_id = Column(UUID(as_uuid=True), ForeignKey("rules.id", ondelete="CASCADE"), nullable=False)
    rule_b_id = Column(UUID(as_uuid=True), ForeignKey("rules.id", ondelete="CASCADE"), nullable=False)

    # Conflict details
    explanation = Column(Text, nullable=False)
    severity = Column(Float, default=0.5)  # 0-1, how severe the conflict is
    suggested_resolution = Column(String(50), default=ConflictResolution.KEEP_BOTH.value)

    # Status
    status = Column(String(20), default=ConflictStatus.ACTIVE.value)
    resolved_at = Column(DateTime)
    resolution_applied = Column(String(50))  # Which resolution was actually applied
    resolution_details = Column(JSONB, default={})

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")
    rule_a = relationship("Rule", foreign_keys=[rule_a_id])
    rule_b = relationship("Rule", foreign_keys=[rule_b_id])

    def __repr__(self):
        return f"<RuleConflict {self.id}: {self.rule_a_id} vs {self.rule_b_id}>"

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "rule_a_id": str(self.rule_a_id),
            "rule_b_id": str(self.rule_b_id),
            "rule_a_content": self.rule_a.content if self.rule_a else None,
            "rule_b_content": self.rule_b.content if self.rule_b else None,
            "explanation": self.explanation,
            "severity": round(self.severity, 2),
            "suggested_resolution": self.suggested_resolution,
            "status": self.status,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution_applied": self.resolution_applied,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
