"""
Personal AI OS - User Preference Store Model

Stores per-user JSON preference blobs.  Each user has exactly one row;
PATCH operations deep-merge the new values into the existing blob.
"""
import uuid
from datetime import datetime, UTC
from sqlalchemy import Column, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.session import Base


class UserPreferences(Base):
    __tablename__ = "user_preferences"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_preferences_user_id"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Preference blobs — merged incrementally
    llm = Column(JSONB, default=dict, nullable=False)      # e.g. {"provider": "openai", "model": "gpt-4o", "temperature": 0.7}
    ui = Column(JSONB, default=dict, nullable=False)       # e.g. {"theme": "dark", "language": "en"}
    notifications = Column(JSONB, default=dict, nullable=False)  # e.g. {"email": true, "digest_frequency": "weekly"}
    custom = Column(JSONB, default=dict, nullable=False)   # catch-all for app-specific keys

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    user = relationship("User")
