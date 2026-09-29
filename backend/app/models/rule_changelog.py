"""
Personal AI OS - Rule Changelog Model

Tracks the full text history of every rule edit.
Every update appends a new row; existing rows are never mutated.
"""
import uuid
from datetime import datetime, UTC
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class RuleChangelog(Base):
    __tablename__ = "rule_changelog"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(UUID(as_uuid=True), ForeignKey("rules.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False)               # monotonically increasing per rule
    old_content = Column(Text, nullable=True)              # None on first creation
    new_content = Column(Text, nullable=False)
    changed_by = Column(String, nullable=True)             # user external_id or "system"
    change_reason = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    rule = relationship("Rule", back_populates="changelog")
