"""
Personal AI OS - LLM Fallback Policy Model
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class LLMFallbackPolicy(Base):
    """
    Fallback policy for LLM interactions.
    Defines fallback models/providers in case the primary one fails.
    """
    
    __tablename__ = "llm_fallback_policies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    primary_provider = Column(String(100), nullable=False)
    primary_model = Column(String(100), nullable=False)
    fallback_provider = Column(String(100), nullable=False)
    fallback_model = Column(String(100), nullable=False)
    
    max_retries = Column(Integer, default=3)
    backoff_factor = Column(Float, default=2.0)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="fallback_policies")
    
    def __repr__(self):
        return f"<LLMFallbackPolicy {self.primary_provider}/{self.primary_model} -> {self.fallback_provider}/{self.fallback_model}>"
