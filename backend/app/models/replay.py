"""
Personal AI OS - Replay Model

Supports prompt replay and regression testing by re-running past
interactions against the current rule set and comparing outputs.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class ReplayRun(Base):
    """
    A replay run that re-processes past interactions with current rules.

    Detects regressions and improvements after rule changes.
    """

    __tablename__ = "replay_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name = Column(String(255), nullable=False)
    status = Column(String(20), default="pending")  # pending, running, completed, failed

    # Progress counters
    total_interactions = Column(Integer, default=0)
    completed = Column(Integer, default=0)
    regressions_found = Column(Integer, default=0)
    improvements_found = Column(Integer, default=0)
    unchanged_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    # Relationships
    user = relationship("User")
    results = relationship("ReplayResult", back_populates="run", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ReplayRun {self.id}: {self.name} [{self.status}]>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "name": self.name,
            "status": self.status,
            "total_interactions": self.total_interactions,
            "completed": self.completed,
            "regressions_found": self.regressions_found,
            "improvements_found": self.improvements_found,
            "unchanged_count": self.unchanged_count,
            "progress_pct": round(
                (self.completed / self.total_interactions * 100)
                if self.total_interactions > 0 else 0, 1
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class ReplayResult(Base):
    """
    Result of replaying a single interaction.

    Stores the original response, replayed response, similarity score,
    and verdict (regression / improved / unchanged).
    """

    __tablename__ = "replay_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("replay_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    interaction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("interactions.id", ondelete="SET NULL"),
    )

    # Original vs replayed
    original_prompt = Column(Text)
    original_response = Column(Text)
    replayed_response = Column(Text)

    # Comparison metrics
    similarity_score = Column(Float, default=0.0)
    verdict = Column(String(20))  # regression, improved, unchanged

    # LLM-generated diff summary
    diff_summary = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    run = relationship("ReplayRun", back_populates="results")

    def __repr__(self):
        return f"<ReplayResult {self.id}: {self.verdict}>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "run_id": str(self.run_id),
            "interaction_id": str(self.interaction_id) if self.interaction_id else None,
            "original_prompt": self.original_prompt,
            "original_response": self.original_response,
            "replayed_response": self.replayed_response,
            "similarity_score": round(self.similarity_score, 3) if self.similarity_score else 0,
            "verdict": self.verdict,
            "diff_summary": self.diff_summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
