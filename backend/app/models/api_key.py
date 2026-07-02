"""
Personal AI OS - API Key Model
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.session import Base


class APIKey(Base):
    """
    API Key for authenticated access.

    Keys are SHA-256 hashed before storage. Only the first 8 characters
    (key_prefix) are kept in plaintext for identification in the UI.
    """

    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Security
    key_hash = Column(String(64), unique=True, nullable=False, index=True)
    key_prefix = Column(String(8), nullable=False)

    # Metadata
    name = Column(String(100), nullable=False)
    scopes = Column(JSONB, default=["*"])  # e.g. ["chat", "rules", "analytics"]

    # Lifecycle
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)

    # Security: IP allowlist (empty list = all IPs allowed)
    ip_allowlist = Column(JSONB, default=[])

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="api_keys")

    def __repr__(self):
        return f"<APIKey {self.key_prefix}*** ({self.name})>"

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def to_dict(self):
        """Convert to dictionary (never includes the raw key)."""
        return {
            "id": str(self.id),
            "name": self.name,
            "key_prefix": self.key_prefix,
            "scopes": self.scopes,
            "is_active": self.is_active,
            "ip_allowlist": self.ip_allowlist or [],
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
