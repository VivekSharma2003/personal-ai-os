"""
Personal AI OS - API Session Model

Tracks active sessions tied to API keys for security monitoring.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class APISession(Base):
    """
    Tracks API sessions by (api_key, ip_address) pairs.

    Each unique combination of API key and IP address creates a session
    record for monitoring and anomaly detection.
    """

    __tablename__ = "api_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id", ondelete="CASCADE"), index=True)

    ip_address = Column(String(45), nullable=False)  # IPv4 or IPv6
    user_agent = Column(String(512), default="")

    # Activity tracking
    request_count = Column(Integer, default=1)
    last_seen_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")

    def __repr__(self):
        return f"<APISession {self.id}: {self.ip_address} ({self.request_count} requests)>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "api_key_id": str(self.api_key_id) if self.api_key_id else None,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent or "",
            "request_count": self.request_count,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
