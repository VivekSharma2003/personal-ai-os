"""
Personal AI OS - Health Snapshot Model

Stores periodic health check results so trends can be queried
and alerts fired when metrics breach thresholds.
"""
import uuid
from datetime import datetime, UTC
from sqlalchemy import Column, String, DateTime, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.session import Base


class HealthSnapshot(Base):
    __tablename__ = "health_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    checked_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True)

    # Subsystem statuses
    db_ok = Column(Boolean, nullable=False)
    redis_ok = Column(Boolean, nullable=False)
    vector_ok = Column(Boolean, nullable=True)

    # Key metrics
    db_latency_ms = Column(Float, nullable=True)
    redis_latency_ms = Column(Float, nullable=True)
    active_rules_count = Column(Float, nullable=True)

    # Overall
    healthy = Column(Boolean, nullable=False)
    detail = Column(JSONB, nullable=True)   # arbitrary extra probes
