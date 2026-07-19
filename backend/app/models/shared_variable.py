"""
Personal AI OS - Shared Variable Model

Supports dynamic variables that can be referenced inside rules (e.g. {{user_name}})
and are resolved dynamically at prompt construction time.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class SharedVariable(Base):
    """
    User-scoped shared variables/parameters that expand dynamically in rules.
    Placeholders are written as {{variable_name}} inside rules.
    """

    __tablename__ = "shared_variables"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name = Column(String(100), nullable=False)
    value = Column(Text, nullable=False)
    description = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint: variable names must be unique per user
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_user_variable_name"),
    )

    # Relationships
    user = relationship("User")

    def __repr__(self):
        return f"<SharedVariable {self.id}: name={self.name} value={self.value[:30]}>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "name": self.name,
            "value": self.value,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
