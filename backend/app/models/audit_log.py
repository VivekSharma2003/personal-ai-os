"""
Personal AI OS - Audit Log Model
"""
import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.session import Base


class AuditEventType(str, Enum):
    """Types of events that are logged."""
    RULE_CREATED = "rule_created"
    RULE_APPLIED = "rule_applied"
    RULE_REINFORCED = "rule_reinforced"
    RULE_DECAYED = "rule_decayed"
    RULE_ARCHIVED = "rule_archived"
    RULE_EDITED = "rule_edited"
    RULE_DELETED = "rule_deleted"
    RULE_DISABLED = "rule_disabled"
    RULE_ENABLED = "rule_enabled"


class AuditLog(Base):
    """
    Audit log for transparency and debugging.
    
    Tracks all rule lifecycle events for user visibility.
    """
    
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rule_id = Column(UUID(as_uuid=True), ForeignKey("rules.id", ondelete="SET NULL"))
    
    event_type = Column(String(50), nullable=False)
    event_data = Column(JSONB, default={})
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    rule = relationship("Rule", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<AuditLog {self.event_type} at {self.created_at}>"
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "rule_id": str(self.rule_id) if self.rule_id else None,
            "event_type": self.event_type,
            "event_data": self.event_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
