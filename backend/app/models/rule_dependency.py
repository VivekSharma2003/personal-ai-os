"""
Personal AI OS - Rule Dependency Model
"""
import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class DependencyType(str, Enum):
    """Types of rule dependencies."""
    REQUIRES = "requires"    # Child only active if parent is active
    EXCLUDES = "excludes"    # Child only active if parent is NOT active
    ENHANCES = "enhances"    # Advisory — parent is recommended but not required


class RuleDependency(Base):
    """
    Dependency relationship between two rules.

    Allows rules to conditionally activate based on other rules' state.
    For example:
      - "Bullet point formatting" REQUIRES "Formal tone" (only format if formal)
      - "Casual greetings" EXCLUDES "Formal tone" (mutually exclusive)
      - "Code examples" ENHANCES "Technical style" (works better together)
    """

    __tablename__ = "rule_dependencies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # The rule that has the dependency (child)
    rule_id = Column(
        UUID(as_uuid=True),
        ForeignKey("rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # The rule it depends on (parent)
    depends_on_rule_id = Column(
        UUID(as_uuid=True),
        ForeignKey("rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Type of dependency
    dependency_type = Column(
        String(20),
        nullable=False,
        default=DependencyType.REQUIRES.value,
    )

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    rule = relationship("Rule", foreign_keys=[rule_id], backref="dependencies")
    depends_on = relationship("Rule", foreign_keys=[depends_on_rule_id])

    # Prevent duplicate dependencies
    __table_args__ = (
        UniqueConstraint("rule_id", "depends_on_rule_id", name="uq_rule_dependency"),
    )

    def __repr__(self):
        return f"<RuleDependency {self.rule_id} {self.dependency_type} {self.depends_on_rule_id}>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "rule_id": str(self.rule_id),
            "depends_on_rule_id": str(self.depends_on_rule_id),
            "dependency_type": self.dependency_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
