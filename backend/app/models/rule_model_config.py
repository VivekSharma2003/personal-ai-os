"""
Personal AI OS - Rule Model Configuration Overrides

Supports defining custom temperature, max tokens, and prompt optimizations
per LLM model/provider for a given rule.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class RuleModelConfig(Base):
    """
    Model-specific configurations and optimization overrides for a rule.
    Allows adjusting rules specifically for target models (e.g. Claude vs GPT-4).
    """

    __tablename__ = "rule_model_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(
        UUID(as_uuid=True),
        ForeignKey("rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    provider = Column(String(50), nullable=False)  # openai, gemini, anthropic
    model_name = Column(String(100), nullable=False)  # e.g., gpt-4-turbo-preview, or * for all

    temperature_override = Column(Float, nullable=True)
    max_tokens_override = Column(Integer, nullable=True)
    optimized_content = Column(Text, nullable=True)  # custom rephrasing of the rule content

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    rule = relationship("Rule", back_populates="model_configs")

    def __repr__(self):
        return f"<RuleModelConfig {self.id}: rule={self.rule_id} model={self.provider}/{self.model_name}>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "rule_id": str(self.rule_id),
            "provider": self.provider,
            "model_name": self.model_name,
            "temperature_override": self.temperature_override,
            "max_tokens_override": self.max_tokens_override,
            "optimized_content": self.optimized_content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
