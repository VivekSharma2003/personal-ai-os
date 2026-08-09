"""
Personal AI OS - Self-Healing Schemas

Pydantic schemas for compliance evaluations and self-healing.
"""
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import List, Optional


class AdherenceEvaluationResponse(BaseModel):
    """Schema for adherence evaluation entry response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    interaction_id: UUID
    rule_id: UUID
    adhered: bool
    score: float
    justification: Optional[str] = None
    created_at: Optional[datetime] = None


class RuleAdherenceStat(BaseModel):
    """Schema for rule adherence statistics."""
    rule_id: str
    content: str
    eval_count: int
    avg_score: float


class HealedRuleResponse(BaseModel):
    """Schema for self-healing suggestion/commit result."""
    healed: bool
    rule_id: str
    old_content: str
    new_content: str
    adherence_score: float
