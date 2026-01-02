"""
Personal AI OS - Interaction Model
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship

from app.db.session import Base


class Interaction(Base):
    """
    Stores chat interactions for context and memory.
    
    When a correction leads to a rule, the interaction is linked to that rule.
    """
    
    __tablename__ = "interactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    conversation_id = Column(String(255), index=True)
    
    # Message content
    user_message = Column(Text, nullable=False)
    assistant_response = Column(Text, nullable=False)
    
    # Rules that were applied in this interaction
    rules_applied = Column(ARRAY(UUID(as_uuid=True)), default=[])
    
    # Correction tracking
    was_corrected = Column(Boolean, default=False)
    correction_text = Column(Text)
    extracted_rule_id = Column(UUID(as_uuid=True), ForeignKey("rules.id", ondelete="SET NULL"))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Vector store reference for semantic search
    embedding_id = Column(String(255))
    
    # Relationships
    user = relationship("User", back_populates="interactions")
    extracted_rule = relationship("Rule")
    
    def __repr__(self):
        return f"<Interaction {self.id}>"
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "user_message": self.user_message,
            "assistant_response": self.assistant_response,
            "rules_applied": [str(r) for r in (self.rules_applied or [])],
            "was_corrected": self.was_corrected,
            "correction_text": self.correction_text,
            "extracted_rule_id": str(self.extracted_rule_id) if self.extracted_rule_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
