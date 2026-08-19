"""
Personal AI OS - Cost Optimization Schemas
"""
from typing import List
from pydantic import BaseModel, Field


class PrunableCandidate(BaseModel):
    id: str
    content: str
    score: float
    tokens: int


class ReviewSavingsResponse(BaseModel):
    total_active_rules: int
    total_estimated_tokens: int
    prunable_rules_count: int
    potential_savings_tokens: int
    prunable_candidates: List[PrunableCandidate]


class PruneRulesRequest(BaseModel):
    max_tokens: int = Field(..., description="Maximum allowed tokens for rules context")


class PruneRulesResponse(BaseModel):
    accepted_rules_count: int
    dropped_rules_count: int
    total_tokens: int
    accepted_rules: List[str]
    dropped_rules: List[str]
