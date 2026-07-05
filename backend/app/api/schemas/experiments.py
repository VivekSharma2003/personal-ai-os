"""
Personal AI OS - Experiment Schemas

Pydantic schemas for A/B testing.
"""
from pydantic import BaseModel, Field
from typing import Optional, List


class CreateExperimentRequest(BaseModel):
    """Request to create a new A/B experiment."""
    name: str = Field(..., min_length=1, max_length=255)
    rule_a_id: str
    rule_b_id: str
    min_sample_size: int = Field(default=50, ge=10, le=10000)


class RecordOutcomeRequest(BaseModel):
    """Record a satisfaction outcome for a variant."""
    variant: str = Field(..., pattern="^[ab]$")
    positive: bool


class ExperimentResponse(BaseModel):
    """Experiment details and current statistics."""
    id: str
    user_id: str
    name: str
    status: str
    rule_a_id: Optional[str] = None
    rule_b_id: Optional[str] = None
    variant_a_impressions: int
    variant_b_impressions: int
    variant_a_positive: int
    variant_b_positive: int
    variant_a_rate: float
    variant_b_rate: float
    winner: Optional[str] = None
    min_sample_size: int
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


class ExperimentListResponse(BaseModel):
    """List of experiments."""
    experiments: List[ExperimentResponse]
    total: int
