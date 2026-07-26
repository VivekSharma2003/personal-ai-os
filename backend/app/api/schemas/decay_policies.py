"""
Personal AI OS - Decay Policy Schemas

Pydantic schemas for decay policy CRUD.
"""
from pydantic import BaseModel, Field
from typing import Optional


class DecayPolicyUpsert(BaseModel):
    """Schema to create/update a decay policy override."""
    tag_id: Optional[str] = None
    category: Optional[str] = Field(default=None, pattern="^(style|tone|formatting|logic|safety)$")
    base_decay_rate: float = Field(default=0.05, ge=0.0, le=1.0)
    grace_period_days: int = Field(default=7, ge=0, le=365)
    topic_sensitivity: float = Field(default=1.0, ge=0.0, le=5.0)


class DecayPolicyResponse(BaseModel):
    """Schema for a decay policy override response."""
    id: str
    user_id: str
    tag_id: Optional[str] = None
    category: Optional[str] = None
    base_decay_rate: float
    grace_period_days: int
    topic_sensitivity: float
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class DecayProcessResponse(BaseModel):
    """Schema for a decay processing result."""
    processed: int
    decayed: int
    archived: int
    changes: list
