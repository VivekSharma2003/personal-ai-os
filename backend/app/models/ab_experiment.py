"""
Personal AI OS - A/B Testing Models
"""
import uuid
from datetime import datetime, UTC
from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class ABExperiment(Base):
    __tablename__ = "ab_experiments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    variants = relationship("ABVariant", back_populates="experiment", cascade="all, delete-orphan")


class ABVariant(Base):
    __tablename__ = "ab_variants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id = Column(UUID(as_uuid=True), ForeignKey("ab_experiments.id"), nullable=False)
    label = Column(String, nullable=False)           # e.g. "control", "variant_a"
    prompt_template = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    experiment = relationship("ABExperiment", back_populates="variants")
    results = relationship("ABResult", back_populates="variant", cascade="all, delete-orphan")


class ABResult(Base):
    __tablename__ = "ab_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    variant_id = Column(UUID(as_uuid=True), ForeignKey("ab_variants.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    score = Column(Float, nullable=False)            # 0.0 – 1.0 rating
    feedback = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    variant = relationship("ABVariant", back_populates="results")
