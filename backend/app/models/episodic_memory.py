"""
Personal AI OS - Episodic Memory Model
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.session import Base


class EpisodicMemory(Base):
    """
    Represents a consolidated memory profile from a conversation thread.
    """
    
    __tablename__ = "episodic_memories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    summary = Column(Text, nullable=False)
    key_takeaways = Column(JSONB, nullable=False)
    
    embedding_id = Column(String(255))
    interaction_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="episodic_memories")
    
    def __repr__(self):
        return f"<EpisodicMemory {self.id}>"
