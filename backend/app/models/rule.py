"""
Personal AI OS - Rule Model
"""
import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class RuleCategory(str, Enum):
    """Categories for rules."""
    STYLE = "style"
    TONE = "tone"
    FORMATTING = "formatting"
    LOGIC = "logic"
    SAFETY = "safety"


class RuleStatus(str, Enum):
    """Status of a rule."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DISABLED = "disabled"


class Rule(Base):
    """
    Core entity representing a learned user preference.
    
    Rules are extracted from user corrections and applied to future responses.
    """
    
    __tablename__ = "rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Rule content
    content = Column(Text, nullable=False)  # The generalized rule
    original_correction = Column(Text)  # User's original correction
    category = Column(String(50), nullable=False, default=RuleCategory.STYLE.value)
    
    # Confidence tracking
    confidence = Column(Float, default=0.5)  # 0-1 score
    times_applied = Column(Integer, default=0)
    times_reinforced = Column(Integer, default=0)
    
    # Status
    status = Column(String(20), default=RuleStatus.ACTIVE.value)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_applied_at = Column(DateTime)
    last_reinforced_at = Column(DateTime)
    
    # Vector store reference
    embedding_id = Column(String(255))
    
    # Relationships
    user = relationship("User", back_populates="rules")
    audit_logs = relationship("AuditLog", back_populates="rule")
    
    def __repr__(self):
        return f"<Rule {self.id}: {self.content[:50]}...>"
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "content": self.content,
            "original_correction": self.original_correction,
            "category": self.category,
            "confidence": round(self.confidence, 2),
            "times_applied": self.times_applied,
            "times_reinforced": self.times_reinforced,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_applied_at": self.last_applied_at.isoformat() if self.last_applied_at else None,
        }
