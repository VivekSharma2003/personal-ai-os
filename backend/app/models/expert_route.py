"""
Personal AI OS - Expert Route Database Model
"""
import uuid
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, UTC

from app.db.session import Base

class ExpertRoute(Base):
    __tablename__ = "expert_routes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    intent = Column(String, unique=True, index=True, nullable=False)
    provider = Column(String, nullable=False) # e.g., "openai", "anthropic", "gemini"
    model = Column(String, nullable=False)    # e.g., "gpt-4-turbo", "claude-3-opus"
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
