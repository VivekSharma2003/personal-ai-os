"""
Personal AI OS - Data Retention Policy Model
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class RetentionPolicy(Base):
    """
    Per-user data retention policy.

    Defines how long different resource types are kept before
    automatic cleanup.
    """

    __tablename__ = "retention_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Resource type: 'interactions', 'audit_logs', 'conversations'
    resource_type = Column(String(50), nullable=False)

    # How many days to retain records (0 = keep forever)
    retention_days = Column(Integer, nullable=False, default=90)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="retention_policies")

    # One policy per resource type per user
    __table_args__ = (
        UniqueConstraint("user_id", "resource_type", name="uq_user_retention_resource"),
    )

    def __repr__(self):
        return f"<RetentionPolicy {self.resource_type}: {self.retention_days}d>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "resource_type": self.resource_type,
            "retention_days": self.retention_days,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
