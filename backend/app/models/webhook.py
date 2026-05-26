"""
Personal AI OS - Webhook Models

Webhook registration and delivery tracking for the event system.
"""
import uuid
import secrets
from datetime import datetime
# pyrefly: ignore [missing-import]
from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, Text
# pyrefly: ignore [missing-import]
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import relationship

from app.db.session import Base


class Webhook(Base):
    """
    User-registered webhook for receiving event notifications.

    Each webhook subscribes to specific event types and receives
    HMAC-SHA256 signed POST requests when those events fire.
    """

    __tablename__ = "webhooks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Webhook configuration
    url = Column(String(2048), nullable=False)
    secret = Column(String(255), nullable=False, default=lambda: secrets.token_hex(32))
    description = Column(String(500))

    # Subscribed event types
    events = Column(ARRAY(String), default=[])  # e.g., ["rule.created", "chat.completed"]

    # Status
    active = Column(Boolean, default=True)
    consecutive_failures = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")
    deliveries = relationship("WebhookDelivery", back_populates="webhook", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Webhook {self.id}: {self.url}>"

    def to_dict(self, include_secret=False):
        """Convert to dictionary for API responses."""
        result = {
            "id": str(self.id),
            "url": self.url,
            "description": self.description,
            "events": self.events or [],
            "active": self.active,
            "consecutive_failures": self.consecutive_failures,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_secret:
            result["secret"] = self.secret
        return result


class WebhookDelivery(Base):
    """
    Tracks individual webhook delivery attempts.

    Stores the payload, response, and retry count for debugging.
    """

    __tablename__ = "webhook_deliveries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    webhook_id = Column(UUID(as_uuid=True), ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False)

    # Delivery details
    event_type = Column(String(100), nullable=False)
    payload = Column(JSONB, nullable=False)

    # Response tracking
    status_code = Column(Integer)
    response_body = Column(Text)
    error_message = Column(Text)

    # Retry tracking
    attempt_number = Column(Integer, default=1)
    max_attempts = Column(Integer, default=3)
    success = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    delivered_at = Column(DateTime)

    # Relationships
    webhook = relationship("Webhook", back_populates="deliveries")

    def __repr__(self):
        return f"<WebhookDelivery {self.id}: {self.event_type} -> {self.success}>"

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "webhook_id": str(self.webhook_id),
            "event_type": self.event_type,
            "payload": self.payload,
            "status_code": self.status_code,
            "error_message": self.error_message,
            "attempt_number": self.attempt_number,
            "success": self.success,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
        }
