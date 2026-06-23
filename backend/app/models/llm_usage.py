"""
Personal AI OS - LLM Usage Model

Tracks per-request token usage and estimated cost for each LLM call.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class LLMUsage(Base):
    """
    Records token usage and cost for every LLM API call.

    Used for cost analytics, budget enforcement, and usage trending.
    """

    __tablename__ = "llm_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # LLM call details
    provider = Column(String(50), nullable=False)       # openai, gemini, anthropic
    model = Column(String(100), nullable=False)          # gpt-4-turbo-preview, gemini-1.5-pro, etc.
    endpoint = Column(String(50), nullable=False)        # chat, stream, extract, feedback, etc.

    # Token counts
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)

    # Cost
    estimated_cost_usd = Column(Float, nullable=False, default=0.0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User")

    def __repr__(self):
        return f"<LLMUsage {self.id}: {self.provider}/{self.model} {self.total_tokens} tokens ${self.estimated_cost_usd:.4f}>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "provider": self.provider,
            "model": self.model,
            "endpoint": self.endpoint,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
