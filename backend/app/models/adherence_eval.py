"""
Personal AI OS - Adherence Evaluation Model

Tracks automated evaluations of whether assistant responses adhered
to active system rules. Used to trigger self-healing prompt optimization.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class AdherenceEvaluation(Base):
    """
    Evaluation entry judging whether an assistant response adhered to a specific rule.
    Multiple evaluations per rule allow tracing performance trends.
    """

    __tablename__ = "adherence_evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interaction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("interactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_id = Column(
        UUID(as_uuid=True),
        ForeignKey("rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    adhered = Column(Boolean, nullable=False, default=True)
    score = Column(Float, nullable=False, default=1.0)  # judge adherence score (0.0 to 1.0)
    justification = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    interaction = relationship("Interaction")
    rule = relationship("Rule")

    def __repr__(self):
        return f"<AdherenceEvaluation {self.id}: rule={self.rule_id} score={self.score}>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "interaction_id": str(self.interaction_id),
            "rule_id": str(self.rule_id),
            "adhered": self.adhered,
            "score": self.score,
            "justification": self.justification,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
