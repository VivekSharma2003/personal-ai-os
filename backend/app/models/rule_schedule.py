"""
Personal AI OS - Rule Schedule Model

Allows rules to be active only during certain time windows
(one-time or recurring via cron expression).
"""
import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class ScheduleType(str, Enum):
    """Types of schedule."""
    ONE_TIME = "one_time"
    RECURRING = "recurring"


class RuleSchedule(Base):
    """
    A time-based schedule attached to a rule.

    When a rule has one or more active schedules, it is only applied
    during the windows defined by those schedules.
    """

    __tablename__ = "rule_schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(
        UUID(as_uuid=True),
        ForeignKey("rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    schedule_type = Column(
        String(20), nullable=False, default=ScheduleType.RECURRING.value
    )

    # For one-time schedules
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)

    # For recurring schedules (cron-style)
    # Format: "HH:MM-HH:MM" for daily windows, or full cron for complex
    cron_expression = Column(String(100), nullable=True)

    # Timezone (IANA format, e.g., "America/New_York", "Asia/Kolkata")
    timezone = Column(String(50), default="UTC")

    # Active days for recurring (bitmask: Mon=1, Tue=2, Wed=4, ..., Sun=64)
    # 127 = all days, 31 = weekdays, 96 = weekends
    active_days = Column(String(20), default="127")

    # Whether this schedule is enabled
    is_active = Column(Boolean, default=True)

    # Description
    description = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    rule = relationship("Rule", backref="schedules")

    def __repr__(self):
        return f"<RuleSchedule {self.id} type={self.schedule_type}>"

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "rule_id": str(self.rule_id),
            "schedule_type": self.schedule_type,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "cron_expression": self.cron_expression,
            "timezone": self.timezone,
            "active_days": self.active_days,
            "is_active": self.is_active,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
