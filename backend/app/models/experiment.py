"""
Personal AI OS - Experiment Model

Supports A/B testing of rule variants to measure which produces
better user satisfaction.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class Experiment(Base):
    """
    A/B test comparing two rule variants.

    Traffic is split randomly between variant A and B.
    Satisfaction signals are collected to determine a winner.
    """

    __tablename__ = "experiments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default="running")  # running, paused, completed

    # Rule variants
    rule_a_id = Column(UUID(as_uuid=True), ForeignKey("rules.id", ondelete="SET NULL"))
    rule_b_id = Column(UUID(as_uuid=True), ForeignKey("rules.id", ondelete="SET NULL"))

    # Impression and outcome counters
    variant_a_impressions = Column(Integer, default=0)
    variant_b_impressions = Column(Integer, default=0)
    variant_a_positive = Column(Integer, default=0)
    variant_b_positive = Column(Integer, default=0)

    # Result
    winner = Column(String(10))  # "a", "b", or null if not yet determined
    min_sample_size = Column(Integer, default=50)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    # Relationships
    user = relationship("User")
    rule_a = relationship("Rule", foreign_keys=[rule_a_id])
    rule_b = relationship("Rule", foreign_keys=[rule_b_id])

    def __repr__(self):
        return f"<Experiment {self.id}: {self.name} [{self.status}]>"

    def to_dict(self):
        rate_a = (self.variant_a_positive / self.variant_a_impressions * 100) if self.variant_a_impressions > 0 else 0
        rate_b = (self.variant_b_positive / self.variant_b_impressions * 100) if self.variant_b_impressions > 0 else 0

        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "name": self.name,
            "status": self.status,
            "rule_a_id": str(self.rule_a_id) if self.rule_a_id else None,
            "rule_b_id": str(self.rule_b_id) if self.rule_b_id else None,
            "variant_a_impressions": self.variant_a_impressions,
            "variant_b_impressions": self.variant_b_impressions,
            "variant_a_positive": self.variant_a_positive,
            "variant_b_positive": self.variant_b_positive,
            "variant_a_rate": round(rate_a, 1),
            "variant_b_rate": round(rate_b, 1),
            "winner": self.winner,
            "min_sample_size": self.min_sample_size,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
