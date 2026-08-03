"""
Personal AI OS - Self-Healing Schemas

Pydantic schemas for compliance evaluations and self-healing.
"""
from pydantic import BaseModel
from typing import List, Optional


class AdherenceEvaluationResponse(BaseModel):
    """Schema for adherence evaluation entry response."""
    id: str
    interaction_id: str
    rule_id: str
    adhered: bool
    score: float
    justification: Optional[str] = None
    created_at: Optional[str] = None


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
