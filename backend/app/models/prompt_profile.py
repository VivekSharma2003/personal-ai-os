"""
Personal AI OS - Prompt Profile Model

Named prompt profiles that pre-select rule subsets and LLM parameters.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.session import Base


class PromptProfile(Base):
    """
    A named prompt configuration profile.

    Profiles filter which rules to include (by tag or category),
    inject a custom system preamble, and override LLM parameters
    like temperature and max_tokens.
    """

    __tablename__ = "prompt_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text, default="")

    # Rule filtering
    rule_filter_tags = Column(JSONB, default=[])           # List of tag IDs (UUIDs) to include
    rule_filter_categories = Column(JSONB, default=[])     # List of category strings to include

    # Prompt customization
    system_preamble = Column(Text, default="")             # Prepended to system prompt

    # LLM parameter overrides (null = use default)
    temperature = Column(Float)
    max_tokens = Column(Integer)

    # Flags
    is_default = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")

    def __repr__(self):
        return f"<PromptProfile {self.id}: {self.name}>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "name": self.name,
            "description": self.description or "",
            "rule_filter_tags": self.rule_filter_tags or [],
            "rule_filter_categories": self.rule_filter_categories or [],
            "system_preamble": self.system_preamble or "",
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
